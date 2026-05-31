from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app

from app.extensions import db
from app.models import BaseNote, GeocodeCache

_last_request_at = 0.0


@dataclass(frozen=True)
class GeocodeResult:
    success: bool
    message: str
    query: str | None = None


@dataclass(frozen=True)
class GeocodeBatchResult:
    processed: int
    updated: int
    failed: int


def _join_query_parts(parts: list[str | None]) -> str:
    return ", ".join(part.strip() for part in parts if part and part.strip())


def build_geocode_query(note: BaseNote) -> str:
    return _join_query_parts([note.address, note.region_or_city, note.country])


def build_geocode_queries(note: BaseNote) -> list[str]:
    candidates = [
        [note.address, note.region_or_city, note.country],
        [note.title, note.region_or_city, note.country],
        [note.address, note.country],
        [note.title, note.country],
        [note.region_or_city, note.country],
    ]
    queries: list[str] = []
    for parts in candidates:
        query = _join_query_parts(parts)
        if query and query not in queries:
            queries.append(query)
    return queries


def _sync_json_cache(query: str, latitude: float, longitude: float) -> None:
    path = Path(current_app.config["GEOCODE_CACHE_PATH"])
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, dict[str, float]] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    data[query] = {"latitude": latitude, "longitude": longitude}
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _rate_limit() -> None:
    global _last_request_at

    seconds = current_app.config["GEOCODING_RATE_LIMIT_SECONDS"]
    elapsed = time.monotonic() - _last_request_at
    if elapsed < seconds:
        time.sleep(seconds - elapsed)
    _last_request_at = time.monotonic()


def _search_nominatim(query: str) -> tuple[float, float] | None:
    _rate_limit()
    params = urlencode({"q": query, "format": "jsonv2", "limit": 1})
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": current_app.config["GEOCODING_USER_AGENT"],
        },
    )

    try:
        with urlopen(request, timeout=current_app.config["GEOCODING_TIMEOUT"]) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        current_app.logger.warning("Nominatim HTTP error for %r: %s", query, exc)
        return None
    except (URLError, TimeoutError, OSError) as exc:
        current_app.logger.warning("Nominatim connection error for %r: %s", query, exc)
        return None
    except json.JSONDecodeError as exc:
        current_app.logger.warning("Nominatim returned invalid JSON for %r: %s", query, exc)
        return None

    if not payload:
        current_app.logger.info("Nominatim found no coordinates for %r", query)
        return None

    try:
        first = payload[0]
        return round(float(first["lat"]), 6), round(float(first["lon"]), 6)
    except (KeyError, TypeError, ValueError) as exc:
        current_app.logger.warning("Nominatim response missing lat/lon for %r: %s", query, exc)
        return None


def _lookup_real_coordinates(query: str) -> tuple[float, float] | None:
    provider = current_app.config["GEOCODING_PROVIDER"].lower()
    if provider != "nominatim":
        current_app.logger.warning("Unsupported geocoding provider configured: %s", provider)
        return None
    return _search_nominatim(query)


def geocode_note_result(note: BaseNote, *, force: bool = False) -> GeocodeResult:
    if note.has_coordinates and not force:
        return GeocodeResult(False, "Der Hauptschein hat bereits Koordinaten.")

    queries = build_geocode_queries(note)
    if not queries:
        return GeocodeResult(False, "Adresse, Ort, Land oder Titel fehlen fuer die Suche.")

    provider = current_app.config["GEOCODING_PROVIDER"].lower()
    if provider != "nominatim":
        return GeocodeResult(False, f"Unbekannter Geocoding-Provider: {provider}")

    for query in queries:
        cached = GeocodeCache.query.filter_by(query_text=query).first()
        if cached and cached.status == "found" and cached.latitude is not None and cached.longitude is not None and not force:
            note.latitude = cached.latitude
            note.longitude = cached.longitude
            return GeocodeResult(True, "Koordinaten aus dem Cache uebernommen.", query)

        result = _lookup_real_coordinates(query)
        if result is None:
            if cached is None:
                db.session.add(GeocodeCache(query_text=query, status="not_found"))
            elif force:
                cached.status = "not_found"
                cached.latitude = None
                cached.longitude = None
            continue

        latitude, longitude = result
        if cached is None:
            cached = GeocodeCache(query_text=query)
            db.session.add(cached)
        cached.latitude = latitude
        cached.longitude = longitude
        cached.status = "found"
        note.latitude = latitude
        note.longitude = longitude
        _sync_json_cache(query, latitude, longitude)
        return GeocodeResult(True, "Echte Koordinaten wurden berechnet.", query)

    current_app.logger.warning("No geocoding result for note %s. Tried: %s", note.id, queries)
    if force:
        note.latitude = None
        note.longitude = None
    return GeocodeResult(
        False,
        "Keine Koordinaten gefunden oder Geocoding-Dienst nicht erreichbar. Versuchte Suche: "
        + " | ".join(queries),
        queries[0],
    )


def geocode_note(note: BaseNote, *, force: bool = False) -> bool:
    return geocode_note_result(note, force=force).success


def geocode_missing_notes(limit: int | None = None) -> GeocodeBatchResult:
    query = BaseNote.query.filter(BaseNote.latitude.is_(None) | BaseNote.longitude.is_(None)).order_by(BaseNote.id.asc())
    if limit is not None:
        query = query.limit(limit)
    notes = query.all()
    count = 0
    for note in notes:
        if geocode_note(note):
            count += 1
    db.session.commit()
    return GeocodeBatchResult(processed=len(notes), updated=count, failed=len(notes) - count)


def geocode_all_notes(limit: int | None = None) -> GeocodeBatchResult:
    query = BaseNote.query.order_by(BaseNote.id.asc())
    if limit is not None:
        query = query.limit(limit)
    notes = query.all()
    count = 0
    for note in notes:
        if geocode_note(note, force=True):
            count += 1
    db.session.commit()
    return GeocodeBatchResult(processed=len(notes), updated=count, failed=len(notes) - count)
