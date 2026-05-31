from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms import CollectionEntryForm, WishlistEntryForm
from app.models import BaseNote, UserCollectionEntry, Variant, WishlistEntry

bp = Blueprint("collection", __name__, url_prefix="/collection")


def populate_entry_choices(form: CollectionEntryForm | WishlistEntryForm) -> None:
    notes = BaseNote.query.filter_by(is_active=True).order_by(BaseNote.title).all()
    form.base_note_id.choices = [(note.id, f"{note.title} ({note.catalog_number or '-'})") for note in notes]
    variants = Variant.query.join(BaseNote).order_by(BaseNote.title, Variant.variant_type).all()
    form.variant_id.choices = [(0, "Nur Hauptschein")] + [
        (variant.id, f"{variant.base_note.title} - {variant.variant_type}") for variant in variants
    ]


def normalize_note_variant(base_note_id: int, variant_id: int | None) -> tuple[int, int | None]:
    if variant_id:
        variant = Variant.query.get_or_404(variant_id)
        return variant.base_note_id, variant.id
    return base_note_id, None


@bp.route("")
@login_required
def index():
    filter_mode = request.args.get("filter", "all")
    query = UserCollectionEntry.query.filter_by(user_id=current_user.id).join(BaseNote)
    if filter_mode == "base":
        query = query.filter(UserCollectionEntry.variant_id.is_(None))
    elif filter_mode == "variants":
        query = query.filter(UserCollectionEntry.variant_id.is_not(None))
    entries = query.order_by(UserCollectionEntry.created_at.desc()).all()
    return render_template("collection/index.html", entries=entries, filter_mode=filter_mode)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = CollectionEntryForm()
    populate_entry_choices(form)
    if form.validate_on_submit():
        base_note_id, variant_id = normalize_note_variant(form.base_note_id.data, form.variant_id.data or None)
        entry = UserCollectionEntry(
            user_id=current_user.id,
            base_note_id=base_note_id,
            variant_id=variant_id,
            condition=form.condition.data,
            quantity=form.quantity.data,
            personal_notes=form.personal_notes.data,
            acquired_at=form.acquired_at.data,
        )
        db.session.add(entry)
        try:
            db.session.commit()
            flash("Sammlungseintrag gespeichert.", "success")
            return redirect(url_for("collection.index"))
        except IntegrityError:
            db.session.rollback()
            flash("Dieser Sammlungseintrag existiert bereits.", "error")
    return render_template("collection/form.html", form=form, title="Sammlungseintrag anlegen")


@bp.route("/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit(entry_id: int):
    entry = UserCollectionEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    form = CollectionEntryForm(obj=entry)
    populate_entry_choices(form)
    if request.method == "GET":
        form.base_note_id.data = entry.base_note_id
        form.variant_id.data = entry.variant_id or 0
    if form.validate_on_submit():
        base_note_id, variant_id = normalize_note_variant(form.base_note_id.data, form.variant_id.data or None)
        form.populate_obj(entry)
        entry.base_note_id = base_note_id
        entry.variant_id = variant_id
        try:
            db.session.commit()
            flash("Sammlungseintrag aktualisiert.", "success")
            return redirect(url_for("collection.index"))
        except IntegrityError:
            db.session.rollback()
            flash("Dieser Sammlungseintrag existiert bereits.", "error")
    return render_template("collection/form.html", form=form, title="Sammlungseintrag bearbeiten")


@bp.route("/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete(entry_id: int):
    entry = UserCollectionEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    flash("Sammlungseintrag geloescht.", "success")
    return redirect(url_for("collection.index"))


@bp.route("/missing", methods=["GET", "POST"])
@login_required
def missing():
    return redirect(url_for("collection.wishlist"))


@bp.route("/wishlist", methods=["GET", "POST"])
@login_required
def wishlist():
    form = WishlistEntryForm()
    populate_entry_choices(form)
    if form.validate_on_submit():
        base_note_id, variant_id = normalize_note_variant(form.base_note_id.data, form.variant_id.data or None)
        db.session.add(
            WishlistEntry(
                user_id=current_user.id,
                base_note_id=base_note_id,
                variant_id=variant_id,
                notes=form.notes.data,
            )
        )
        try:
            db.session.commit()
            flash("Wunschlisteneintrag gespeichert.", "success")
            return redirect(url_for("collection.wishlist"))
        except IntegrityError:
            db.session.rollback()
            flash("Dieser Eintrag steht bereits auf deiner Wunschliste.", "error")
    notes = BaseNote.query.filter_by(is_active=True).order_by(BaseNote.country, BaseNote.title).all()
    collected_note_ids = {
        row[0]
        for row in db.session.query(UserCollectionEntry.base_note_id)
        .filter_by(user_id=current_user.id)
        .distinct()
        .all()
    }
    wishlist_note_ids = {
        row[0]
        for row in db.session.query(WishlistEntry.base_note_id)
        .filter_by(user_id=current_user.id)
        .distinct()
        .all()
    }
    return render_template(
        "collection/wishlist.html",
        notes=notes,
        collected_note_ids=collected_note_ids,
        wishlist_note_ids=wishlist_note_ids,
    )
