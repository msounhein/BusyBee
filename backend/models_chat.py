from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database import Base

class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    reasoning_content = Column(Text, nullable=True)  # MiniMax thinking — must pass back on multi-turn
    created_at = Column(DateTime, default=datetime.utcnow)
