# MemoCatalog Flask

Eine eigenstaendige Flask/Jinja-Version von MemoCatalog fuer Memo-Euro- und 0-Euro-Souvenir-Banknoten.

## Stack

- Python 3.12+
- Flask App Factory
- SQLite, SQLAlchemy, Flask-Migrate/Alembic
- Flask-Login, Flask-WTF
- Jinja2 Templates
- Tailwind CSS per CDN

## Start

```bash
cd flask
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
flask --app wsgi init-db
flask --app wsgi run --debug
```

Danach laeuft die App unter `http://127.0.0.1:5000`.

Demo-Admin:

- Benutzer: `admin`
- Passwort: `admin123`

## Migrationen

Flask-Migrate ist in `app/extensions.py` und `create_app()` verdrahtet.

```bash
flask --app wsgi db init
flask --app wsgi db migrate -m "initial schema"
flask --app wsgi db upgrade
```

Tests:

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Funktionen

- Oeffentlicher Katalog mit Suche, Filter, Sortierung, Pagination sowie Grid- und Tabellenansicht
- Detailseite mit Bildern, Varianten, GPS-Status und Sammel-/Fehllistenaktionen
- Registrierung, Login, Logout und Admin-Rolle
- Sammlung mit Hauptscheinen oder konkreten Varianten
- Statistik-Dashboard
- Admin-Dashboard, Hauptschein- und Variantenpflege, Nutzer, Sammlungen, Standortuebersicht
- Excel-Import mit persistenter Vorschau, Warnungen und Import-Job-Status
- Echtes Geocoding ueber Nominatim/OpenStreetMap mit Datenbank- und JSON-Cache

Hinweis: Das Geocoding wird bewusst ueber Admin-Aktionen gestartet, damit keine externen API-Aufrufe beim normalen Speichern oder Seeden passieren. Fuer den oeffentlichen Nominatim-Dienst setzt die App einen identifizierenden User-Agent, cached Ergebnisse und drosselt Requests auf ca. einen Request pro Sekunde.
