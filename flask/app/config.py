from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'memocatalog.db'}"
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
