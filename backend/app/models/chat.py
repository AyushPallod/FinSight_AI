from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ChatMessage(Base):
    """
    SQLAlchemy model representing the 'chat_messages' table.
    Stores historical questions, LLM answers, and JSON-serialized citations.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    citations = Column(JSON, nullable=False) # Stores array of citation structures
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="chat_messages")
