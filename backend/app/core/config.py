from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite by default (single-user/local dev). Change to Postgres later.
    database_url: str = "sqlite:///./app.db"

    # CORS
    cors_allow_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "*"]


settings = Settings()

