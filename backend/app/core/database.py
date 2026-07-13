import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Define Database URL (fallback to local SQLite file for development)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finsight.db")

# 2. Initialize the SQLAlchemy engine
# SQLite requires 'check_same_thread=False' to allow FastAPI's multi-threaded requests
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# 3. Create SessionLocal session class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Create declarative Base class for DB models
Base = declarative_base()


def get_db():
    """
    Dependency generator that yields a database session.
    Automatically closes the session after the request lifecycle ends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
