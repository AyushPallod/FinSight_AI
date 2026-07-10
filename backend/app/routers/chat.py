import logging
import os
from typing import List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.services.retrieval import retrieval_service
from app.services.llm import llm_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

# Request & Response schemas
class ChatRequest(BaseModel):
    query: str
    limit: int = 4

class CitationItem(BaseModel):
    document: str
    page: int
    snippet: str

class ChatResponse(BaseModel):
    query: str
    answer: str
    citations: List[CitationItem]

@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_interaction(request: ChatRequest):
    """
    RAG chat endpoint.
    Retrieves relevant document chunks, prompt-grounds the local Llama 3.2 model,
    and returns a structured cited answer with document source references.
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat query cannot be empty."
        )

    try:
        logger.info(f"Received RAG chat request for query: '{query}'")
        
        # 1. Retrieve top-k context chunks via our Hybrid Search
        chunks = retrieval_service.hybrid_search(
            query=query,
            limit=request.limit
        )

        # 2. Query local Ollama model for grounded answer
        answer = await llm_service.generate_answer(
            query=query,
            chunks=chunks
        )

        # 3. Filter citations based on model's explicit citations
        # If the model says it doesn't know, we return empty citations.
        # Otherwise, if it cites specific files, we filter the return list to matches.
        # If no explicit filenames are written, we return all retrieved context chunks as citations.
        is_grounding_reject = "do not contain the information required" in answer.lower()
        
        citations = []
        if not is_grounding_reject:
            # Check if the LLM wrote any retrieved filename in its text response
            has_explicit_citations = any(
                (c["source_filename"].lower() in answer.lower() or 
                 os.path.splitext(c["source_filename"])[0].lower() in answer.lower())
                for c in chunks
            )

            seen_citations = set()
            for c in chunks:
                filename = c["source_filename"]
                page = c["page_number"]
                snippet = c["text"]

                if has_explicit_citations:
                    # Filter: Only include chunks whose filenames are explicitly mentioned in LLM text
                    is_cited = (
                        filename.lower() in answer.lower() or 
                        os.path.splitext(filename)[0].lower() in answer.lower()
                    )
                    if not is_cited:
                        continue

                citation_key = (filename, page, snippet)
                if citation_key not in seen_citations:
                    seen_citations.add(citation_key)
                    citations.append(
                        CitationItem(
                            document=filename,
                            page=page,
                            snippet=snippet
                        )
                    )

        return ChatResponse(
            query=query,
            answer=answer,
            citations=citations
        )

    except Exception as e:
        logger.error(f"Failed to process RAG chat request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating RAG response: {str(e)}"
        )
