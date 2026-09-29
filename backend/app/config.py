from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # PostgreSQL in Docker (see docker-compose.yml); SQLite for zero-setup local runs.
    DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'ibmode.db').as_posix()}"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    DEBUG: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
