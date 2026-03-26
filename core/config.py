from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Grants Platform API"
    environment: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # LLM APIs
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""           # ← Groq (gratuit, fiable)

    # Search APIs
    tavily_api_key: str = ""
    serp_api_key: str = ""

    # Database
    database_url: str = "postgresql://postgres:postgres@db:5432/grants_db"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8001
    chroma_path: str = "./chroma_data"  # ✨ NOUVEAU

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "grants-platform-pfe"

    # LLM Models — Groq LLaMA 3.3 70B (gratuit)
    extraction_model: str = "llama-3.3-70b-versatile"
    generation_model: str = "llama-3.3-70b-versatile"
    vision_model: str = "llama-3.3-70b-versatile"

    # ✨ NOUVEAU: Embedding Settings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Upload
    upload_dir: str = "uploads"
    max_file_size_mb: int = 20

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()