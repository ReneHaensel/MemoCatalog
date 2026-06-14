from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, FloatField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

from app.models import VariantType


class BaseNoteForm(FlaskForm):
    title = StringField("Titel", validators=[DataRequired(), Length(max=255)])
    country = StringField("Land", validators=[DataRequired(), Length(max=120)])
    region_or_city = StringField("Region/Ort", validators=[Optional(), Length(max=160)])
    address = StringField("Adresse", validators=[Optional(), Length(max=255)])
    issue_year = IntegerField("Jahr", validators=[Optional()])
    variant_type = SelectField(
        "Variante",
        choices=[("", "Keine Variante")] + [(item.value, item.value) for item in VariantType],
        default="",
        validators=[Optional()],
    )
    catalog_number = StringField("Katalognummer", validators=[Optional(), Length(max=100)])
    front_img = StringField("Vorderbild URL", validators=[Optional(), Length(max=500)])
    back_img = StringField("Rueckbild URL", validators=[Optional(), Length(max=500)])
    latitude = FloatField("Latitude", validators=[Optional()])
    longitude = FloatField("Longitude", validators=[Optional()])
    is_active = BooleanField("Aktiv", default=True)
    submit = SubmitField("Speichern")
