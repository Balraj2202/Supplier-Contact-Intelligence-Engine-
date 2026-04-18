"""
config.py — App settings loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Gemini (free)
    gemini_api_key: str = ""

    # Anthropic (optional, paid)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-6"

    # Google Sheets (optional)
    google_service_account_file: str = "credentials/google-service-account.json"
    google_sheet_id: str = ""
    google_sheet_tab: str = "Suppliers"

    # Processing
    batch_size: int = 3
    max_pages_per_supplier: int = 5
    crawl_delay_seconds: float = 1.0

    # App
    log_level: str = "INFO"
    port: int = 8000
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
