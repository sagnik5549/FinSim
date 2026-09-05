from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://finsim:finsim_secret@localhost:5432/finsim"
    SECRET_KEY: str = "finsim-secret-key-change-in-production"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
