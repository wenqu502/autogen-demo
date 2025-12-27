from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from models import db, Agent, Conversation, Message
from autogen_service import run_autogen_chat
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app) # 允许跨域

# 配置数据库
# 默认值用于测试，实际应从 .env 读取
db_url = os.environ.get('DATABASE_URL', 'sqlite:///autogen.db')
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/agents', methods=['GET'])
def get_agents():
    agents = Agent.query.all()
    return jsonify([a.to_dict() for a in agents])

@app.route('/api/agents', methods=['POST'])
def create_agent():
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Name is required"}), 400
        
    new_agent = Agent(
        name=data['name'],
        system_message=data.get('system_message', ''),
        config=data.get('config', {})
    )
    db.session.add(new_agent)
    db.session.commit()
    return jsonify(new_agent.to_dict()), 201

@app.route('/api/agents/<int:id>', methods=['DELETE'])
def delete_agent(id):
    agent = Agent.query.get_or_404(id)
    db.session.delete(agent)
    db.session.commit()
    return jsonify({"message": "Agent deleted"})

@app.route('/api/agents/<int:id>/duplicate', methods=['POST'])
def duplicate_agent(id):
    original_agent = Agent.query.get_or_404(id)
    new_agent = Agent(
        name=f"{original_agent.name}_copy",
        system_message=original_agent.system_message,
        config=original_agent.config
    )
    db.session.add(new_agent)
    db.session.commit()
    return jsonify(new_agent.to_dict()), 201

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message')
    agent_ids = data.get('agent_ids', [])
    
    if not user_input:
        return jsonify({"error": "Message is required"}), 400
    
    # 获取选中的 agents
    agents = Agent.query.filter(Agent.id.in_(agent_ids)).all()
    agents_config = []
    for a in agents:
        agent_data = {
            "name": a.name,
            "system_message": a.system_message,
            "description": a.config.get('description') if a.config else None,
            "config": a.config # 传递完整配置
        }
        agents_config.append(agent_data)
    
    if not agents_config:
         return jsonify({"error": "No agents selected or found"}), 400

    # 运行 AutoGen
    try:
        messages = run_autogen_chat(agents_config, user_input)
        return jsonify({"messages": messages})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
