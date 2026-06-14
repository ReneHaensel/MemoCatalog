from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class CollectionEntryForm(FlaskForm):
    base_note_id = SelectField("Hauptschein", coerce=int, validators=[DataRequired()])
    condition = StringField("Zustand", validators=[Optional(), Length(max=120)])
    quantity = IntegerField("Menge", default=1, validators=[DataRequired(), NumberRange(min=1)])
    personal_notes = TextAreaField("Persoenliche Notiz", validators=[Optional()])
    acquired_at = DateField("Erworben am", validators=[Optional()])
    submit = SubmitField("Speichern")


class WishlistEntryForm(FlaskForm):
    base_note_id = SelectField("Hauptschein", coerce=int, validators=[DataRequired()])
    notes = TextAreaField("Notiz", validators=[Optional()])
    submit = SubmitField("Speichern")
