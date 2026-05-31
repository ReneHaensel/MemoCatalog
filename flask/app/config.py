from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = normalize_database_url(
        os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'memocatalog.db'}")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "app" / "static" / "uploads"))
    WTF_CSRF_TIME_LIMIT = None
    ITEMS_PER_PAGE = int(os.getenv("ITEMS_PER_PAGE", "12"))
    GEOCODE_CACHE_PATH = os.getenv(
        "GEOCODE_CACHE_PATH", str(BASE_DIR / "data" / "geocode_cache.json")
    )
    GEOCODING_PROVIDER = os.getenv("GEOCODING_PROVIDER", "nominatim")
    GEOCODING_USER_AGENT = os.getenv(
        "GEOCODING_USER_AGENT",
        "MemoCatalog/1.0 (local Memo-Euro collection manager)",
    )
    GEOCODING_TIMEOUT = int(os.getenv("GEOCODING_TIMEOUT", "10"))
    GEOCODING_RATE_LIMIT_SECONDS = float(os.getenv("GEOCODING_RATE_LIMIT_SECONDS", "1.1"))
