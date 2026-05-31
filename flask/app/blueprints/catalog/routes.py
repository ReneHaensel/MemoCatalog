from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import BaseNote, UserCollectionEntry, Variant, WishlistEntry

bp = Blueprint("catalog", __name__, url_prefix="/catalog")


SORTS = {
    "year": BaseNote.issue_year.desc(),
    "title": BaseNote.title.asc(),
    "country": BaseNote.country.asc(),
    "address": BaseNote.address.asc(),
    "region": BaseNote.region_or_city.asc(),
    "catalog": BaseNote.catalog_number.asc(),
    "created": BaseNote.created_at.desc(),
}

CATALOG_STATE_KEY = "catalog_state"
CATALOG_DEFAULT_STATE = {
    "q": "",
    "country": "",
    "year": "",
    "address": "",
    "view": "grid",
    "sort": "created",
    "page": 1,
}


def _catalog_state_from_args() -> dict[str, str | int]:
    view = request.args.get("view", CATALOG_DEFAULT_STATE["view"])
    sort = request.args.get("sort", CATALOG_DEFAULT_STATE["sort"])
    page = request.args.get("page", CATALOG_DEFAULT_STATE["page"], type=int)

    if view not in {"grid", "table"}:
        view = CATALOG_DEFAULT_STATE["view"]
    if sort not in SORTS:
        sort = CATALOG_DEFAULT_STATE["sort"]
    if page < 1:
        page = 1

    return {
        "q": request.args.get("q", "").strip(),
        "country": request.args.get("country", "").strip(),
        "year": request.args.get("year", "").strip(),
        "address": request.args.get("address", "").strip(),
        "view": view,
        "sort": sort,
        "page": page,
    }


def _has_non_default_state(state: dict[str, str | int] | None) -> bool:
    if not state:
        return False
    return any(state.get(key) != value for key, value in CATALOG_DEFAULT_STATE.items())


def _saved_catalog_state() -> dict[str, str | int]:
    state = session.get(CATALOG_STATE_KEY)
    if not isinstance(state, dict):
        return CATALOG_DEFAULT_STATE.copy()
    merged = CATALOG_DEFAULT_STATE.copy()
    merged.update({key: state.get(key, value) for key, value in CATALOG_DEFAULT_STATE.items()})
    return merged


def _catalog_return_url() -> str:
    return request.form.get("next") or url_for("catalog.index", **_saved_catalog_state())


@bp.route("")
def index():
    if not request.args:
        saved_state = _saved_catalog_state()
        if _has_non_default_state(saved_state):
            return redirect(url_for("catalog.index", **saved_state))

    state = _catalog_state_from_args()
    session[CATALOG_STATE_KEY] = state

    query = BaseNote.query.filter_by(is_active=True)
    search = str(state["q"])
    country = str(state["country"])
    year = str(state["year"])
    address = str(state["address"])
    view = str(state["view"])
    sort = str(state["sort"])

    if search:
        like = f"%{search}%"
        query = query.outerjoin(Variant).filter(
            or_(
                BaseNote.title.ilike(like),
                BaseNote.address.ilike(like),
                BaseNote.region_or_city.ilike(like),
                BaseNote.catalog_number.ilike(like),
                Variant.catalog_number.ilike(like),
            )
        )
    if country:
        query = query.filter(BaseNote.country == country)
    if year.isdigit():
        query = query.filter(BaseNote.issue_year == int(year))
    if address:
        query = query.filter(BaseNote.address.ilike(f"%{address}%"))

    page = int(state["page"])
    notes = (
        query.distinct()
        .order_by(SORTS.get(sort, BaseNote.created_at.desc()))
        .paginate(page=page, per_page=current_app.config["ITEMS_PER_PAGE"], error_out=False)
    )
    countries = [row[0] for row in db.session.query(BaseNote.country).distinct().order_by(BaseNote.country)]
    years = [row[0] for row in db.session.query(BaseNote.issue_year).distinct().order_by(BaseNote.issue_year.desc()) if row[0]]
    collected_note_ids: set[int] = set()
    wishlist_note_ids: set[int] = set()
    if current_user.is_authenticated and not current_user.is_admin:
        collected_note_ids = {
            row[0]
            for row in db.session.query(UserCollectionEntry.base_note_id)
            .filter_by(user_id=current_user.id, variant_id=None)
            .distinct()
            .all()
        }
        wishlist_note_ids = {
            row[0]
            for row in db.session.query(WishlistEntry.base_note_id)
            .filter_by(user_id=current_user.id, variant_id=None)
            .distinct()
            .all()
        }
    return render_template(
        "catalog/index.html",
        notes=notes,
        countries=countries,
        years=years,
        view=view,
        sort=sort,
        search=search,
        country=country,
        year=year,
        address=address,
        collected_note_ids=collected_note_ids,
        wishlist_note_ids=wishlist_note_ids,
    )


@bp.route("/<int:note_id>")
def detail(note_id: int):
    note = BaseNote.query.get_or_404(note_id)
    catalog_state = _saved_catalog_state()
    catalog_back_url = (
        url_for("catalog.index", **catalog_state)
        if _has_non_default_state(catalog_state)
        else url_for("catalog.index")
    )
    return render_template("catalog/detail.html", note=note, catalog_back_url=catalog_back_url)


@bp.route("/<int:note_id>/collect", methods=["POST"])
@login_required
def collect(note_id: int):
    note = BaseNote.query.get_or_404(note_id)
    variant_id = request.form.get("variant_id", type=int) or None
    if variant_id:
        Variant.query.filter_by(id=variant_id, base_note_id=note.id).first_or_404()
    entry = UserCollectionEntry(
        user_id=current_user.id,
        base_note_id=note.id,
        variant_id=variant_id,
        quantity=1,
    )
    db.session.add(entry)
    if variant_id is None:
        WishlistEntry.query.filter_by(
            user_id=current_user.id,
            base_note_id=note.id,
            variant_id=None,
        ).delete()
    try:
        db.session.commit()
        flash("Eintrag wurde zur Sammlung hinzugefuegt.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Dieser Eintrag ist bereits in deiner Sammlung.", "error")
    return redirect(url_for("catalog.detail", note_id=note.id))


@bp.route("/<int:note_id>/toggle-collection", methods=["POST"])
@login_required
def toggle_collection(note_id: int):
    if current_user.is_admin:
        return redirect(_catalog_return_url())

    note = BaseNote.query.get_or_404(note_id)
    enabled = request.form.get("enabled") == "1"
    entry = UserCollectionEntry.query.filter_by(
        user_id=current_user.id,
        base_note_id=note.id,
        variant_id=None,
    ).first()

    if enabled and entry is None:
        db.session.add(
            UserCollectionEntry(
                user_id=current_user.id,
                base_note_id=note.id,
                quantity=1,
            )
        )
        WishlistEntry.query.filter_by(
            user_id=current_user.id,
            base_note_id=note.id,
            variant_id=None,
        ).delete()
    elif not enabled and entry is not None:
        db.session.delete(entry)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Der Sammlungseintrag konnte nicht aktualisiert werden.", "error")
    return redirect(_catalog_return_url())


@bp.route("/<int:note_id>/wishlist", methods=["POST"])
@login_required
def wishlist(note_id: int):
    note = BaseNote.query.get_or_404(note_id)
    variant_id = request.form.get("variant_id", type=int) or None
    if variant_id:
        Variant.query.filter_by(id=variant_id, base_note_id=note.id).first_or_404()
    if variant_id is None:
        UserCollectionEntry.query.filter_by(
            user_id=current_user.id,
            base_note_id=note.id,
            variant_id=None,
        ).delete()
    db.session.add(
        WishlistEntry(
            user_id=current_user.id,
            base_note_id=note.id,
            variant_id=variant_id,
            notes=request.form.get("notes"),
        )
    )
    try:
        db.session.commit()
        flash("Eintrag wurde zur Wunschliste hinzugefuegt.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Dieser Eintrag steht bereits auf deiner Wunschliste.", "error")
    return redirect(url_for("catalog.detail", note_id=note.id))


@bp.route("/<int:note_id>/toggle-wishlist", methods=["POST"])
@login_required
def toggle_wishlist(note_id: int):
    if current_user.is_admin:
        return redirect(_catalog_return_url())

    note = BaseNote.query.get_or_404(note_id)
    enabled = request.form.get("enabled") == "1"
    entry = WishlistEntry.query.filter_by(
        user_id=current_user.id,
        base_note_id=note.id,
        variant_id=None,
    ).first()

    if enabled and entry is None:
        db.session.add(WishlistEntry(user_id=current_user.id, base_note_id=note.id))
        UserCollectionEntry.query.filter_by(
            user_id=current_user.id,
            base_note_id=note.id,
            variant_id=None,
        ).delete()
    elif not enabled and entry is not None:
        db.session.delete(entry)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Der Wunschlisteneintrag konnte nicht aktualisiert werden.", "error")
    return redirect(_catalog_return_url())
