from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.extensions import db
from app.models import BaseNote, GeocodeCache, User, UserCollectionEntry, WishlistEntry
from app.services.geocoding import geocode_all_notes, geocode_missing_notes, geocode_note
from app.services.imports import create_import_preview, run_import_batch


class TestConfig:
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    ITEMS_PER_PAGE = 12
    UPLOAD_FOLDER = "/tmp/memocatalog-test-uploads"
    GEOCODE_CACHE_PATH = "/tmp/memocatalog-test-geocode.json"
    GEOCODE_JSON_CACHE_ENABLED = False
    GEOCODING_PROVIDER = "nominatim"
    GEOCODING_USER_AGENT = "MemoCatalog tests"
    GEOCODING_TIMEOUT = 1
    GEOCODING_RATE_LIMIT_SECONDS = 0
    IMPORT_BATCH_SIZE = 2
    IMPORT_GEOCODE_DURING_IMPORT = False


def test_app_smoke():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        assert b"MemoCatalog" in response.data


def test_navigation_for_guest_only_shows_catalog_menu_item():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        client = app.test_client()
        response = client.get("/")

        assert response.status_code == 200
        assert b"Katalog" in response.data
        assert b'href="/collection"' not in response.data
        assert b'href="/collection/wishlist"' not in response.data
        assert b'href="/stats"' not in response.data
        assert b'href="/admin"' not in response.data


def test_navigation_for_logged_in_user_shows_private_menu_items():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        user = User(username="collector", email="collector@example.test")
        user.set_password("collector123")
        db.session.add(user)
        db.session.commit()

        client = app.test_client()
        client.post("/auth/login", data={"username": "collector", "password": "collector123"})
        response = client.get("/")

        assert response.status_code == 200
        assert b"Katalog" in response.data
        assert b"Sammlung" in response.data
        assert b"Wunschliste" in response.data
        assert b"Stats" in response.data


def test_homepage_renders_world_map_locations():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        note = BaseNote(
            title="Map Note",
            country="Deutschland",
            region_or_city="Berlin",
            issue_year=2026,
            latitude=52.516275,
            longitude=13.377704,
        )
        db.session.add(note)
        db.session.commit()

        client = app.test_client()
        response = client.get("/")

        assert response.status_code == 200
        assert b'id="home-locations-map"' in response.data
        assert b"leaflet.markercluster" in response.data
        assert b"markerClusterGroup" in response.data
        assert b"Map Note" in response.data
        assert b"52.516275" in response.data
        assert b"13.377704" in response.data


def test_homepage_map_locations_include_collection_statuses():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        user = User(username="collector", email="collector@example.test")
        user.set_password("collector123")
        collected_note = BaseNote(
            title="Collected Map Note",
            country="Deutschland",
            issue_year=2026,
            latitude=52.516275,
            longitude=13.377704,
        )
        wishlist_note = BaseNote(
            title="Wishlist Map Note",
            country="Frankreich",
            issue_year=2026,
            latitude=48.85837,
            longitude=2.294481,
        )
        db.session.add_all([user, collected_note, wishlist_note])
        db.session.flush()
        db.session.add(
            UserCollectionEntry(
                user_id=user.id,
                base_note_id=collected_note.id,
                quantity=1,
            )
        )
        db.session.add(
            WishlistEntry(
                user_id=user.id,
                base_note_id=wishlist_note.id,
            )
        )
        db.session.commit()

        client = app.test_client()
        client.post("/auth/login", data={"username": "collector", "password": "collector123"})
        response = client.get("/")

        assert response.status_code == 200
        assert b"Collected Map Note" in response.data
        assert b"Wishlist Map Note" in response.data
        assert b'"status": "collected"' in response.data
        assert b'"status": "wishlist"' in response.data


def test_geocode_note_uses_real_provider(monkeypatch):
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        note = BaseNote(
            title="Test Note",
            country="Deutschland",
            region_or_city="Berlin",
            address="Pariser Platz",
            issue_year=2026,
        )
        db.session.add(note)
        db.session.flush()

        monkeypatch.setattr(
            "app.services.geocoding._lookup_real_coordinates",
            lambda query: (52.516275, 13.377704),
        )

        assert geocode_note(note, force=True) is True
        assert note.latitude == 52.516275
        assert note.longitude == 13.377704


def test_geocode_note_does_not_require_json_cache(monkeypatch):
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        note = BaseNote(
            title="No File Cache",
            country="Deutschland",
            region_or_city="Berlin",
            issue_year=2026,
        )
        db.session.add(note)
        db.session.flush()

        monkeypatch.setattr(
            "app.services.geocoding._lookup_real_coordinates",
            lambda query: (52.516275, 13.377704),
        )

        assert geocode_note(note, force=True) is True
        assert note.latitude == 52.516275


def test_geocode_note_falls_back_to_title_query(monkeypatch):
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        note = BaseNote(
            title="Brandenburger Tor",
            country="Deutschland",
            region_or_city="Berlin",
            address="Unbekannte Adresse",
            issue_year=2026,
        )
        db.session.add(note)
        db.session.flush()

        def fake_lookup(query):
            if query == "Brandenburger Tor, Berlin, Deutschland":
                return (52.516275, 13.377704)
            return None

        monkeypatch.setattr("app.services.geocoding._lookup_real_coordinates", fake_lookup)

        assert geocode_note(note, force=True) is True
        assert note.latitude == 52.516275
        assert note.longitude == 13.377704


def test_geocode_all_notes_processes_more_than_100(monkeypatch):
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        notes = [
            BaseNote(
                title=f"Bulk Note {index}",
                country="Deutschland",
                region_or_city="Berlin",
                address=f"Adresse {index}",
                issue_year=2026,
            )
            for index in range(105)
        ]
        db.session.add_all(notes)
        db.session.commit()

        monkeypatch.setattr(
            "app.services.geocoding._lookup_real_coordinates",
            lambda query: (52.516275, 13.377704),
        )

        result = geocode_all_notes()

        assert result.processed == 105
        assert result.updated == 105
        assert result.failed == 0


def test_force_geocode_clears_old_coordinates_when_no_real_match(monkeypatch):
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        note = BaseNote(
            title="Old Fake Note",
            country="Deutschland",
            region_or_city="Berlin",
            issue_year=2026,
            latitude=44.078692,
            longitude=-9.35186,
        )
        db.session.add(note)
        db.session.commit()

        monkeypatch.setattr("app.services.geocoding._lookup_real_coordinates", lambda query: None)

        assert geocode_note(note, force=True) is False
        assert note.latitude is None
        assert note.longitude is None


def test_geocode_missing_uses_force_mode_like_manual_calculation(monkeypatch):
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        note = BaseNote(
            title="Fresh Note",
            country="Deutschland",
            region_or_city="Berlin",
            address="Pariser Platz",
            issue_year=2026,
        )
        db.session.add(note)
        db.session.add(
            GeocodeCache(
                query_text="Pariser Platz, Berlin, Deutschland",
                latitude=44.078692,
                longitude=-9.35186,
                status="found",
            )
        )
        db.session.commit()

        monkeypatch.setattr(
            "app.services.geocoding._lookup_real_coordinates",
            lambda query: (52.516275, 13.377704),
        )

        result = geocode_missing_notes()

        assert result.processed == 1
        assert result.updated == 1
        assert note.latitude == 52.516275
        assert note.longitude == 13.377704


def test_admin_detail_shows_edit_instead_of_collection_actions():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        admin = User(username="admin", email="admin@example.test", is_admin=True)
        admin.set_password("admin123")
        note = BaseNote(title="Admin Note", country="Deutschland", issue_year=2026)
        db.session.add_all([admin, note])
        db.session.commit()

        client = app.test_client()
        client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = client.get(f"/catalog/{note.id}")

        assert response.status_code == 200
        assert b"Hauptschein bearbeiten" in response.data
        assert b"Hauptschein sammeln" not in response.data
        assert b"Zur Wunschliste" not in response.data


def test_catalog_user_can_toggle_collection_and_wishlist_from_index():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        user = User(username="collector", email="collector@example.test")
        user.set_password("collector123")
        note = BaseNote(title="Toggle Note", country="Deutschland", issue_year=2026)
        db.session.add_all([user, note])
        db.session.commit()

        client = app.test_client()
        client.post("/auth/login", data={"username": "collector", "password": "collector123"})
        response = client.get("/catalog?view=table")

        assert response.status_code == 200
        assert b"Status" in response.data
        assert b"Sammlung" in response.data
        assert b"Wunschliste" in response.data

        response = client.post(
            f"/catalog/{note.id}/toggle-collection",
            data={"enabled": "1", "next": "/catalog?view=table"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert UserCollectionEntry.query.filter_by(
            user_id=user.id,
            base_note_id=note.id,
            variant_id=None,
        ).count() == 1
        assert WishlistEntry.query.filter_by(
            user_id=user.id,
            base_note_id=note.id,
            variant_id=None,
        ).count() == 0

        response = client.post(
            f"/catalog/{note.id}/toggle-wishlist",
            data={"enabled": "1", "next": "/catalog?view=table"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert WishlistEntry.query.filter_by(
            user_id=user.id,
            base_note_id=note.id,
            variant_id=None,
        ).count() == 1
        assert UserCollectionEntry.query.filter_by(
            user_id=user.id,
            base_note_id=note.id,
            variant_id=None,
        ).count() == 0


def test_wishlist_page_uses_new_name_and_old_missing_url_redirects():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        user = User(username="collector", email="collector@example.test")
        user.set_password("collector123")
        collected_note = BaseNote(title="Collected Tile", country="Deutschland", issue_year=2026)
        wishlist_note = BaseNote(title="Wishlist Tile", country="Frankreich", issue_year=2026)
        open_note = BaseNote(title="Open Tile", country="Italien", issue_year=2026)
        db.session.add_all([user, collected_note, wishlist_note, open_note])
        db.session.flush()
        db.session.add(
            UserCollectionEntry(user_id=user.id, base_note_id=collected_note.id, quantity=1)
        )
        db.session.add(WishlistEntry(user_id=user.id, base_note_id=wishlist_note.id))
        db.session.commit()

        client = app.test_client()
        client.post("/auth/login", data={"username": "collector", "password": "collector123"})
        response = client.get("/collection/wishlist")

        assert response.status_code == 200
        assert b"Wunschliste" in response.data
        assert b"Fehlliste" not in response.data
        assert b"Collected Tile" in response.data
        assert b"Wishlist Tile" in response.data
        assert b"Open Tile" in response.data
        assert b"border-emerald-500" in response.data
        assert b"border-sky-400" in response.data
        assert b"border-slate-300" in response.data

        redirect_response = client.get("/collection/missing")
        assert redirect_response.status_code == 302
        assert redirect_response.headers["Location"].endswith("/collection/wishlist")


def test_catalog_state_is_remembered_for_detail_back_link():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        note = BaseNote(
            title="Berlin Note",
            country="Deutschland",
            region_or_city="Berlin",
            issue_year=2026,
        )
        db.session.add(note)
        db.session.commit()

        client = app.test_client()
        client.get("/catalog?q=Berlin&view=table&sort=title&country=Deutschland")
        response = client.get(f"/catalog/{note.id}")

        assert response.status_code == 200
        assert b"Zurueck zum Katalog" in response.data
        assert b"q=Berlin" in response.data
        assert b"view=table" in response.data
        assert b"sort=title" in response.data
        assert b"country=Deutschland" in response.data

        redirect_response = client.get("/catalog")
        assert redirect_response.status_code == 302
        assert "view=table" in redirect_response.headers["Location"]


def test_admin_note_edit_redirects_to_catalog_detail():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        admin = User(username="admin", email="admin@example.test", is_admin=True)
        admin.set_password("admin123")
        note = BaseNote(title="Old Title", country="Deutschland", issue_year=2026)
        db.session.add_all([admin, note])
        db.session.commit()

        client = app.test_client()
        client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = client.post(
            f"/admin/notes/{note.id}/edit",
            data={
                "title": "New Title",
                "country": "Deutschland",
                "region_or_city": "",
                "address": "",
                "issue_year": "2026",
                "catalog_number": "",
                "front_img": "",
                "back_img": "",
                "latitude": "",
                "longitude": "",
                "is_active": "y",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["Location"].endswith(f"/catalog/{note.id}")


def test_import_runs_in_batches_without_geocoding():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        rows = [
            {
                "Land": "Deutschland",
                "Region/BL/Ort": "Berlin",
                "Nummer": f"DE-{index}",
                "Bezeichnung": f"Import Note {index}",
                "Jahr": 2026,
                "Adresse": "Pariser Platz",
            }
            for index in range(3)
        ]

        job = create_import_preview("import.xlsx", rows, [])
        run_import_batch(job)

        assert job.processed_rows == 2
        assert job.status == "running"
        assert BaseNote.query.count() == 2

        run_import_batch(job)

        assert job.processed_rows == 3
        assert job.status == "completed"
        assert BaseNote.query.count() == 3
        assert BaseNote.query.filter(BaseNote.latitude.is_not(None)).count() == 0


def test_admin_location_geocode_redirects_back_to_locations(monkeypatch):
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        admin = User(username="admin", email="admin@example.test", is_admin=True)
        admin.set_password("admin123")
        note = BaseNote(
            title="Location Note",
            country="Deutschland",
            region_or_city="Berlin",
            issue_year=2026,
        )
        db.session.add_all([admin, note])
        db.session.commit()

        monkeypatch.setattr(
            "app.services.geocoding._lookup_real_coordinates",
            lambda query: (52.516275, 13.377704),
        )

        client = app.test_client()
        client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = client.post(
            f"/admin/notes/{note.id}/geocode",
            data={"next": "/admin/locations"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/admin/locations")
