import logging
from typing import List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.services.retrieval import retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/search",
    tags=["search"]
)

# Request & Response schemas
class SearchRequest(BaseModel):
    query: str
    limit: int = 5

class SearchResultItem(BaseModel):
    id: str
    text: str
    page_number: int
    chunk_index: int
    document_id: str
    source_filename: str
    word_count: int
    char_count: int
    rrf_score: float

class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]

@router.post("", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search_documents(request: SearchRequest):
    """
    Perform a hybrid search (BM25 + Dense Vector) using Reciprocal Rank Fusion (RRF).
    Returns the top-k document chunks matching the query context.
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty."
        )

    try:
        logger.info(f"Received search request for query: '{query}'")
        fused_results = retrieval_service.hybrid_search(
            query=query,
            limit=request.limit
        )

        return SearchResponse(
            query=query,
            total_results=len(fused_results),
            results=[
                SearchResultItem(
                    id=item["id"],
                    text=item["text"],
                    page_number=item["page_number"],
                    chunk_index=item["chunk_index"],
                    document_id=item["document_id"],
                    source_filename=item["source_filename"],
                    word_count=item["word_count"],
                    char_count=item["char_count"],
                    rrf_score=item["rrf_score"]
                )
                for item in fused_results
            ]
        )

    except Exception as e:
        logger.error(f"Failed to perform search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while executing the search query: {str(e)}"
        )
