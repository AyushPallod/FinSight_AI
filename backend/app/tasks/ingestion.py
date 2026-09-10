import logging
import os

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.chat import ChatMessage  # noqa: F401 — needed for SQLAlchemy registry
from app.models.document import Document

# All models must be imported in the Celery worker process so SQLAlchemy
# can resolve all relationship() references (e.g. Document → User).
from app.models.user import User  # noqa: F401 — needed for SQLAlchemy registry
from app.services.chunking import chunking_service
from app.services.guardrails import scrub_chunks
from app.services.ingestion import ingestion_service
from app.services.vector_store import vector_store_service

logger = logging.getLogger(__name__)


@celery_app.task(name="process_document_task")
def process_document_task(document_id: int, file_path: str, filename: str) -> None:
    """
    Background Celery task that coordinates the parsing, chunking,
    embedding, and vector indexing for an uploaded financial document.
    """
    logger.info(
        f"Background task picked up: processing document '{filename}' (ID: {document_id})"
    )

    # We instantiate a transaction session dedicated to this worker process
    db = SessionLocal()
    try:
        # 1. Look up the document record in SQLite
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(
                f"Failed task: Document ID {document_id} was not found in SQLite."
            )
            return

        # 2. Update status to 'processing'
        doc.upload_status = "processing"
        db.commit()
        logger.info(f"Document ID {document_id} marked as 'processing'.")

        # 3. Derive file extension for the ingestion dispatcher
        file_extension = os.path.splitext(filename)[1].lower()

        # 4. Extract text pages from the document
        logger.info(f"Extracting content from: {file_path}")
        pages = ingestion_service.extract_text(file_path, file_extension)
        logger.info(f"Extracted {len(pages)} page(s) from '{filename}'.")

        # 5. Perform semantic chunking — passes document_id and filename for metadata
        logger.info(f"Chunking document '{filename}'...")
        chunks = chunking_service.chunk_document(
            pages=pages, document_id=str(document_id), source_filename=filename
        )

        # 6. Scrub PII from chunk text before it enters the vector store
        logger.info(
            f"Scrubbing PII from {len(chunks)} chunks for document '{filename}'..."
        )
        chunks = scrub_chunks(chunks)

        # 7. Generate embeddings and index inside Qdrant
        logger.info(
            f"Vector-indexing {len(chunks)} chunks in Qdrant for document ID {document_id}..."
        )
        vector_store_service.upsert_document_chunks(chunks)

        # 8. Mark status as 'completed'
        doc.upload_status = "completed"
        db.commit()
        logger.info(
            f"Background task succeeded! Document ID {document_id} marked as 'completed'."
        )

    except Exception as e:
        logger.exception(
            f"Background task failed for document ID {document_id} due to: {e!s}"
        )

        # Update SQL status to 'failed' so the user is informed
        db.rollback()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.upload_status = "failed"
            db.commit()

    finally:
        # Close the DB session
        db.close()

        # 7. Clean up the temporary file on disk to prevent temp folder storage leak
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temporary upload file: {file_path}")
            except Exception as cleanup_err:
                logger.warning(
                    f"Could not remove temp file {file_path}: {cleanup_err!s}"
                )
