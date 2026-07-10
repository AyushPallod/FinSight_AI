import os
import shutil
import logging
import uuid
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from app.services.ingestion import ingestion_service
from app.services.chunking import chunking_service
from app.services.vector_store import vector_store_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)

# Temp uploads directory path
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp_uploads")

# Response schemas
class PageContent(BaseModel):
    page_number: int
    text: str

class ChunkContent(BaseModel):
    chunk_index: int
    document_id: str
    source_filename: str
    page_number: int
    text: str
    word_count: int
    char_count: int

class DocumentIngestionResponse(BaseModel):
    filename: str
    extension: str
    total_pages: int
    total_characters: int
    content: List[PageContent]
    chunks: List[ChunkContent]

@router.post("/upload", response_model=DocumentIngestionResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document (PDF, DOCX, PPTX, or TXT) to extract its text and perform semantic chunking with metadata.
    """
    filename = file.filename
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="File upload lacks a valid filename."
        )

    file_extension = os.path.splitext(filename)[1].lower().strip(".")
    allowed_extensions = ["pdf", "doc", "docx", "ppt", "pptx", "txt"]

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: .{file_extension}. Allowed types: {', '.join(allowed_extensions)}"
        )

    # Save to temp file
    temp_file_path = os.path.join(TEMP_DIR, filename)
    logger.info(f"Receiving file: {filename}. Saving temporarily to: {temp_file_path}")

    try:
        # Write file in chunks to prevent high memory usage
        with open(temp_file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunk size
                buffer.write(chunk)

        # Parse file text
        extracted_pages = ingestion_service.extract_text(temp_file_path, file_extension)

        # Generate a unique document ID
        document_id = str(uuid.uuid4())

        # Generate semantic chunks with detailed metadata
        chunks_data = chunking_service.chunk_document(
            pages=extracted_pages,
            document_id=document_id,
            source_filename=filename
        )

        # Index chunks in Qdrant Vector Store (BGE-M3 Embeddings)
        logger.info(f"Indexing chunks in Qdrant collection for document: {filename}")
        vector_store_service.upsert_document_chunks(chunks_data)

        total_characters = sum(len(p["text"]) for p in extracted_pages)
        logger.info(f"Successfully processed {filename}. Extracted {len(extracted_pages)} pages, {len(chunks_data)} chunks, {total_characters} characters.")

        return DocumentIngestionResponse(
            filename=filename,
            extension=file_extension,
            total_pages=len(extracted_pages),
            total_characters=total_characters,
            content=[
                PageContent(page_number=p["page_number"], text=p["text"]) 
                for p in extracted_pages
            ],
            chunks=[
                ChunkContent(
                    chunk_index=c["chunk_index"],
                    document_id=c["document_id"],
                    source_filename=c["source_filename"],
                    page_number=c["page_number"],
                    text=c["text"],
                    word_count=c["word_count"],
                    char_count=c["char_count"]
                )
                for c in chunks_data
            ]
        )

    except Exception as e:
        logger.error(f"Error during ingestion of {filename}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Cleaned up temp file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to delete temp file {temp_file_path}: {str(cleanup_error)}")
