from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegistrationForm(FlaskForm):
    username = StringField("Benutzername", validators=[DataRequired(), Length(min=3, max=80)])
    email = EmailField("E-Mail", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Passwort", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Passwort wiederholen", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Registrieren")


class LoginForm(FlaskForm):
    username = StringField("Benutzername oder E-Mail", validators=[DataRequired()])
    password = PasswordField("Passwort", validators=[DataRequired()])
    remember = BooleanField("Angemeldet bleiben")
    submit = SubmitField("Einloggen")
