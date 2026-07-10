from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "FinSight AI"
    API_V1_STR: str = "/api/v1"
    
    # Qdrant Vector DB Settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    
    # Ollama LLM Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
