from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import SubmitField


class ImportUploadForm(FlaskForm):
    file = FileField(
        "Excel-Datei",
        validators=[FileRequired(), FileAllowed(["xlsx"], "Bitte eine .xlsx Datei waehlen.")],
    )
    submit = SubmitField("Vorschau erstellen")
