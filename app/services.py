"""Service records: plate-first flow, parts, labor, listing."""
from datetime import datetime, date

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, abort,
)
from flask_login import login_required, current_user

from .extensions import db
from .models import Car, Service, Part, SERVICE_TYPES, SERVICE_TYPE_LABELS, SERVICE_TYPE_POPRAVKE
from .security import scoped_query

services_bp = Blueprint("services", __name__)


def _can_access(service: Service) -> bool:
    return current_user.is_admin or service.worker_id == current_user.id


def _normalise_plate(plate: str) -> str:
    return plate.replace(" ", "").upper().strip()


def _recompute_car_mileage(car: Car) -> None:
    """Set the car's last-known mileage from its most recent service reading.

    Using the newest service (by date, then id) means editing/deleting an
    older service never clobbers a more recent odometer value.
    """
    latest = (
        Service.query
        .filter(Service.car_id == car.id, Service.mileage.isnot(None))
        .order_by(Service.date.desc(), Service.id.desc())
        .first()
    )
    if latest is not None:
        car.mileage = latest.mileage


# ---------------------------------------------------------------------------
# 1) Start a service: ask for the registration plate first
# ---------------------------------------------------------------------------
@services_bp.route("/service/start", methods=["GET", "POST"])
@login_required
def start():
    if request.method == "POST":
        plate = _normalise_plate(request.form.get("plate", ""))
        if not plate:
            flash("Unesite registarsku oznaku.", "danger")
            return render_template("services/start.html")

        car = Car.query.filter_by(plate=plate).first()
        if car:
            flash(f"Vozilo {plate} je pronađeno. Dodajte novi servis.", "info")
            return redirect(url_for("services.new", car_id=car.id))

        # Not found -> register the car, then continue to the service
        flash(f"Vozilo {plate} ne postoji. Registrujte ga.", "warning")
        return redirect(url_for("cars.new", plate=plate, then="service"))

    return render_template("services/start.html")


# ---------------------------------------------------------------------------
# 2) Create a new service for an existing car
# ---------------------------------------------------------------------------
@services_bp.route("/service/new", methods=["GET", "POST"])
@login_required
def new():
    car_id = request.args.get("car_id") or request.form.get("car_id")
    car = db.session.get(Car, int(car_id)) if car_id else None
    if car is None:
        flash("Vozilo nije izabrano.", "danger")
        return redirect(url_for("services.start"))

    if request.method == "POST":
        service = Service(car_id=car.id, worker_id=current_user.id,
                         shop_id=current_user.shop_id)
        _apply_service_form(service, request.form)
        db.session.add(service)
        _rebuild_parts(service, request.form)
        db.session.commit()
        _recompute_car_mileage(car)
        db.session.commit()
        flash("Servis je sačuvan.", "success")
        return redirect(url_for("services.detail", service_id=service.id))

    return render_template("services/form.html", service=None, car=car,
                           today=date.today().isoformat())


# ---------------------------------------------------------------------------
# 3) View / edit / delete
# ---------------------------------------------------------------------------
@services_bp.route("/service/<int:service_id>")
@login_required
def detail(service_id):
    service = db.session.get(Service, service_id) or abort(404)
    if not _can_access(service):
        abort(403)
    return render_template("services/detail.html", service=service, car=service.car)


@services_bp.route("/service/<int:service_id>/edit", methods=["GET", "POST"])
@login_required
def edit(service_id):
    service = db.session.get(Service, service_id) or abort(404)
    if not _can_access(service):
        abort(403)

    if request.method == "POST":
        _apply_service_form(service, request.form)
        _rebuild_parts(service, request.form)
        db.session.commit()
        _recompute_car_mileage(service.car)
        db.session.commit()
        flash("Servis je ažuriran.", "success")
        return redirect(url_for("services.detail", service_id=service.id))

    return render_template("services/form.html", service=service, car=service.car,
                           today=date.today().isoformat())


@services_bp.route("/service/<int:service_id>/delete", methods=["POST"])
@login_required
def delete(service_id):
    service = db.session.get(Service, service_id) or abort(404)
    if not _can_access(service):
        abort(403)
    car = service.car
    db.session.delete(service)
    db.session.commit()
    _recompute_car_mileage(car)
    db.session.commit()
    flash("Servis je obrisan.", "info")
    return redirect(url_for("cars.detail", car_id=car.id))


# ---------------------------------------------------------------------------
# 4) Listing
# ---------------------------------------------------------------------------
@services_bp.route("/services")
@login_required
def list_services():
    q = scoped_query(Service)
    if not current_user.is_admin:
        q = q.filter(Service.worker_id == current_user.id)

    plate = request.args.get("q", "").strip()
    filter_type = request.args.get("service_type", "")
    joined = False
    if plate:
        q = q.join(Car)
        joined = True
        q = q.filter(Car.plate.ilike(f"%{_normalise_plate(plate)}%"))
    if filter_type and filter_type in SERVICE_TYPE_LABELS:
        q = q.filter(Service.service_type == filter_type)

    services = q.order_by(Service.date.desc(), Service.id.desc()).all()
    return render_template("services/list.html", services=services, q=plate,
                           filter_type=filter_type)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _apply_service_form(service: Service, form) -> None:
    date_str = form.get("date", "").strip()
    try:
        service.date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        service.date = date.today()
    service.mileage = _to_int(form.get("mileage"))
    service.labor_price = _to_float(form.get("labor_price"))
    service.labor_description = form.get("labor_description", "").strip()
    st = form.get("service_type", SERVICE_TYPE_POPRAVKE)
    service.service_type = st if st in SERVICE_TYPE_LABELS else SERVICE_TYPE_POPRAVKE


def _rebuild_parts(service: Service, form) -> None:
    """Replace the service's parts with the ones posted in the form."""
    for p in list(service.parts):
        db.session.delete(p)
    service.parts.clear()

    names = form.getlist("part_name[]")
    qtys = form.getlist("part_qty[]")
    prices = form.getlist("part_price[]")
    discs = form.getlist("part_disc[]")

    for i, name in enumerate(names):
        name = name.strip()
        if not name:
            continue
        part = Part(
            name=name,
            quantity=_to_float(qtys[i] if i < len(qtys) else 1) or 1.0,
            price=_to_float(prices[i] if i < len(prices) else 0),
            price_with_discount=_to_float(discs[i] if i < len(discs) else 0),
        )
        service.parts.append(part)


def _to_int(value):
    try:
        return int(str(value).replace(" ", "").replace(".", ""))
    except (TypeError, ValueError):
        return None


def _to_float(value):
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return 0.0
