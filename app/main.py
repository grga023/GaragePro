"""Dashboard and first-run company setup."""
import os

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, current_app,
)
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from .extensions import db
from .models import Company, Car, Service, Shop, SERVICE_TYPES, SERVICE_TYPE_LABELS
from .security import admin_required, scoped_query
from .utils import save_image, period_range

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def dashboard():
    if current_user.is_moderator:
        return redirect(url_for("moderator.dashboard"))

    q = scoped_query(Service)
    if not current_user.is_admin:
        q = q.filter(Service.worker_id == current_user.id)
    q = q.options(selectinload(Service.parts))

    from datetime import timedelta
    today_start, today_end = period_range("day")
    month_start, month_end = period_range("month")
    week_start = today_start - timedelta(days=today_start.weekday())

    today_services = q.filter(Service.date == today_start).all()
    month_services = q.filter(Service.date.between(month_start, month_end)).all()
    week_services = q.filter(Service.date.between(week_start, today_start)).all()

    stats = {
        "today_count": len(today_services),
        "today_revenue": sum(s.total_full for s in today_services),
        "month_count": len(month_services),
        "month_revenue": sum(s.total_full for s in month_services),
        "month_profit": sum(s.total_profit for s in month_services),
        "cars_total": scoped_query(Car).count() if current_user.is_admin else
                      db.session.query(func.count(Service.car_id.distinct())).filter(
                          Service.worker_id == current_user.id).scalar(),
    }

    by_type = {}
    for s in month_services:
        by_type.setdefault(s.service_type, []).append(s)
    type_stats = []
    for key, label in SERVICE_TYPES:
        svcs = by_type.get(key, [])
        type_stats.append({
            "key": key,
            "label": label,
            "count": len(svcs),
            "revenue": sum(s.total_full for s in svcs),
            "profit": sum(s.total_profit for s in svcs),
        })

    recent = q.order_by(Service.date.desc(), Service.id.desc()).limit(10).all()

    alerts = []
    if stats["today_count"] == 0:
        alerts.append({"type": "warning", "msg": "⚠️ Danas nema nijednog servisa."})
    if len(week_services) == 0 and today_start.weekday() >= 2:
        alerts.append({"type": "danger", "msg": "🔴 Nema servisa ove nedelje — proverite aktivnost."})
    if stats["month_count"] > 0:
        avg_daily = stats["month_count"] / max((today_start - month_start).days, 1)
        alerts.append({"type": "info", "msg": f"📊 Prosečno {avg_daily:.1f} servisa dnevno ovog meseca. Mesečni profit: {stats['month_profit']:.0f} RSD."})

    return render_template("dashboard.html", stats=stats, recent=recent,
                           type_stats=type_stats, alerts=alerts)


@main_bp.route("/setup", methods=["GET", "POST"])
@login_required
@admin_required
def setup():
    # Moderators use the moderator panel; owners edit their own shop.
    if current_user.is_moderator:
        return redirect(url_for("moderator.index"))

    shop = db.session.get(Shop, current_user.shop_id) if current_user.shop_id else None

    # Fallback: old Company row for backward compat
    company = db.session.get(Company, 1)
    if company is None:
        company = Company(id=1)
        db.session.add(company)
        db.session.commit()

    if request.method == "POST":
        company.name = request.form.get("name", "").strip()
        company.address = request.form.get("address", "").strip()
        company.contact = request.form.get("contact", "").strip()

        # Also sync to the shop record
        if shop:
            shop.name = company.name
            shop.address = company.address
            shop.contact = company.contact

        logo = request.files.get("logo")
        if logo and logo.filename:
            if company.logo_path:
                old = os.path.join(current_app.config["UPLOAD_FOLDER"], company.logo_path)
                if os.path.exists(old):
                    try:
                        os.remove(old)
                    except OSError:
                        pass
            company.logo_path = save_image(logo, "logo", max_dim=600)
            if shop:
                shop.logo_path = company.logo_path

        db.session.commit()
        flash("Podaci o servisu su sačuvani.", "success")
        return redirect(url_for("main.setup"))

    return render_template("setup.html", company=company)
