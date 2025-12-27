import autogen
import os

def run_autogen_chat(agents_config, user_input):
    """
    运行 AutoGen 对话
    :param agents_config: list of dict, e.g. [{'name': 'Coder', 'system_message': '...'}]
    :param user_input: str
    :return: list of messages
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not found in environment variables")

    # 配置 DeepSeek
    base_llm_config = {
        "config_list": [
            {
                "model": "deepseek-chat",
                "api_key": api_key,
                "base_url": "https://api.deepseek.com"
            }
        ],
        "temperature": 0.7,
    }

    # 创建 User Proxy
    # human_input_mode="NEVER" 表示不请求人类输入，全自动运行
    user_proxy = autogen.UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0,
        code_execution_config={"work_dir": "coding", "use_docker": False}, # 允许本地代码执行，注意安全
    )

    # 创建 Assistants
    assistants = []
    for agent_conf in agents_config:
        # 合并自定义配置
        agent_llm_config = base_llm_config.copy()
        
        # 如果 agent 有自定义的 llm_config，可以覆盖 (这里简单处理，支持 temperature)
        custom_config = agent_conf.get('config', {})
        if 'temperature' in custom_config:
             agent_llm_config['temperature'] = float(custom_config['temperature'])

        assistant = autogen.AssistantAgent(
            name=agent_conf['name'],
            system_message=agent_conf['system_message'],
            description=agent_conf.get('description'), # 用于 GroupChat 选择
            llm_config=agent_llm_config,
            human_input_mode=custom_config.get('human_input_mode', 'NEVER'),
            max_consecutive_auto_reply=int(custom_config.get('max_consecutive_auto_reply', 10))
        )
        assistants.append(assistant)

    if not assistants:
        return [{"role": "system", "content": "No agents configured."}]

    # 使用 GroupChat
    groupchat = autogen.GroupChat(
        agents=[user_proxy] + assistants, 
        messages=[], 
        max_round=20
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=base_llm_config)
    
    try:
        # 触发对话
        user_proxy.initiate_chat(
            manager,
            message=user_input
        )
        
        # 返回聊天记录
        # groupchat.messages 是一个列表，包含所有发言
        # 格式: [{'role': 'user', 'content': '...', 'name': '...'}, ...]
        return groupchat.messages
    except Exception as e:
        print(f"Error in autogen: {e}")
        return [{"role": "system", "content": f"Error: {str(e)}"}]
