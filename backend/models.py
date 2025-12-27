from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON
from datetime import datetime

db = SQLAlchemy()

class Agent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    system_message = db.Column(db.Text, nullable=True)
    config = db.Column(JSON, nullable=True) # 存储 LLM 配置
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "system_message": self.system_message,
            "config": self.config,
            "created_at": self.created_at.isoformat()
        }

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat()
        }

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }
