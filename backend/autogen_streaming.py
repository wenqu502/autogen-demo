import autogen
import queue
import threading
import json
import os
from datetime import datetime

class TrackingGroupChat(autogen.GroupChat):
    def __init__(self, queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._queue = queue
    
    def append(self, message, speaker):
        # 将消息放入队列
        # message is a dict: {'content': ..., 'role': ..., 'name': ...}
        # speaker is the Agent object
        msg_copy = message.copy()
        msg_copy['name'] = speaker.name # Ensure name is correct
        msg_copy['timestamp'] = datetime.utcnow().isoformat()
        self._queue.put(msg_copy)
        super().append(message, speaker)

def run_streaming_chat(agents_config, user_input, history=None, max_round=10):
    """
    运行 AutoGen 对话并流式返回消息
    :param agents_config: list of dict, 智能体配置
    :param user_input: str, 用户输入 (如果是 'CONTINUE' 且无内容，则可能需要特殊处理)
    :param history: list of dict, 历史消息
    :param max_round: int, 最大轮数
    :return: generator yielding JSON strings
    """
    
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        yield json.dumps({"error": "DEEPSEEK_API_KEY not found"})
        return

    base_llm_config = {
        "config_list": [{"model": "deepseek-chat", "api_key": api_key, "base_url": "https://api.deepseek.com"}],
        "temperature": 0.7,
    }

    # 1. 创建 UserProxy
    user_proxy = autogen.UserProxyAgent(
        name="User",
        system_message="A human admin.",
        code_execution_config=False,
        human_input_mode="NEVER",
        llm_config=False,
    )

    # 2. 创建 Assistants
    assistants = []
    for agent_cfg in agents_config:
        # 合并 LLM 配置
        llm_config = base_llm_config.copy()
        if 'config' in agent_cfg and agent_cfg['config']:
            if 'temperature' in agent_cfg['config']:
                llm_config['temperature'] = min(1.0, agent_cfg['config']['temperature']) # Fix temperature > 1.0 issue

        assistant = autogen.AssistantAgent(
            name=agent_cfg['name'],
            system_message=agent_cfg['system_message'],
            description=agent_cfg.get('description'), # 用于 GroupChat 选择
            llm_config=llm_config
        )
        assistants.append(assistant)

    # 3. 准备历史消息
    initial_messages = []
    if history:
        for msg in history:
            if isinstance(msg, dict) and 'content' in msg and 'role' in msg:
                clean_msg = {
                    "role": msg['role'],
                    "content": msg['content'],
                    "name": msg.get('name', msg['role'])
                }
                # 如果是 system 消息且不是初始 system_message，可能需要过滤？
                # AutoGen 通常处理 system message 是通过 agent.system_message
                # 这里主要放 user 和 assistant 的对话记录
                if clean_msg['role'] != 'system':
                     initial_messages.append(clean_msg)

    # 4. 创建 TrackingGroupChat 和 Manager
    msg_queue = queue.Queue()
    
    groupchat = TrackingGroupChat(
        queue=msg_queue,
        agents=[user_proxy] + assistants, 
        messages=initial_messages, 
        max_round=max_round
    )
    
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=base_llm_config)

    # 5. 在线程中运行 initiate_chat
    def run_chat_thread():
        try:
            # 如果 user_input 为空字符串 (例如点击 "继续")，我们需要特殊的处理
            # AutoGen 的 initiate_chat 需要一个 message。
            # 如果是继续，我们是否可以用 user_proxy 说一句 "Please continue" ? 
            # 或者，如果 history 不为空，我们可以尝试 resume?
            # 简单起见，如果 user_input 有内容，则是用户发言。
            # 如果 user_input 为空，我们让 user_proxy 发送一个空消息或者 "Continue" (但这会出现在历史里)
            # 更好的方法：如果 user_input 是空的，我们也许不应该调用 initiate_chat 而是直接 run_chat?
            # 但 initiate_chat 是入口。
            
            prompt = user_input
            if not prompt:
                prompt = "Please continue the discussion."

            user_proxy.initiate_chat(
                manager,
                message=prompt,
                clear_history=False
            )
        except Exception as e:
            msg_queue.put({"error": str(e)})
        finally:
            msg_queue.put(None) # Sentinel

    thread = threading.Thread(target=run_chat_thread)
    thread.start()

    # 6. 主线程流式返回
    first_msg = True
    while True:
        try:
            # 使用较短的超时时间，以便在长时间无响应时发送心跳或检查状态
            # 但这里我们主要依赖 queue 的阻塞
            # 600s 超时确实有点长，如果 DeepSeek 响应慢，这里会一直卡着
            # 我们可以改为循环检查，或者前端增加超时处理
            # 这里的 log 显示 GroupChat is underpopulated，可能是 AutoGen 在等待某些条件？
            # 或者 DeepSeek API 响应慢？
            
            msg = msg_queue.get(timeout=600) # Wait up to 600s for a message (agents can be slow)
            if msg is None:
                break
            
            if "error" in msg:
                yield f"data: {json.dumps({'error': msg['error']})}\n\n"
            else:
                # 过滤掉刚才用户发送的消息 (因为前端已经有了)
                # 只有当它是新生成的消息时才发送
                # initiate_chat 会先把用户消息加入 groupchat，所以第一个消息通常是 user input
                if first_msg and msg.get('role') == 'user':
                    first_msg = False
                    continue
                
                first_msg = False
                yield f"data: {json.dumps(msg)}\n\n"
                
        except queue.Empty:
            # 如果超时，发送一个特定的错误或者心跳？
            # 这里是完全没有消息产生
            yield f"data: {json.dumps({'error': 'Timeout waiting for agent response. Please try again.'})}\n\n"
            break
        except GeneratorExit:
            # 客户端断开连接 (ERR_ABORTED)
            # 我们应该停止后台线程吗？
            # 很难直接停止线程，但我们可以不再 yield
            print("Client disconnected from stream")
            break
        except Exception as e:
             print(f"Stream error: {e}")
             break
            
    yield "data: [DONE]\n\n"
