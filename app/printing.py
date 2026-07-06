"""Print views: customer and owner copies, one or many services (HTML + PDF)."""
from datetime import date

from flask import (
    Blueprint, render_template, request, abort, Response, flash, redirect, url_for,
)
from flask_login import login_required, current_user

from .extensions import db
from .models import Service, Car

print_bp = Blueprint("printing", __name__)


def _can_access(service: Service) -> bool:
    return current_user.is_admin or service.worker_id == current_user.id


def _service_context(service_id):
    svc = db.session.get(Service, service_id) or abort(404)
    if not _can_access(svc):
        abort(403)
    mode = request.args.get("mode", "customer")
    return dict(services=[svc], car=svc.car, owner=(mode == "owner"),
                mode=mode, single=True, now=date.today())


def _car_context(car_id):
    car_obj = db.session.get(Car, car_id) or abort(404)
    services = list(car_obj.services)
    if not current_user.is_admin:
        services = [s for s in services if s.worker_id == current_user.id]
    services.sort(key=lambda s: (s.date, s.id))
    mode = request.args.get("mode", "customer")
    return dict(services=services, car=car_obj, owner=(mode == "owner"),
                mode=mode, single=(len(services) == 1), now=date.today())


# ---------------------------------------------------------------------------
# HTML print (browser print dialog)
# ---------------------------------------------------------------------------
@print_bp.route("/print/service/<int:service_id>")
@login_required
def service(service_id):
    return render_template("print/services.html", **_service_context(service_id))


@print_bp.route("/print/car/<int:car_id>")
@login_required
def car(car_id):
    return render_template("print/services.html", **_car_context(car_id))


# ---------------------------------------------------------------------------
# PDF export (download)
# ---------------------------------------------------------------------------
def _pdf_response(ctx, filename):
    from .pdf import render_pdf
    html = render_template("print/pdf.html", **ctx)
    try:
        pdf_bytes = render_pdf(html)
    except Exception as exc:  # noqa: BLE001
        flash(f"PDF nije moguće generisati: {exc}", "danger")
        return redirect(request.referrer or url_for("main.dashboard"))
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@print_bp.route("/pdf/service/<int:service_id>")
@login_required
def service_pdf(service_id):
    ctx = _service_context(service_id)
    tag = "vlasnik" if ctx["owner"] else "kupac"
    return _pdf_response(ctx, f"servis_{ctx['car'].plate}_{tag}.pdf")


@print_bp.route("/pdf/car/<int:car_id>")
@login_required
def car_pdf(car_id):
    ctx = _car_context(car_id)
    tag = "vlasnik" if ctx["owner"] else "kupac"
    return _pdf_response(ctx, f"vozilo_{ctx['car'].plate}_{tag}.pdf")
