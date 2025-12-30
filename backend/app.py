from flask import Flask, request, jsonify, render_template, session, Response, stream_with_context, send_from_directory
from flask_cors import CORS
from models import db, Agent, Conversation, Message, User
from autogen_service import run_autogen_chat
from autogen_streaming import run_streaming_chat
import os
import json
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

import logging
import traceback
from werkzeug.exceptions import HTTPException

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')

# Global Error Handler
@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors
    if isinstance(e, HTTPException):
        return e

    # Now you're handling non-HTTP exceptions only
    logger.error(f"Unhandled Exception: {str(e)}")
    logger.error(traceback.format_exc())
    return jsonify({
        "error": "Internal Server Error",
        "message": str(e),
        "traceback": traceback.format_exc()
    }), 500

app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key') # 必须设置 secret_key 才能使用 session
CORS(app, supports_credentials=True) # 允许跨域携带 cookie

# 配置数据库
# 默认值用于测试，实际应从 .env 读取
# Render 等生产环境建议使用 PostgreSQL，这里使用 SQLite 作为 fallback
# 使用绝对路径确保在 Render 上能正确写入
basedir = os.path.abspath(os.path.dirname(__file__))
default_db_path = os.path.join(basedir, 'autogen.db')
db_url = os.environ.get('DATABASE_URL', f'sqlite:///{default_db_path}')

print(f"Starting app with database: {db_url}")

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# 初始化数据库表
with app.app_context():
    try:
        db.create_all()
        print("Database tables created.")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        print("Please ensure PostgreSQL is running and the database exists.")

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

# --- Auth Routes ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400
    
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    # --- Pre-seed Default Agents ---
    default_agents = [
        {
            "name": "史蒂夫·乔布斯",
            "system_message": "你就是史蒂夫·乔布斯。你追求极致的完美，对产品设计和用户体验有着近乎偏执的要求。你说话直率，甚至有些刻薄，但总是能一针见血地指出问题。你推崇“极简主义”，痛恨平庸。在对话中，你要展现出你的远见卓识和对改变世界的渴望。",
            "config": {
                "description": "已故苹果创始人，产品设计与用户体验专家，追求完美与极简。",
                "temperature": 0.9,
                "human_input_mode": "ALWAYS"
            }
        },
        {
            "name": "伊隆·马斯克",
            "system_message": "你是伊隆·马斯克。你是一个物理学第一性原理的信徒，总是思考如何通过技术让人类成为跨行星物种。你说话快，思维跳跃，喜欢用硬核的工程术语。你非常乐观，对时间线总是过于自信。你关注能源、航天、AI 和脑机接口。",
            "config": {
                "description": "SpaceX/Tesla 创始人，关注第一性原理、工程与未来科技。",
                "temperature": 1.0,
                "human_input_mode": "ALWAYS"
            }
        },
        {
            "name": "孔子",
            "system_message": "你是孔丘，字仲尼，人称孔子。你是儒家学派的创始人，万世师表。你说话引经据典，重视“仁”、“义”、“礼”、“智”、“信”。你总是循循善诱，试图用道德和礼教来感化提问者。你的语言风格古朴典雅，但要让现代人听得懂。",
            "config": {
                "description": "儒家至圣先师，擅长道德教化、哲学思考与人生智慧。",
                "temperature": 0.6,
                "human_input_mode": "ALWAYS"
            }
        },
        {
            "name": "李白",
            "system_message": "你是李白，号青莲居士，人称“诗仙”。你性格豪放不羁，热爱美酒与明月。你说话充满了浪漫主义色彩，动不动就吟诗作对。你想象力丰富，不拘小节，对世俗的权贵不屑一顾，追求精神的绝对自由。",
            "config": {
                "description": "唐代浪漫主义诗人，擅长文学创作、创意灵感与情感表达。",
                "temperature": 1.0,
                "human_input_mode": "ALWAYS"
            }
        },
        {
            "name": "夏洛克·福尔摩斯",
            "system_message": "你是夏洛克·福尔摩斯。你是一个高功能的反社会人格（自称），世界上唯一的咨询侦探。你极其理性，观察力敏锐，擅长演绎推理。你说话语速快，逻辑严密，对他人的情感波动不感兴趣，只关注事实和真相。你喜欢用排除法解决问题。",
            "config": {
                "description": "咨询侦探，擅长逻辑推理、细节观察与事实分析。",
                "temperature": 0.3,
                "human_input_mode": "ALWAYS"
            }
        }
    ]

    for agent_data in default_agents:
        new_agent = Agent(
            user_id=user.id,
            name=agent_data['name'],
            system_message=agent_data['system_message'],
            config=agent_data['config']
        )
        db.session.add(new_agent)
    
    db.session.commit()
    
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session['user_id'] = user.id
        return jsonify({"message": "Login successful", "user": {"id": user.id, "username": user.username}})
    
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/guest_login', methods=['POST'])
def guest_login():
    session['user_id'] = 'guest'
    return jsonify({"message": "Guest login successful", "user": {"id": "guest", "username": "访客 (临时)"}})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "Logged out"})

@app.route('/api/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify(None)
    
    if session['user_id'] == 'guest':
        return jsonify({"id": "guest", "username": "访客 (临时)"})

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify(None)
    return jsonify({"id": user.id, "username": user.username})

# --- Protected Agent Routes ---

@app.route('/api/agents', methods=['GET'])
@login_required
def get_agents():
    user_id = session['user_id']
    if user_id == 'guest':
        return jsonify([]) # 访客不从数据库读取
    
    agents = Agent.query.filter_by(user_id=user_id).all()
    
    # --- 如果用户没有智能体，自动预置默认智能体 ---
    if not agents:
        default_agents = [
            {
                "name": "史蒂夫·乔布斯",
                "system_message": "你就是史蒂夫·乔布斯。你追求极致的完美，对产品设计和用户体验有着近乎偏执的要求。你说话直率，甚至有些刻薄，但总是能一针见血地指出问题。你推崇“极简主义”，痛恨平庸。在对话中，你要展现出你的远见卓识和对改变世界的渴望。",
                "config": {
                    "description": "已故苹果创始人，产品设计与用户体验专家，追求完美与极简。",
                    "temperature": 0.9,
                    "human_input_mode": "NEVER"
                }
            },
            {
                "name": "伊隆·马斯克",
                "system_message": "你是伊隆·马斯克。你是一个物理学第一性原理的信徒，总是思考如何通过技术让人类成为跨行星物种。你说话快，思维跳跃，喜欢用硬核的工程术语。你非常乐观，对时间线总是过于自信。你关注能源、航天、AI 和脑机接口。",
                "config": {
                    "description": "SpaceX/Tesla 创始人，关注第一性原理、工程与未来科技。",
                    "temperature": 1.0,
                    "human_input_mode": "NEVER"
                }
            },
            {
                "name": "孔子",
                "system_message": "你是孔丘，字仲尼，人称孔子。你是儒家学派的创始人，万世师表。你说话引经据典，重视“仁”、“义”、“礼”、“智”、“信”。你总是循循善诱，试图用道德和礼教来感化提问者。你的语言风格古朴典雅，但要让现代人听得懂。",
                "config": {
                    "description": "儒家至圣先师，擅长道德教化、哲学思考与人生智慧。",
                    "temperature": 0.6,
                    "human_input_mode": "NEVER"
                }
            },
            {
                "name": "李白",
                "system_message": "你是李白，号青莲居士，人称“诗仙”。你性格豪放不羁，热爱美酒与明月。你说话充满了浪漫主义色彩，动不动就吟诗作对。你想象力丰富，不拘小节，对世俗的权贵不屑一顾，追求精神的绝对自由。",
                "config": {
                    "description": "唐代浪漫主义诗人，擅长文学创作、创意灵感与情感表达。",
                    "temperature": 1.0,
                    "human_input_mode": "NEVER"
                }
            },
            {
                "name": "夏洛克·福尔摩斯",
                "system_message": "你是夏洛克·福尔摩斯。你是一个高功能的反社会人格（自称），世界上唯一的咨询侦探。你极其理性，观察力敏锐，擅长演绎推理。你说话语速快，逻辑严密，对他人的情感波动不感兴趣，只关注事实和真相。你喜欢用排除法解决问题。",
                "config": {
                    "description": "咨询侦探，擅长逻辑推理、细节观察与事实分析。",
                    "temperature": 0.3,
                    "human_input_mode": "NEVER"
                }
            }
        ]

        for agent_data in default_agents:
            new_agent = Agent(
                user_id=user_id,
                name=agent_data['name'],
                system_message=agent_data['system_message'],
                config=agent_data['config']
            )
            db.session.add(new_agent)
        
        db.session.commit()
        
        # 重新查询
        agents = Agent.query.filter_by(user_id=user_id).all()

    return jsonify([a.to_dict() for a in agents])

@app.route('/api/agents', methods=['POST'])
@login_required
def create_agent():
    if session['user_id'] == 'guest':
        # 访客创建的智能体不保存到数据库，仅前端维护
        # 这里返回一个模拟的响应，但实际上前端应该自己处理
        return jsonify({"id": 999, "name": "Temp", "user_id": "guest"}), 200

    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Name is required"}), 400
        
    new_agent = Agent(
        user_id=session['user_id'], # 关联当前用户
        name=data['name'],
        system_message=data.get('system_message', ''),
        config=data.get('config', {})
    )
    db.session.add(new_agent)
    db.session.commit()
    return jsonify(new_agent.to_dict()), 201

@app.route('/api/agents/<int:id>', methods=['DELETE'])
@login_required
def delete_agent(id):
    agent = Agent.query.filter_by(id=id, user_id=session['user_id']).first_or_404()
    db.session.delete(agent)
    db.session.commit()
    return jsonify({"message": "Agent deleted"})

@app.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    user_id = session['user_id']
    if user_id == 'guest':
        return jsonify([])
    
    convs = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.updated_at.desc()).all()
    return jsonify([c.to_dict() for c in convs])

@app.route('/api/conversations', methods=['POST'])
@login_required
def create_conversation():
    user_id = session['user_id']
    if user_id == 'guest':
        return jsonify({"id": "temp", "title": "Temporary Chat"}), 200
        
    data = request.json
    title = data.get('title', 'New Chat')
    agent_ids = data.get('agent_ids', [])
    
    conv = Conversation(user_id=user_id, title=title, agent_ids=agent_ids)
    db.session.add(conv)
    db.session.commit()
    return jsonify(conv.to_dict()), 201

@app.route('/api/conversations/<int:id>', methods=['GET'])
@login_required
def get_conversation(id):
    user_id = session['user_id']
    conv = Conversation.query.filter_by(id=id, user_id=user_id).first_or_404()
    messages = Message.query.filter_by(conversation_id=id).order_by(Message.timestamp.asc()).all()
    
    return jsonify({
        "conversation": conv.to_dict(),
        "messages": [m.to_dict() for m in messages]
    })

@app.route('/api/conversations/<int:id>', methods=['PUT'])
@login_required
def update_conversation(id):
    user_id = session['user_id']
    conv = Conversation.query.filter_by(id=id, user_id=user_id).first_or_404()
    data = request.json
    
    if 'title' in data:
        conv.title = data['title']
    if 'agent_ids' in data:
        conv.agent_ids = data['agent_ids']
        
    db.session.commit()
    return jsonify(conv.to_dict())

@app.route('/api/chat/stream', methods=['POST'])
@login_required
def chat_stream():
    data = request.json
    user_input = data.get('message')
    conversation_id = data.get('conversation_id')
    
    # 历史记录处理：
    # 如果是 DB 会话，从 DB 加载
    # 如果是 Guest 或 Stateless，从 history 字段加载
    history = []
    agent_ids = []
    
    user_id = session['user_id']
    is_guest = (user_id == 'guest')
    
    # --- Guest Mode Handling ---
    if is_guest:
        history = data.get('history', [])
        agents_data = data.get('agents', [])
        if not agents_data:
             return jsonify({"error": "No agents provided for guest"}), 400
        agents_config = agents_data
        
    # --- Registered User Handling ---
    else:
        if conversation_id:
            conv = Conversation.query.filter_by(id=conversation_id, user_id=user_id).first()
            if not conv:
                return jsonify({"error": "Conversation not found"}), 404
            
            # Update title if it's new
            if conv.title == 'New Chat' and user_input:
                conv.title = user_input[:20]
                db.session.commit()
            
            # Load Agents
            agent_ids = conv.agent_ids or []
            if not agent_ids:
                 # Try to get from request if not in DB yet (e.g. first msg)
                 agent_ids = data.get('agent_ids', [])
                 if agent_ids:
                     conv.agent_ids = agent_ids
                     db.session.commit()
            
            # Load Messages
            db_msgs = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp.asc()).all()
            history = [m.to_dict() for m in db_msgs]
            
            # Fetch Agent Configs
            agents = Agent.query.filter(Agent.id.in_(agent_ids), Agent.user_id == user_id).all()
            if not agents:
                 return jsonify({"error": "No agents found"}), 400
            
            agents_config = []
            for a in agents:
                agents_config.append({
                    "name": a.name,
                    "system_message": a.system_message,
                    "description": a.config.get('description') if a.config else None,
                    "config": a.config
                })
        else:
             return jsonify({"error": "Conversation ID required for registered users"}), 400

    # Save User Message to DB (if not guest)
    if not is_guest and conversation_id and user_input:
        user_msg = Message(
            conversation_id=conversation_id,
            role='user',
            name='User',
            content=user_input
        )
        db.session.add(user_msg)
        db.session.commit()

    def generate():
        # Stream wrapper to save to DB
        with app.app_context():
            # Get generator
            gen = run_streaming_chat(agents_config, user_input, history)
            
            for chunk in gen:
                # Chunk format: "data: {...}\n\n"
                if chunk.startswith("data: "):
                    json_str = chunk[6:].strip()
                    if json_str != "[DONE]":
                        try:
                            msg_data = json.loads(json_str)
                            if "error" not in msg_data and not is_guest and conversation_id:
                                # Save agent response to DB
                                # msg_data has: role, content, name, timestamp
                                agent_msg = Message(
                                    conversation_id=conversation_id,
                                    role=msg_data.get('role', 'assistant'),
                                    name=msg_data.get('name'),
                                    content=msg_data.get('content'),
                                )
                                db.session.add(agent_msg)
                                db.session.commit()
                        except Exception as e:
                            print(f"Error saving message: {e}")
                
                yield chunk

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/debug', methods=['GET'])
def debug_info():
    try:
        import autogen
        import openai
        import pydantic
        return jsonify({
            "status": "ok",
            "autogen_version": getattr(autogen, "__version__", "unknown"),
            "openai_version": getattr(openai, "__version__", "unknown"),
            "pydantic_version": getattr(pydantic, "__version__", "unknown"),
            "env_api_key_present": bool(os.environ.get("DEEPSEEK_API_KEY"))
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
