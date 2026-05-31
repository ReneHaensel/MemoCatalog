from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, url_for

from app.blueprints.admin.routes import admin_required
from app.forms import ImportUploadForm
from app.models import ImportJob
from app.services.imports import create_import_preview, parse_excel, run_import

bp = Blueprint("imports", __name__, url_prefix="/admin/import")


@bp.route("", methods=["GET", "POST"])
@admin_required
def index():
    form = ImportUploadForm()
    latest_jobs = ImportJob.query.order_by(ImportJob.created_at.desc()).limit(10).all()
    if form.validate_on_submit():
        upload = form.file.data
        parsed = parse_excel(upload)
        job = create_import_preview(upload.filename, parsed.rows, parsed.warnings)
        flash("Importvorschau wurde erstellt.", "success")
        return redirect(url_for("imports.preview", job_id=job.id))
    return render_template("imports/index.html", form=form, jobs=latest_jobs)


@bp.route("/<int:job_id>")
@admin_required
def preview(job_id: int):
    job = ImportJob.query.get_or_404(job_id)
    return render_template("imports/preview.html", job=job)


@bp.route("/<int:job_id>/run", methods=["POST"])
@admin_required
def run(job_id: int):
    job = ImportJob.query.get_or_404(job_id)
    if job.status == "completed":
        flash("Dieser Import wurde bereits ausgefuehrt.", "error")
    else:
        run_import(job)
        flash("Import abgeschlossen.", "success")
    return redirect(url_for("imports.preview", job_id=job.id))
