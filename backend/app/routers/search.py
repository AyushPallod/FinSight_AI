import json
import logging
import time

import redis
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.metrics import (
    cache_hits_total,
    cache_misses_total,
    retrieval_latency_seconds,
)
from app.models.user import User
from app.services.retrieval import retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


# Connect to Redis with string decoding enabled
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


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
    results: list[SearchResultItem]


@router.post("", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search_documents(
    request: SearchRequest, current_user: User = Depends(get_current_user)
):
    """
    Perform a hybrid search (BM25 + Dense Vector) using Reciprocal Rank Fusion (RRF).
    Caches results in Redis for identical queries for 5 minutes, scoped by user.
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty.",
        )

    # Scoped cache key to ensure user A's query doesn't leak to user B
    cache_key = f"search_cache:{current_user.id}:{query}:{request.limit}"

    # Try fetching from cache
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache HIT for query: '{query}' (User ID: {current_user.id})")
            cache_hits_total.inc()
            return json.loads(cached_data)
    except Exception as re:
        logger.warning(
            f"Failed to read from Redis search cache: {re!s}. Falling back to direct search."
        )

    try:
        logger.info(f"Cache MISS. Executing hybrid search for query: '{query}'")
        cache_misses_total.inc()

        start_time = time.perf_counter()
        fused_results = retrieval_service.hybrid_search(
            query=query, limit=request.limit
        )
        duration = time.perf_counter() - start_time
        retrieval_latency_seconds.observe(duration)

        response_data = SearchResponse(
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
                    rrf_score=item["rrf_score"],
                )
                for item in fused_results
            ],
        )

        # Cache results in Redis for 5 minutes (300 seconds)
        try:
            redis_client.setex(cache_key, 300, response_data.model_dump_json())
            logger.info(f"Cached search results in Redis: '{cache_key}'")
        except Exception as re:
            logger.warning(f"Failed to write to Redis search cache: {re!s}")

        return response_data

    except Exception as e:
        logger.error(f"Failed to perform search: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while executing the search query: {e!s}",
        )
