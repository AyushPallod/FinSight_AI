import logging
import re
from typing import Any

from rank_bm25 import BM25Okapi

from app.services.vector_store import vector_store_service

logger = logging.getLogger(__name__)


def tokenize(text: str) -> list[str]:
    """
    Standard clean tokenizer: converts text to lowercase and extracts alphanumeric words.
    """
    if not text:
        return []
    return re.findall(r"\w+", text.lower())


class RetrievalService:
    def dense_search(self, query: str, limit: int = 10) -> list[Any]:
        """
        Executes a dense vector similarity search against Qdrant.
        """
        try:
            # Generate embedding vector for the search query
            query_vector = vector_store_service.model.encode(query).tolist()

            with vector_store_service.get_client() as client:
                response = client.query_points(
                    collection_name=vector_store_service.collection_name,
                    query=query_vector,
                    limit=limit,
                )
            return response.points
        except Exception as e:
            logger.error(f"Error during dense search: {e!s}", exc_info=True)
            return []

    def sparse_search(self, query: str, limit: int = 10) -> list[Any]:
        """
        Executes a BM25 sparse keyword search over all currently indexed chunks.
        """
        try:
            # 1. Retrieve all points from Qdrant to build the corpus
            with vector_store_service.get_client() as client:
                scroll_result, _ = client.scroll(
                    collection_name=vector_store_service.collection_name,
                    limit=10000,
                    with_payload=True,
                    with_vectors=False,  # We do not need vectors for BM25
                )

            if not scroll_result:
                return []

            # 2. Tokenize text payloads
            corpus_texts = [point.payload.get("text", "") for point in scroll_result]
            tokenized_corpus = [tokenize(text) for text in corpus_texts]

            # 3. Compile BM25 index in memory
            bm25 = BM25Okapi(tokenized_corpus)

            # 4. Score documents against the query
            query_tokens = tokenize(query)
            scores = bm25.get_scores(query_tokens)

            # 5. Pack, filter, and sort results
            scored_points = list(zip(scroll_result, scores))
            # Keep only items with a positive score (at least one term matched)
            matched_points = [item for item in scored_points if item[1] > 0.0]
            matched_points.sort(key=lambda x: x[1], reverse=True)

            # Return sorted Qdrant points
            return [item[0] for item in matched_points[:limit]]

        except Exception as e:
            logger.error(f"Error during sparse search: {e!s}", exc_info=True)
            return []

    def hybrid_search(
        self, query: str, limit: int = 5, rrf_k: int = 60
    ) -> list[dict[str, Any]]:
        """
        Performs hybrid search by combining Dense and Sparse search results
        using Reciprocal Rank Fusion (RRF).
        """
        logger.info(
            f"Executing hybrid search for query: '{query}' (limit={limit}, k={rrf_k})"
        )

        # We search for slightly more than the limit in each system to ensure
        # a good overlap before merging ranks.
        search_buffer = limit * 3

        dense_hits = self.dense_search(query, limit=search_buffer)
        sparse_hits = self.sparse_search(query, limit=search_buffer)

        rrf_scores = {}
        point_map = {}

        # 1. Process Dense ranks
        for rank, hit in enumerate(dense_hits):
            point_id = hit.id
            point_map[point_id] = hit

            rank_pos = rank + 1  # RRF is 1-indexed
            rrf_scores[point_id] = rrf_scores.get(point_id, 0.0) + (
                1.0 / (rrf_k + rank_pos)
            )

        # 2. Process Sparse (BM25) ranks
        for rank, hit in enumerate(sparse_hits):
            point_id = hit.id
            point_map[point_id] = hit

            rank_pos = rank + 1  # RRF is 1-indexed
            rrf_scores[point_id] = rrf_scores.get(point_id, 0.0) + (
                1.0 / (rrf_k + rank_pos)
            )

        if not rrf_scores:
            logger.info("Hybrid search returned no matches.")
            return []

        # 3. Sort points by descending RRF score
        sorted_ids = sorted(
            rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True
        )

        # 4. Construct final structured payload
        fused_results = []
        for point_id in sorted_ids[:limit]:
            hit = point_map[point_id]
            fused_results.append(
                {
                    "id": point_id,
                    "text": hit.payload.get("text", ""),
                    "page_number": hit.payload.get("page_number", 1),
                    "chunk_index": hit.payload.get("chunk_index", 0),
                    "document_id": hit.payload.get("document_id", ""),
                    "source_filename": hit.payload.get("source_filename", "Unknown"),
                    "word_count": hit.payload.get("word_count", 0),
                    "char_count": hit.payload.get("char_count", 0),
                    "rrf_score": round(rrf_scores[point_id], 6),
                }
            )

        logger.info(f"Hybrid search returned {len(fused_results)} fused results.")
        return fused_results


retrieval_service = RetrievalService()
