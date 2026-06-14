from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.forms import BaseNoteForm
from app.models import BaseNote, User, UserCollectionEntry, WishlistEntry
from app.services.geocoding import geocode_all_notes, geocode_missing_notes, geocode_note, geocode_note_result

bp = Blueprint("admin", __name__, url_prefix="/admin")

F = TypeVar("F", bound=Callable)


def admin_required(view: F) -> F:
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped  # type: ignore[return-value]


@bp.route("")
@admin_required
def dashboard():
    stats = {
        "notes": BaseNote.query.count(),
        "notes_with_variant": BaseNote.query.filter(BaseNote.variant_type.is_not(None), BaseNote.variant_type != "").count(),
        "users": User.query.count(),
        "admins": User.query.filter_by(is_admin=True).count(),
        "collection_entries": UserCollectionEntry.query.count(),
        "wishlist_entries": WishlistEntry.query.count(),
        "with_coordinates": BaseNote.query.filter(BaseNote.latitude.is_not(None), BaseNote.longitude.is_not(None)).count(),
        "without_coordinates": BaseNote.query.filter(BaseNote.latitude.is_(None) | BaseNote.longitude.is_(None)).count(),
    }
    return render_template("admin/dashboard.html", stats=stats)


@bp.route("/notes")
@admin_required
def notes():
    notes = BaseNote.query.order_by(BaseNote.created_at.desc()).all()
    return render_template("admin/notes.html", notes=notes)


@bp.route("/notes/new", methods=["GET", "POST"])
@admin_required
def note_new():
    form = BaseNoteForm()
    if form.validate_on_submit():
        note = BaseNote()
        form.populate_obj(note)
        note.variant_type = note.variant_type or None
        db.session.add(note)
        db.session.commit()
        flash("Hauptschein angelegt.", "success")
        return redirect(url_for("admin.notes"))
    return render_template("admin/note_form.html", form=form, title="Hauptschein anlegen")


@bp.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@admin_required
def note_edit(note_id: int):
    note = BaseNote.query.get_or_404(note_id)
    form = BaseNoteForm(obj=note)
    if form.validate_on_submit():
        form.populate_obj(note)
        note.variant_type = note.variant_type or None
        db.session.commit()
        flash("Hauptschein aktualisiert.", "success")
        return redirect(url_for("catalog.detail", note_id=note.id))
    return render_template("admin/note_form.html", form=form, title="Hauptschein bearbeiten", note=note)


@bp.route("/notes/<int:note_id>/geocode", methods=["POST"])
@admin_required
def note_geocode(note_id: int):
    note = BaseNote.query.get_or_404(note_id)
    next_url = request.form.get("next") or url_for("admin.note_edit", note_id=note.id)
    result = geocode_note_result(note, force=True)
    if result.success:
        db.session.commit()
        query_info = f" Suche: {result.query}" if result.query else ""
        flash(result.message + query_info, "success")
    else:
        db.session.rollback()
        flash(result.message, "error")
    return redirect(next_url)


@bp.route("/notes/<int:note_id>/delete", methods=["POST"])
@admin_required
def note_delete(note_id: int):
    note = BaseNote.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    flash("Hauptschein geloescht.", "success")
    return redirect(url_for("admin.notes"))


@bp.route("/users")
@admin_required
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@bp.route("/collections")
@admin_required
def collections():
    entries = UserCollectionEntry.query.order_by(UserCollectionEntry.created_at.desc()).all()
    return render_template("admin/collections.html", entries=entries)


@bp.route("/locations")
@admin_required
def locations():
    countries = (
        db.session.query(BaseNote.country, func.count(BaseNote.id))
        .group_by(BaseNote.country)
        .order_by(BaseNote.country)
        .all()
    )
    notes = BaseNote.query.order_by(BaseNote.country, BaseNote.region_or_city).all()
    return render_template("admin/locations.html", notes=notes, countries=countries)


@bp.route("/locations/geocode", methods=["POST"])
@admin_required
def geocode_missing():
    result = geocode_missing_notes()
    flash(
        f"{result.updated} von {result.processed} fehlenden Koordinaten wurden berechnet."
        + (f" {result.failed} ohne Treffer." if result.failed else ""),
        "success" if result.failed == 0 else "error",
    )
    return redirect(url_for("admin.locations"))


@bp.route("/locations/geocode-all", methods=["POST"])
@admin_required
def geocode_all():
    result = geocode_all_notes()
    flash(
        f"{result.updated} von {result.processed} Koordinaten wurden neu berechnet."
        + (f" {result.failed} ohne Treffer." if result.failed else ""),
        "success" if result.failed == 0 else "error",
    )
    return redirect(url_for("admin.locations"))
