from __future__ import annotations

from flask import Blueprint, render_template, url_for
from flask_login import current_user
from sqlalchemy import distinct, func

from app.extensions import db
from app.models import BaseNote, UserCollectionEntry, Variant, WishlistEntry

bp = Blueprint("main", __name__)


def build_stats() -> dict[str, object]:
    total_notes = BaseNote.query.filter_by(is_active=True).count()
    total_variants = Variant.query.count()
    collected_notes = 0
    collected_variants = 0
    countries: list[tuple[str, int]] = []
    years: list[tuple[int, int]] = []
    latest_entries: list[UserCollectionEntry] = []

    if current_user.is_authenticated:
        entries = UserCollectionEntry.query.filter_by(user_id=current_user.id)
        collected_notes = (
            entries.filter(UserCollectionEntry.variant_id.is_(None))
            .with_entities(func.count(distinct(UserCollectionEntry.base_note_id)))
            .scalar()
            or 0
        )
        collected_variants = entries.filter(UserCollectionEntry.variant_id.is_not(None)).count()
        countries = (
            entries.join(BaseNote)
            .with_entities(BaseNote.country, func.count(UserCollectionEntry.id))
            .group_by(BaseNote.country)
            .order_by(func.count(UserCollectionEntry.id).desc())
            .all()
        )
        years = (
            entries.join(BaseNote)
            .with_entities(BaseNote.issue_year, func.count(UserCollectionEntry.id))
            .group_by(BaseNote.issue_year)
            .order_by(BaseNote.issue_year.desc())
            .all()
        )
        latest_entries = entries.order_by(UserCollectionEntry.created_at.desc()).limit(5).all()

    progress = round((collected_notes / total_notes) * 100, 1) if total_notes else 0
    return {
        "total_notes": total_notes,
        "total_variants": total_variants,
        "collected_notes": collected_notes,
        "collected_variants": collected_variants,
        "progress": progress,
        "countries": countries,
        "years": years,
        "latest_entries": latest_entries,
    }


@bp.route("/")
def index():
    latest_notes = BaseNote.query.filter_by(is_active=True).order_by(BaseNote.created_at.desc()).limit(6).all()
    location_notes = (
        BaseNote.query.filter_by(is_active=True)
        .filter(BaseNote.latitude.is_not(None), BaseNote.longitude.is_not(None))
        .order_by(BaseNote.country.asc(), BaseNote.title.asc())
        .all()
    )
    collected_note_ids: set[int] = set()
    wishlist_note_ids: set[int] = set()
    if current_user.is_authenticated:
        collected_note_ids = {
            row[0]
            for row in db.session.query(UserCollectionEntry.base_note_id)
            .filter_by(user_id=current_user.id)
            .distinct()
            .all()
        }
        wishlist_note_ids = {
            row[0]
            for row in db.session.query(WishlistEntry.base_note_id)
            .filter_by(user_id=current_user.id)
            .distinct()
            .all()
        }

    map_locations = [
        {
            "id": note.id,
            "title": note.title,
            "country": note.country,
            "region_or_city": note.region_or_city,
            "catalog_number": note.catalog_number,
            "latitude": note.latitude,
            "longitude": note.longitude,
            "url": url_for("catalog.detail", note_id=note.id),
            "status": "collected"
            if note.id in collected_note_ids
            else "wishlist"
            if note.id in wishlist_note_ids
            else "default",
        }
        for note in location_notes
    ]
    return render_template(
        "index.html",
        stats=build_stats(),
        latest_notes=latest_notes,
        map_locations=map_locations,
    )


@bp.route("/stats")
def stats():
    return render_template("stats/index.html", stats=build_stats())
