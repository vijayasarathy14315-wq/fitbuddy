from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "FitBuddy – AI Fitness Plan Generator"

    environment: str = "development"

    database_url: str = "sqlite:///./fitbuddy.db"

    # Gemini
    gemini_api_key: str = ""

    # Keep these configurable because Gemini model availability can change.
    workout_model: str = "gemini-3.8-flash"
    nutrition_model: str = "gemini-3.8-flash"

    # Admin
    admin_username: str = "admin"
    admin_password: str = "change-me"

    # Development fallback
    allow_mock_ai: bool = True

    max_feedback_length: int = 1200

    @field_validator("allow_mock_ai", mode="before")
    @classmethod
    def parse_allow_mock_ai(cls, value):
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()