from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Document(Base):
    """
    SQLAlchemy model representing the 'documents' table in PostgreSQL/SQLite.
    Tracks metadata and ingestion status for every uploaded financial report.
    """

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False, index=True)
    upload_status = Column(
        String, default="pending", nullable=False
    )  # pending, processing, completed, failed
    owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", back_populates="documents")
