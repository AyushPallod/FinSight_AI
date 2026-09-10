import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.document import Document
from app.models.user import User
from app.tasks.ingestion import process_document_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Temp uploads directory path
TEMP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp_uploads"
)
os.makedirs(TEMP_DIR, exist_ok=True)


# Response schemas
class UploadResponse(BaseModel):
    id: int
    filename: str
    upload_status: str
    message: str


class DocumentStatusResponse(BaseModel):
    id: int
    filename: str
    upload_status: str
    created_at: str


@router.post(
    "/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document (PDF, DOCX, PPTX, or TXT).
    Saves metadata to database and offloads parsing, chunking, and indexing to a background Celery queue.
    """
    filename = file.filename
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File upload lacks a valid filename.",
        )

    file_extension = os.path.splitext(filename)[1].lower().strip(".")
    allowed_extensions = ["pdf", "doc", "docx", "ppt", "pptx", "txt"]

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: .{file_extension}. Allowed types: {', '.join(allowed_extensions)}",
        )

    # Save to unique temp file to avoid file overwriting conflicts
    unique_id = str(uuid.uuid4())
    temp_filename = f"{unique_id}_{filename}"
    temp_file_path = os.path.join(TEMP_DIR, temp_filename)
    logger.info(f"Receiving file: {filename}. Saving temporarily to: {temp_file_path}")

    try:
        # Write file in chunks to prevent high memory usage
        with open(temp_file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunk size
                buffer.write(chunk)

        # 1. Create a metadata entry in the SQLite database
        new_doc = Document(
            filename=filename, upload_status="pending", owner_id=current_user.id
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        # 2. Trigger Celery Task Asynchronously
        logger.info(
            f"Queuing background ingestion task for document '{filename}' (ID: {new_doc.id})"
        )
        process_document_task.delay(
            document_id=new_doc.id, file_path=temp_file_path, filename=filename
        )

        return UploadResponse(
            id=new_doc.id,
            filename=new_doc.filename,
            upload_status=new_doc.upload_status,
            message="Document upload accepted. Processing started in the background.",
        )

    except Exception as e:
        logger.error(
            f"Error starting background ingestion of {filename}: {e!s}",
            exc_info=True,
        )
        # Clean up temp file immediately on failure to trigger task
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate document upload: {e!s}",
        )


@router.get(
    "/{id}/status",
    response_model=DocumentStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_document_status(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the processing status of an uploaded document.
    """
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        )

    # Ownership check
    if doc.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this document's status.",
        )

    return DocumentStatusResponse(
        id=doc.id,
        filename=doc.filename,
        upload_status=doc.upload_status,
        created_at=doc.created_at.isoformat(),
    )
