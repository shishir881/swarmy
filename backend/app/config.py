"""
Application configuration using pydantic-settings.

Loads environment variables from a .env file and provides typed access
to all configuration parameters needed by the application.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from enviroanment variables."""

    # Database connection string — defaults to Neon PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://neondb_owner:npg_03CchjoxuSye@ep-late-credit-a1rnvk13-pooler.ap-southeast-1.aws.neon.tech/neondb"

    # Groq API key for Llama-3 access
    GROQ_API_KEY: str = ""

    # ChromaDB persistence directory
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # LLM model identifier (Groq-hosted)
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    SMTP_USER: str = ""          # e.g. yourname@gmail.com
    SMTP_APP_PASSWORD: str = ""  # Gmail App Password (not your regular password)

    # JWT authentication settings
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Google OAuth settings
    GOOGLE_CLIENT_ID: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Singleton settings instance
settings = Settings()


