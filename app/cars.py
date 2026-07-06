"""Car registration, listing and editing."""
import os

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, abort,
    current_app,
)
from flask_login import login_required, current_user

from .extensions import db
from .models import Car, Service, FUEL_TYPES
from .security import scoped_query
from .utils import save_image

cars_bp = Blueprint("cars", __name__)


def _normalise_plate(plate: str) -> str:
    return plate.replace(" ", "").upper().strip()


@cars_bp.route("/cars")
@login_required
def list_cars():
    query = request.args.get("q", "").strip()
    if current_user.is_admin:
        cars = scoped_query(Car)
    else:
        car_ids = db.session.query(Service.car_id).filter(
            Service.worker_id == current_user.id
        ).distinct().subquery()
        cars = Car.query.filter(Car.id.in_(db.session.query(car_ids)))
    if query:
        like = f"%{query}%"
        cars = cars.filter(
            db.or_(Car.plate.ilike(like), Car.owner_name.ilike(like),
                   Car.brand.ilike(like), Car.model.ilike(like))
        )
    cars = cars.order_by(Car.owner_name).all()
    return render_template("cars/list.html", cars=cars, q=query)


@cars_bp.route("/car/<int:car_id>")
@login_required
def detail(car_id):
    car = db.session.get(Car, car_id) or abort(404)
    services = car.services
    if not current_user.is_admin:
        services = [s for s in services if s.worker_id == current_user.id]
        if not services:
            abort(403)
    return render_template("cars/detail.html", car=car, services=services)


@cars_bp.route("/car/new", methods=["GET", "POST"])
@login_required
def new():
    prefill_plate = _normalise_plate(request.args.get("plate", ""))
    then = request.args.get("then", "")

    if request.method == "POST":
        plate = _normalise_plate(request.form.get("plate", ""))
        then = request.form.get("then", then)

        if not plate:
            flash("Registarska oznaka je obavezna.", "danger")
            return render_template("cars/form.html", car=None, fuel_types=FUEL_TYPES,
                                   prefill_plate=prefill_plate, then=then)

        existing = Car.query.filter_by(plate=plate).first()
        if existing:
            flash("Vozilo sa tom registracijom već postoji.", "warning")
            return redirect(url_for("cars.detail", car_id=existing.id))

        car = Car(plate=plate, shop_id=current_user.shop_id)
        _apply_form(car, request.form)
        photo = request.files.get("photo")
        if photo and photo.filename:
            car.photo_path = save_image(photo, "cars")

        db.session.add(car)
        db.session.commit()
        flash("Vozilo je registrovano.", "success")

        if then == "service":
            return redirect(url_for("services.new", car_id=car.id))
        return redirect(url_for("cars.detail", car_id=car.id))

    return render_template("cars/form.html", car=None, fuel_types=FUEL_TYPES,
                           prefill_plate=prefill_plate, then=then)


@cars_bp.route("/car/<int:car_id>/edit", methods=["GET", "POST"])
@login_required
def edit(car_id):
    car = db.session.get(Car, car_id) or abort(404)
    if request.method == "POST":
        new_plate = _normalise_plate(request.form.get("plate", ""))
        if new_plate and new_plate != car.plate:
            clash = Car.query.filter_by(plate=new_plate).first()
            if clash and clash.id != car.id:
                flash("Druga vozilo već koristi tu registraciju.", "danger")
                return render_template("cars/form.html", car=car, fuel_types=FUEL_TYPES)
            car.plate = new_plate

        _apply_form(car, request.form)
        photo = request.files.get("photo")
        if photo and photo.filename:
            if car.photo_path:
                old = os.path.join(current_app.config["UPLOAD_FOLDER"], car.photo_path)
                if os.path.exists(old):
                    try:
                        os.remove(old)
                    except OSError:
                        pass
            car.photo_path = save_image(photo, "cars")

        db.session.commit()
        flash("Podaci o vozilu su ažurirani.", "success")
        return redirect(url_for("cars.detail", car_id=car.id))

    return render_template("cars/form.html", car=car, fuel_types=FUEL_TYPES)


def _apply_form(car: Car, form) -> None:
    car.owner_name = form.get("owner_name", "").strip()
    car.phone = form.get("phone", "").strip()
    car.brand = form.get("brand", "").strip()
    car.model = form.get("model", "").strip()
    car.engine = form.get("engine", "").strip()
    car.fuel_type = form.get("fuel_type", "").strip()
    car.year = _to_int(form.get("year"))
    car.mileage = _to_int(form.get("mileage"))


def _to_int(value):
    try:
        return int(str(value).replace(" ", "").replace(".", ""))
    except (TypeError, ValueError):
        return None
