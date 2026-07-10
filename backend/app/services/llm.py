import logging
import httpx
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    async def generate_answer(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Queries the locally running Ollama model using the provided context chunks.
        Enforces strict grounding guidelines and inline citation instructions.
        """
        if not chunks:
            return (
                "I am sorry, but the provided documents do not contain the "
                "information required to answer your question."
            )

        # 1. Format retrieval chunks as marked context segments
        context_blocks = []
        for chunk in chunks:
            filename = chunk.get("source_filename", "Unknown")
            page = chunk.get("page_number", 1)
            text = chunk.get("text", "")
            context_blocks.append(
                f"--- DOCUMENT SOURCE: {filename} | PAGE: {page} ---\n{text}\n"
            )
        
        context_text = "\n".join(context_blocks)

        # 2. Build system-level grounding guidelines
        system_instructions = (
            "You are FinSight AI, a financial document intelligence assistant.\n"
            "Answer the user's question objectively and accurately using ONLY the provided Document Sources below.\n"
            "If the provided Document Sources do not contain enough facts to answer the question, state exactly:\n"
            "'I am sorry, but the provided documents do not contain the information required to answer your question.'\n"
            "Do not make up facts, draw outside assumptions, or use external knowledge.\n\n"
            "CRITICAL: For every fact, number, or claim you state, you MUST cite the source document name and page number. "
            "Format your citations inline precisely as [Source: filename, Page X].\n"
        )

        prompt = (
            f"{system_instructions}\n"
            f"Document Sources:\n"
            f"{context_text}\n"
            f"User Question: {query}\n\n"
            f"Answer:"
        )

        # 3. Post HTTP request to local Ollama API
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0  # Zero temperature for deterministic factual responses
            }
        }

        try:
            logger.info(f"Sending prompt to local Ollama API ({url}) using model '{self.model}'...")
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=60.0)
                
            if response.status_code != 200:
                logger.error(f"Ollama API returned non-200 status: {response.status_code} - {response.text}")
                return "Error: Failed to connect to the local LLM generation service."
                
            result = response.json()
            answer = result.get("response", "").strip()
            return answer

        except httpx.RequestError as e:
            logger.error(f"HTTP connection error to Ollama at {url}: {str(e)}")
            return "Error: Could not reach the local Ollama service. Please make sure Ollama is running."
        except Exception as e:
            logger.error(f"Unexpected error during answer generation: {str(e)}", exc_info=True)
            return "Error: An unexpected error occurred while generating the answer."

llm_service = LLMService()
