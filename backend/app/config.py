from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # PostgreSQL in Docker (see docker-compose.yml); SQLite for zero-setup local runs.
    DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'ibmode.db').as_posix()}"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    DEBUG: bool = False
    # Serverless (e.g. Vercel): requests for one game can hit different instances, so the
    # per-process state cache must be off and the database row lock serialises actions.
    SERVERLESS: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("DATABASE_URL")
    @classmethod
    def _sqlalchemy_scheme(cls, v: str) -> str:
        # Hosted Postgres providers hand out postgres:// or postgresql:// URLs.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg2://" + v[len(prefix):]
        return v


settings = Settings()
