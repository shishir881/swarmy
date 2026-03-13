"""
Application configuration using pydantic-settings.

Loads environment variables from a .env file and provides typed access
to all configuration parameters needed by the application.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database connection string (SQLite for local dev, PostgreSQL for production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./event_command_center.db"

    # Groq API key for Llama-3 access
    GROQ_API_KEY: str = ""

    # ChromaDB persistence directory
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # LLM model identifier (Groq-hosted)
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    # Gmail SMTP settings for sending real emails
    SMTP_USER: str = ""          # e.g. yourname@gmail.com
    SMTP_APP_PASSWORD: str = ""  # Gmail App Password (not your regular password)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Singleton settings instance
settings = Settings()
