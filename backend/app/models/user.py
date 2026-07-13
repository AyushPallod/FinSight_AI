import re
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from pydantic import BaseModel, field_validator


# ==========================================
# 1. SQLAlchemy Database Model
# ==========================================
class User(Base):
    """
    SQLAlchemy model representing the 'users' table in the database.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    documents = relationship(
        "Document", back_populates="owner", cascade="all, delete-orphan"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="user", cascade="all, delete-orphan"
    )


# ==========================================
# 2. Pydantic Validation Schemas
# ==========================================
class UserBase(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """
        Validates email format using regex to prevent bad user input.
        """
        email_clean = v.strip().lower()
        # Basic email validation regex
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email_clean):
            raise ValueError("Invalid email format")
        return email_clean


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Enforce basic password length validation.
        """
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v


class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        # Allows Pydantic to read SQLAlchemy models directly
        from_attributes = True
