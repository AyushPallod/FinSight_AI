import os
import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set default test database if not set
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///./finsight_test.db"

import numpy as np
import pytest
from qdrant_client import QdrantClient
from sqlalchemy import create_engine

from app.core.celery_app import celery_app
from app.core.database import Base, SessionLocal, get_db
from app.main import app
from app.routers import search
from app.services.vector_store import vector_store_service


# Mock embedding model to avoid downloading BGE-M3 (2.2GB)
class MockEmbeddingModel:
    def encode(self, texts, **kwargs):
        if isinstance(texts, str):
            return np.random.rand(1024)
        return np.random.rand(len(texts), 1024)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    engine = create_engine(os.environ["DATABASE_URL"])
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after tests finish
    Base.metadata.drop_all(bind=engine)
    # Clean up test SQLite file if it was created
    if "sqlite" in os.environ["DATABASE_URL"]:
        db_file = os.environ["DATABASE_URL"].replace("sqlite:///", "")
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_tables(db_session):
    yield
    # Truncate tables to ensure tests have clean state
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()


@pytest.fixture(autouse=True)
def override_get_db(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_qdrant():
    # Use in-memory QdrantClient for testing
    client = QdrantClient(":memory:")

    # Pre-create the collection in memory
    from qdrant_client.models import Distance, VectorParams

    client.create_collection(
        collection_name=vector_store_service.collection_name,
        vectors_config=VectorParams(
            size=vector_store_service.vector_dim, distance=Distance.COSINE
        ),
    )

    @contextmanager
    def mock_get_client():
        yield client

    with patch.object(vector_store_service, "get_client", side_effect=mock_get_client):
        yield client


@pytest.fixture(autouse=True)
def mock_embedding_model():
    with patch.object(vector_store_service, "_model", new=MockEmbeddingModel()):
        yield


@pytest.fixture(autouse=True)
def eager_celery():
    # Run tasks synchronously in the same process
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield


@pytest.fixture(autouse=True)
def mock_redis():
    mock_client = MagicMock()
    mock_client.get.return_value = None  # Always cache miss
    with patch.object(search, "redis_client", mock_client):
        yield mock_client
