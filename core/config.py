from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """
    Configuration centralisée de l'application.
    Les variables d'environnement surchargent les valeurs par défaut.
    """

    # ────────────────────────────────────────────────────────
    # 🏗️ APPLICATION
    # ────────────────────────────────────────────────────────
    app_name: str = "Grants Platform API"
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"

    # ────────────────────────────────────────────────────────
    # 🔐 JWT & SECURITY
    # ────────────────────────────────────────────────────────
    secret_key: str = os.getenv(
        "SECRET_KEY",
        "change-me-in-production-this-is-unsafe"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    )
    refresh_token_expire_days: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )

    # ────────────────────────────────────────────────────────
    # 🤖 LLM API KEYS (From Environment Only)
    # ────────────────────────────────────────────────────────
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")

    # ────────────────────────────────────────────────────────
    # 🔍 SEARCH API KEYS (From Environment Only)
    # ─────────────────��──────────────────────────────────────
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    serp_api_key: str = os.getenv("SERP_API_KEY", "")

    # ────────────────────────────────────────────────────────
    # 🗄️ DATABASE
    # ────────────────────────────────────────────────────────
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./grants.db"
    )

    # ────────────────────────────────────────────────────────
    # 🗄️ REDIS (Cache & Queue)
    # ────────────────────────────────────────────────────────
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ────────────────────────────────────────────────────────
    # 📊 EMBEDDING & VECTOR STORE
    # ────────────────────────────────────────────────────────
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL",
        "all-MiniLM-L6-v2"
    )
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "384"))
    chroma_path: str = os.getenv("CHROMA_PATH", "./chroma_data")

    # ────────────────────────────────────────────────────────
    # 🔗 LANGSMITH (Optional - Debugging)
    # ────────────────────────────────────────────────────────
    langchain_tracing_v2: bool = (
        os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    )
    langchain_api_key: str = os.getenv("LANGCHAIN_API_KEY", "")
    langchain_project: str = os.getenv(
        "LANGCHAIN_PROJECT",
        "grants-platform-pfe"
    )

    # ────────────────────────────────────────────────────────
    # 📧 EMAIL (Optional)
    # ────────────────────────────────────────────────────────
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")

    # ────────────────────────────────────────────────────────
    # 📤 FILE UPLOAD
    # ────────────────────────────────────────────────────────
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))

    # ────────────────────────────────────────────────────────
    # 🤖 LLM MODELS
    # ────────────────────────────────────────────────────────
    extraction_model: str = "llama-3.3-70b-versatile"  # Groq
    generation_model: str = "llama-3.3-70b-versatile"  # Groq
    vision_model: str = "llama-3.3-70b-versatile"      # Groq

    class Config:
        env_file = ".env"
        case_sensitive = False

    def validate_production(self):
        """Valider les configurations de production"""
        if self.environment == "production":
            if self.secret_key == "change-me-in-production-this-is-unsafe":
                raise ValueError("❌ SECRET_KEY non configurée en production!")
            if not self.groq_api_key and not self.anthropic_api_key:
                raise ValueError("❌ Aucune clé LLM configurée en production!")


@lru_cache()
def get_settings() -> Settings:
    """
    Retourner les settings (avec cache).
    Appeler une seule fois au démarrage.
    """
    settings = Settings()
    if settings.environment == "production":
        settings.validate_production()
    return settings


# Instance globale
settings = get_settings()