import logging
import os
import uuid
from contextlib import contextmanager
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    def __init__(self):
        self.collection_name = "financial_documents"
        self.vector_dim = 1024  # BGE-M3 outputs 1024-dimensional vectors
        self._model = None

        # Configure Qdrant database folder path in the workspace
        self.db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "qdrant_storage",
        )

        # Initialize default collection
        self.init_collection()

    @contextmanager
    def get_client(self):
        """
        Context manager to lease a Qdrant client connection.
        Attempts to connect to standard port 6333 first, falling back to local file-based database.
        Strictly releases file locks upon context exit.
        """
        client = None
        try:
            client = QdrantClient(
                host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=1.0
            )
            client.get_collections()  # Simple call to verify server is active
        except Exception:
            client = QdrantClient(path=self.db_path)

        try:
            yield client
        finally:
            if client:
                client.close()

    @property
    def model(self) -> SentenceTransformer:
        """
        Lazy-loads the embedding model. This prevents the server from freezing
        during imports or startup while downloading/loading the model weights.
        """
        if self._model is None:
            logger.info(
                "Loading BAAI/bge-m3 embedding model (downloading ~2.2GB on first run)..."
            )
            self._model = SentenceTransformer("BAAI/bge-m3")
            logger.info("BAAI/bge-m3 model loaded successfully.")
        return self._model

    def init_collection(self):
        """
        Creates the Qdrant collection if it does not exist.
        """
        try:
            with self.get_client() as client:
                if not client.collection_exists(self.collection_name):
                    logger.info(
                        f"Collection '{self.collection_name}' not found. Creating it."
                    )
                    client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=self.vector_dim, distance=Distance.COSINE
                        ),
                    )
                    logger.info(
                        f"Collection '{self.collection_name}' created successfully."
                    )
                else:
                    logger.info(f"Collection '{self.collection_name}' already exists.")
        except Exception as e:
            logger.error(
                f"Failed to check or create collection '{self.collection_name}': {e!s}",
                exc_info=True,
            )

    def upsert_document_chunks(self, chunks: list[dict[str, Any]]) -> bool:
        """
        Embeds a list of document chunks and indexes them in Qdrant with their metadata.
        """
        if not chunks:
            logger.warning("No chunks provided for vector storage.")
            return False

        try:
            # 1. Extract texts to embed
            texts = [chunk["text"] for chunk in chunks]
            logger.info(
                f"Generating embeddings for {len(texts)} chunks using BGE-M3..."
            )

            # 2. Generate embeddings (dense vectors)
            embeddings = self.model.encode(texts, show_progress_bar=True)
            logger.info("Embeddings generated successfully.")

            # 3. Build Qdrant PointStruct list
            points = []
            for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                point_id = str(uuid.uuid4())
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector.tolist(),  # Qdrant requires standard python list of floats
                        payload={
                            "document_id": chunk["document_id"],
                            "source_filename": chunk["source_filename"],
                            "page_number": chunk["page_number"],
                            "chunk_index": chunk["chunk_index"],
                            "text": chunk["text"],
                            "word_count": chunk["word_count"],
                            "char_count": chunk["char_count"],
                        },
                    )
                )

            # 4. Upsert into Qdrant database
            logger.info(
                f"Upserting {len(points)} points into collection '{self.collection_name}'..."
            )
            with self.get_client() as client:
                client.upsert(collection_name=self.collection_name, points=points)
            logger.info("Upsert completed successfully.")
            return True

        except Exception as e:
            logger.error(
                f"Error during chunk embedding and indexing: {e!s}", exc_info=True
            )
            raise e


# Instantiate singleton service instance
vector_store_service = VectorStoreService()
