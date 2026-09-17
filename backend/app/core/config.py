import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """VERIDOC Sovereign Document Forensics Platform Settings & Configuration."""
    PROJECT_NAME: str = "VERIDOC"
    PROJECT_VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"

    # Database (SQLite local — immutable evidence ledger)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./veridoc.db"
    )

    # Security and Authentication
    DEFAULT_API_KEY: str = os.getenv("VERIDOC_API_KEY", "ssb-veridoc-secret-key-2026")
    ALLOWED_HOSTS: List[str] = ["*"]

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "120/minute"

    # AI Forensics Thresholds
    TIER1_RISK_THRESHOLD: float = 0.30
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)

    # API Setu (apisetu.gov.in) — Government Master Registry Bridge
    API_SETU_BASE_URL: str = os.getenv("API_SETU_BASE_URL", "https://apisetu.gov.in")
    API_SETU_CLIENT_ID: str = os.getenv("API_SETU_CLIENT_ID", "")
    API_SETU_CLIENT_SECRET: str = os.getenv("API_SETU_CLIENT_SECRET", "")

    # Offline Sandbox Mode — set True for offline demonstrations (no live VPN/API needed)
    OFFLINE_SANDBOX_MODE: bool = os.getenv("OFFLINE_SANDBOX_MODE", "true").lower() == "true"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
