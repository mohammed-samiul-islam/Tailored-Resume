"""Application configuration."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """App settings from environment."""

    app_name: str = "Tailored Resume API"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./tailored_resume.db"

    # JWT
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # File upload
    max_upload_bytes: int = 4 * 1024 * 1024  # 4MB
    allowed_resume_extensions: set[str] = {"pdf", "docx"}
    upload_dir: str = "uploads"

    # OpenAI (for parser fallback, job analyzer, resume generator)
    openai_api_key: str = ""

    # Minimum ATS score to save a generated resume (reject below this)
    min_ats_score: int = 90

    # CORS origins (comma-separated, e.g. "http://localhost:3000,https://myapp.com")
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Optional: Supabase for storage (if set, use Supabase; else local upload_dir)
    supabase_url: str = ""
    supabase_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
