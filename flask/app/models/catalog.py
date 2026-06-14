from __future__ import annotations

from datetime import datetime
from enum import Enum

from app.extensions import db


class VariantType(str, Enum):
    SPECIMEN = "Specimen"
    PROBEDRUCK = "Probedruck"
    AUFDRUCK = "Aufdruck"
    GELOCHT = "Gelocht"
    ANNIVERSARY = "Anniversary"


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class BaseNote(TimestampMixin, db.Model):
    __tablename__ = "base_notes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    country = db.Column(db.String(120), nullable=False, index=True)
    region_or_city = db.Column(db.String(160), nullable=True, index=True)
    address = db.Column(db.String(255), nullable=True, index=True)
    issue_year = db.Column(db.Integer, nullable=True, index=True)
    variant_type = db.Column(db.String(50), nullable=True, index=True)
    front_img = db.Column(db.String(500), nullable=True)
    back_img = db.Column(db.String(500), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    catalog_number = db.Column(db.String(100), unique=True, nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)

    collection_entries = db.relationship(
        "UserCollectionEntry", back_populates="base_note", cascade="all, delete-orphan"
    )
    wishlist_entries = db.relationship(
        "WishlistEntry", back_populates="base_note", cascade="all, delete-orphan"
    )

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None


class GeocodeCache(TimestampMixin, db.Model):
    __tablename__ = "geocode_cache"

    id = db.Column(db.Integer, primary_key=True)
    query_text = db.Column("query", db.String(500), unique=True, nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(40), default="cached", nullable=False)


class ImportJob(TimestampMixin, db.Model):
    __tablename__ = "import_jobs"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(40), default="preview", nullable=False, index=True)
    total_rows = db.Column(db.Integer, default=0, nullable=False)
    processed_rows = db.Column(db.Integer, default=0, nullable=False)
    new_count = db.Column(db.Integer, default=0, nullable=False)
    update_count = db.Column(db.Integer, default=0, nullable=False)
    unchanged_count = db.Column(db.Integer, default=0, nullable=False)
    skipped_count = db.Column(db.Integer, default=0, nullable=False)
    geocode_count = db.Column(db.Integer, default=0, nullable=False)
    warnings = db.Column(db.JSON, default=list, nullable=False)
    payload = db.Column(db.JSON, default=list, nullable=False)
