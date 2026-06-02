from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.forms import CollectionEntryForm, WishlistEntryForm
from app.models import BaseNote, UserCollectionEntry, Variant, WishlistEntry

bp = Blueprint("collection", __name__, url_prefix="/collection")


@dataclass
class CollectionListItem:
    entry: UserCollectionEntry | WishlistEntry
    source: str

    @property
    def base_note(self) -> BaseNote:
        return self.entry.base_note

    @property
    def variant(self) -> Variant | None:
        return self.entry.variant

    @property
    def created_at(self) -> datetime:
        return self.entry.created_at

    @property
    def catalog_number(self) -> str:
        if self.variant and self.variant.catalog_number:
            return self.variant.catalog_number
        return self.base_note.catalog_number or ""


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


def _sort_collection_items(items: list[CollectionListItem]) -> list[CollectionListItem]:
    return sorted(
        items,
        key=lambda item: (
            item.catalog_number.casefold() if item.catalog_number else "zzzzzz",
            item.base_note.title.casefold(),
            item.variant.variant_type.casefold() if item.variant else "",
            item.source,
        ),
    )


@bp.route("")
@login_required
def index():
    filter_mode = request.args.get("filter", "all")
    if filter_mode not in {"all", "base", "variants", "wishlist"}:
        filter_mode = "all"

    collection_query = (
        UserCollectionEntry.query.filter_by(user_id=current_user.id)
        .options(selectinload(UserCollectionEntry.base_note), selectinload(UserCollectionEntry.variant))
        .join(BaseNote)
    )
    if filter_mode == "base":
        collection_query = collection_query.filter(UserCollectionEntry.variant_id.is_(None))
    elif filter_mode == "variants":
        collection_query = collection_query.filter(UserCollectionEntry.variant_id.is_not(None))

    wishlist_query = (
        WishlistEntry.query.filter_by(user_id=current_user.id)
        .options(selectinload(WishlistEntry.base_note), selectinload(WishlistEntry.variant))
        .join(BaseNote)
    )

    if filter_mode == "wishlist":
        entries = _sort_collection_items(
            [CollectionListItem(entry, "wishlist") for entry in wishlist_query.all()]
        )
    elif filter_mode == "all":
        collection_items = [CollectionListItem(entry, "collection") for entry in collection_query.all()]
        wishlist_items = [CollectionListItem(entry, "wishlist") for entry in wishlist_query.all()]
        entries = _sort_collection_items(collection_items + wishlist_items)
    else:
        entries = _sort_collection_items(
            [CollectionListItem(entry, "collection") for entry in collection_query.all()]
        )

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
    return redirect(url_for("collection.index", filter="wishlist"))


@bp.route("/wishlist", methods=["GET", "POST"])
@login_required
def wishlist():
    return redirect(url_for("collection.index", filter="wishlist"))


@bp.route("/wishlist/<int:entry_id>/collect", methods=["POST"])
@login_required
def wishlist_collect(entry_id: int):
    entry = WishlistEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    collection_entry = UserCollectionEntry.query.filter_by(
        user_id=current_user.id,
        base_note_id=entry.base_note_id,
        variant_id=entry.variant_id,
    ).first()
    if collection_entry is None:
        db.session.add(
            UserCollectionEntry(
                user_id=current_user.id,
                base_note_id=entry.base_note_id,
                variant_id=entry.variant_id,
                quantity=1,
            )
        )
    db.session.delete(entry)
    try:
        db.session.commit()
        flash("Wunsch wurde in die Sammlung uebernommen.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Der Wunsch konnte nicht in die Sammlung uebernommen werden.", "error")
    return redirect(url_for("collection.index"))
