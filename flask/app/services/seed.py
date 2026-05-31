from __future__ import annotations

from app.extensions import db
from app.models import BaseNote, User, Variant, VariantType


def seed_demo_data() -> None:
    if User.query.filter_by(username="admin").first() is None:
        admin = User(username="admin", email="admin@example.test", is_admin=True)
        admin.set_password("admin123")
        db.session.add(admin)

    samples = [
        {
            "title": "Brandenburger Tor",
            "country": "Deutschland",
            "region_or_city": "Berlin",
            "address": "Pariser Platz, Berlin",
            "issue_year": 2016,
            "catalog_number": "DEAA0001",
        },
        {
            "title": "Schloss Neuschwanstein",
            "country": "Deutschland",
            "region_or_city": "Schwangau",
            "address": "Neuschwansteinstrasse 20, Schwangau",
            "issue_year": 2017,
            "catalog_number": "DEAA0002",
        },
        {
            "title": "Eiffelturm",
            "country": "Frankreich",
            "region_or_city": "Paris",
            "address": "Champ de Mars, Paris",
            "issue_year": 2015,
            "catalog_number": "FRAA0001",
        },
    ]
    for item in samples:
        note = BaseNote.query.filter_by(catalog_number=item["catalog_number"]).first()
        if note is None:
            note = BaseNote(**item, is_active=True)
            db.session.add(note)
            db.session.flush()
            db.session.add(
                Variant(
                    base_note_id=note.id,
                    variant_type=VariantType.SPECIMEN.value,
                    catalog_number=f"{item['catalog_number']}-S",
                )
            )
    db.session.commit()
