"""Calendar / appointment booking.

Workers plan their work by booking time slots for a car.  Owners (admins) see
every appointment in their shop and can filter by worker; a worker only ever
sees their own.  When booking, the registration plate is looked up first — if
the car does not exist yet it is created on the spot (plate-first flow, same as
starting a service).
"""
from datetime import datetime, date, time, timedelta

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, abort,
    jsonify,
)
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from .extensions import db
from .models import (
    Car, Appointment, User, FUEL_TYPES,
    SERVICE_TYPES, SERVICE_TYPE_LABELS, SERVICE_TYPE_POPRAVKE,
    APPOINTMENT_STATUSES, APPOINTMENT_STATUS_LABELS,
    APPOINTMENT_SCHEDULED, ROLE_MODERATOR,
)
from .security import scoped_query

calendar_bp = Blueprint("calendar", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalise_plate(plate: str) -> str:
    return plate.replace(" ", "").upper().strip()


def _scoped_appointments():
    """Appointments visible to the current user (shop-scoped; workers see own)."""
    q = scoped_query(Appointment)
    if not current_user.is_admin:
        q = q.filter(Appointment.worker_id == current_user.id)
    return q


def _can_access(appt: Appointment) -> bool:
    if not (current_user.is_admin or appt.worker_id == current_user.id):
        return False
    # Shop scoping for non-moderators.
    if (not current_user.is_moderator and current_user.shop_id
            and appt.shop_id and appt.shop_id != current_user.shop_id):
        return False
    return True


def _shop_workers():
    """Everyone who can be assigned work in the current shop (excl. moderators)."""
    if current_user.is_moderator:
        return (User.query.filter(User.role != ROLE_MODERATOR)
                .order_by(User.full_name).all())
    if current_user.is_admin:
        return (User.query.filter_by(shop_id=current_user.shop_id)
                .filter(User.role != ROLE_MODERATOR)
                .order_by(User.full_name).all())
    return [current_user]


def _parse_date(value, fallback=None):
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return fallback


def _parse_time(value, fallback):
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except (ValueError, AttributeError):
        return fallback


def _event_dict(a: Appointment) -> dict:
    return {
        "id": a.id,
        "date": a.start_at.date().isoformat(),
        "start_time": a.start_at.strftime("%H:%M"),
        "end_time": a.end_at.strftime("%H:%M"),
        "plate": a.car.plate if a.car else "",
        "car_id": a.car_id,
        "car_desc": a.car.description if a.car else "",
        "owner": a.car.owner_name if a.car else "",
        "phone": (a.car.phone if a.car else "") or "",
        "worker": a.worker.full_name if a.worker else "",
        "worker_id": a.worker_id,
        "service_type": a.service_type,
        "service_type_label": SERVICE_TYPE_LABELS.get(a.service_type, a.service_type),
        "status": a.status,
        "status_label": APPOINTMENT_STATUS_LABELS.get(a.status, a.status),
        "note": a.note or "",
        "car_url": url_for("cars.detail", car_id=a.car_id),
        "edit_url": url_for("calendar.edit", appointment_id=a.id),
        "delete_url": url_for("calendar.delete", appointment_id=a.id),
        "status_url": url_for("calendar.set_status", appointment_id=a.id),
        "service_url": url_for("services.new", car_id=a.car_id),
        "can_edit": bool(current_user.is_admin or a.worker_id == current_user.id),
    }


# ---------------------------------------------------------------------------
# Calendar page
# ---------------------------------------------------------------------------
@calendar_bp.route("/calendar")
@login_required
def index():
    if current_user.is_moderator:
        return redirect(url_for("moderator.dashboard"))
    initial = _parse_date(request.args.get("date", ""), date.today())
    return render_template(
        "calendar/index.html",
        initial_date=initial.isoformat(),
        workers=_shop_workers() if current_user.is_admin else [],
    )


# ---------------------------------------------------------------------------
# JSON event feed (consumed by static/js/calendar.js)
# ---------------------------------------------------------------------------
@calendar_bp.route("/calendar/events")
@login_required
def events():
    if current_user.is_moderator:
        return jsonify([])

    start = _parse_date(request.args.get("start", ""), date.today().replace(day=1))
    end = _parse_date(request.args.get("end", ""), start + timedelta(days=42))

    q = (_scoped_appointments()
         .options(joinedload(Appointment.car), joinedload(Appointment.worker))
         .filter(Appointment.start_at >= datetime.combine(start, time.min))
         .filter(Appointment.start_at < datetime.combine(end, time.min)))

    # Owners can narrow to a single worker; workers are already restricted.
    if current_user.is_admin:
        wid = request.args.get("worker_id", type=int)
        if wid:
            q = q.filter(Appointment.worker_id == wid)

    appts = q.order_by(Appointment.start_at).all()
    return jsonify([_event_dict(a) for a in appts])


# ---------------------------------------------------------------------------
# Plate lookup (prefill the form when the car already exists)
# ---------------------------------------------------------------------------
@calendar_bp.route("/calendar/lookup")
@login_required
def lookup():
    plate = _normalise_plate(request.args.get("plate", ""))
    if not plate:
        return jsonify({"found": False})
    car = Car.query.filter_by(plate=plate).first()
    if not car:
        return jsonify({"found": False})
    return jsonify({
        "found": True,
        "car": {
            "id": car.id,
            "owner_name": car.owner_name or "",
            "phone": car.phone or "",
            "brand": car.brand or "",
            "model": car.model or "",
            "engine": car.engine or "",
            "fuel_type": car.fuel_type or "",
            "year": car.year or "",
            "description": car.description,
        },
    })


# ---------------------------------------------------------------------------
# Create appointment (plate-first: create the car if it does not exist)
# ---------------------------------------------------------------------------
@calendar_bp.route("/calendar/new", methods=["GET", "POST"])
@login_required
def new():
    if current_user.is_moderator:
        return redirect(url_for("moderator.dashboard"))

    if request.method == "POST":
        plate = _normalise_plate(request.form.get("plate", ""))
        if not plate:
            flash("Unesite registarsku oznaku.", "danger")
            return _render_form(None)

        car = Car.query.filter_by(plate=plate).first()
        if car is None:
            owner_name = request.form.get("owner_name", "").strip()
            if not owner_name:
                flash("Vozilo ne postoji — unesite bar ime vlasnika da bi bilo kreirano.",
                      "danger")
                return _render_form(None)
            car = Car(
                plate=plate,
                owner_name=owner_name,
                phone=request.form.get("phone", "").strip(),
                brand=request.form.get("brand", "").strip(),
                model=request.form.get("model", "").strip(),
                engine=request.form.get("engine", "").strip(),
                fuel_type=request.form.get("fuel_type", "").strip(),
                year=_to_int(request.form.get("year")),
                shop_id=current_user.shop_id,
            )
            db.session.add(car)
            db.session.flush()
            flash(f"Vozilo {plate} je kreirano.", "info")

        appt = Appointment(
            shop_id=current_user.shop_id,
            car_id=car.id,
            created_by_id=current_user.id,
        )
        _apply_appointment_form(appt, request.form)
        db.session.add(appt)
        db.session.commit()
        flash("Termin je zakazan.", "success")
        return redirect(url_for("calendar.index", date=appt.start_at.date().isoformat()))

    return _render_form(None)


# ---------------------------------------------------------------------------
# Edit / delete / status
# ---------------------------------------------------------------------------
@calendar_bp.route("/appointment/<int:appointment_id>/edit", methods=["GET", "POST"])
@login_required
def edit(appointment_id):
    appt = db.session.get(Appointment, appointment_id) or abort(404)
    if not _can_access(appt):
        abort(403)

    if request.method == "POST":
        _apply_appointment_form(appt, request.form)
        db.session.commit()
        flash("Termin je ažuriran.", "success")
        return redirect(url_for("calendar.index", date=appt.start_at.date().isoformat()))

    return _render_form(appt)


@calendar_bp.route("/appointment/<int:appointment_id>/delete", methods=["POST"])
@login_required
def delete(appointment_id):
    appt = db.session.get(Appointment, appointment_id) or abort(404)
    if not _can_access(appt):
        abort(403)
    day = appt.start_at.date().isoformat()
    db.session.delete(appt)
    db.session.commit()
    flash("Termin je obrisan.", "info")
    return redirect(url_for("calendar.index", date=day))


@calendar_bp.route("/appointment/<int:appointment_id>/status", methods=["POST"])
@login_required
def set_status(appointment_id):
    appt = db.session.get(Appointment, appointment_id) or abort(404)
    if not _can_access(appt):
        abort(403)
    status = request.form.get("status", "")
    if status not in APPOINTMENT_STATUS_LABELS:
        abort(400)
    appt.status = status
    db.session.commit()
    flash(f"Termin: {APPOINTMENT_STATUS_LABELS[status].lower()}.", "success")
    return redirect(url_for("calendar.index", date=appt.start_at.date().isoformat()))


# ---------------------------------------------------------------------------
# Form helpers
# ---------------------------------------------------------------------------
def _render_form(appt):
    prefill_date = _parse_date(request.args.get("date", ""), date.today())
    return render_template(
        "calendar/form.html",
        appointment=appt,
        workers=_shop_workers(),
        service_types=SERVICE_TYPES,
        statuses=APPOINTMENT_STATUSES,
        fuel_types=FUEL_TYPES,
        prefill_date=prefill_date.isoformat(),
    )


def _apply_appointment_form(appt: Appointment, form) -> None:
    d = _parse_date(form.get("date", ""), date.today())
    start_t = _parse_time(form.get("start_time", ""), time(9, 0))
    end_t = _parse_time(form.get("end_time", ""), None)

    appt.start_at = datetime.combine(d, start_t)
    if end_t is None or datetime.combine(d, end_t) <= appt.start_at:
        appt.end_at = appt.start_at + timedelta(hours=1)
    else:
        appt.end_at = datetime.combine(d, end_t)

    st = form.get("service_type", SERVICE_TYPE_POPRAVKE)
    appt.service_type = st if st in SERVICE_TYPE_LABELS else SERVICE_TYPE_POPRAVKE
    appt.note = form.get("note", "").strip()

    # Status (only meaningful when editing).
    status = form.get("status", "")
    if status in APPOINTMENT_STATUS_LABELS:
        appt.status = status
    elif not appt.status:
        appt.status = APPOINTMENT_SCHEDULED

    # Worker assignment: owners choose; workers are pinned to themselves.
    if current_user.is_admin:
        wid = _to_int(form.get("worker_id"))
        worker = db.session.get(User, wid) if wid else None
        if worker and (current_user.is_moderator or worker.shop_id == current_user.shop_id):
            appt.worker_id = worker.id
        elif not appt.worker_id:
            appt.worker_id = current_user.id
    elif not appt.worker_id:
        appt.worker_id = current_user.id


def _to_int(value):
    try:
        return int(str(value).replace(" ", ""))
    except (TypeError, ValueError):
        return None
