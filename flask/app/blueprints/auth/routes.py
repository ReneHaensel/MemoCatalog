from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import or_

from app.extensions import db
from app.forms import LoginForm, RegistrationForm
from app.models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        exists = User.query.filter(
            or_(User.username == form.username.data, User.email == form.email.data)
        ).first()
        if exists:
            flash("Benutzername oder E-Mail ist bereits vergeben.", "error")
        else:
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            if User.query.count() == 0:
                user.is_admin = True
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Willkommen bei MemoCatalog.", "success")
            return redirect(url_for("main.index"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(
            or_(User.username == form.username.data, User.email == form.username.data)
        ).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash("Du bist eingeloggt.", "success")
            return redirect(request.args.get("next") or url_for("main.index"))
        flash("Login fehlgeschlagen.", "error")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("Du bist ausgeloggt.", "success")
    return redirect(url_for("main.index"))
