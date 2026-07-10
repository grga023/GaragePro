"""Journals (daily / weekly / monthly) and profit / parts analytics."""
from datetime import date, datetime, timedelta
from collections import OrderedDict

import csv
import io

from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, abort,
    Response,
)
from flask_login import login_required, current_user

from .extensions import db
from .models import Car, Service, User, ROLE_ADMIN, SERVICE_TYPES, SERVICE_TYPE_LABELS
from .security import admin_required, scoped_query
from .utils import period_range, PERIOD_LABELS, sr_date, SR_MONTHS
from .email_utils import send_email
from sqlalchemy.orm import selectinload

reports_bp = Blueprint("reports", __name__)


def _build_charts(services, totals, start, end, by_worker):
    """Assemble data for the analytics charts (revenue/profit over time,
    revenue structure, parts price comparison, profit per worker)."""
    span = (end - start).days
    monthly = span > 62  # switch to monthly buckets for long ranges

    buckets = OrderedDict()
    if monthly:
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            buckets[(y, m)] = [0.0, 0.0]
            m += 1
            if m > 12:
                m, y = 1, y + 1
    else:
        cur = start
        while cur <= end:
            buckets[cur] = [0.0, 0.0]
            cur += timedelta(days=1)

    for s in services:
        key = (s.date.year, s.date.month) if monthly else s.date
        if key in buckets:
            buckets[key][0] += s.total_full
            buckets[key][1] += s.total_profit

    labels, revenue, profit = [], [], []
    for key, vals in buckets.items():
        if monthly:
            labels.append(f"{SR_MONTHS[key[1]][:3]} {key[0]}")
        else:
            labels.append(f"{key.day}.{key.month}.")
        revenue.append(round(vals[0], 2))
        profit.append(round(vals[1], 2))

    charts = {
        "labels": labels,
        "revenue": revenue,
        "profit": profit,
        "structure": {
            "labels": ["Delovi (prodajna)", "Rad"],
            "data": [round(totals["parts_full"], 2), round(totals["labor"], 2)],
        },
        "parts": {
            "labels": ["Prodajna (bez pop.)", "Nabavna (sa pop.)", "Marža"],
            "data": [round(totals["parts_full"], 2), round(totals["parts_cost"], 2),
                     round(totals["parts_profit"], 2)],
        },
        "byworker": None,
    }
    if by_worker:
        charts["byworker"] = {
            "labels": [r["worker"].full_name for r in by_worker],
            "data": [round(r["totals"]["profit"], 2) for r in by_worker],
        }
    return charts


def summarize(services):
    return {
        "count": len(services),
        "parts_full": sum(s.parts_total_full for s in services),
        "parts_cost": sum(s.parts_total_cost for s in services),
        "parts_profit": sum(s.parts_profit for s in services),
        "labor": sum((s.labor_price or 0.0) for s in services),
        "revenue": sum(s.total_full for s in services),
        "profit": sum(s.total_profit for s in services),
    }


def _resolve_scope(scope, worker_param):
    """Return (worker_or_None, scope_label) enforcing permissions."""
    if not current_user.is_admin:
        return current_user, f"Radnik: {current_user.full_name}"

    if scope == "all":
        return None, "Ceo servis (svi radnici)"
    if scope and scope.startswith("worker:"):
        try:
            wid = int(scope.split(":", 1)[1])
        except ValueError:
            wid = None
        worker = db.session.get(User, wid) if wid else None
        if worker:
            return worker, f"Radnik: {worker.full_name}"
    # default for admin: themselves
    return current_user, f"Radnik: {current_user.full_name}"


def _services_in_range(start, end, worker, shop_id=None, service_type=None):
    q = Service.query.filter(Service.date.between(start, end))
    if shop_id:
        q = q.filter(Service.shop_id == shop_id)
    if worker is not None:
        q = q.filter(Service.worker_id == worker.id)
    if service_type and service_type in SERVICE_TYPE_LABELS:
        q = q.filter(Service.service_type == service_type)
    return (q.order_by(Service.date.desc(), Service.id.desc())
             .options(selectinload(Service.parts))
             .all())


def compose_journal(period, ref, worker=None, scope_label=None, shop_id=None):
    """Build a journal for a worker (or the whole shop when worker is None).

    Pure function — does NOT read current_user, so it is safe to call from
    the background scheduler as well as from web requests.
    """
    start, end = period_range(period, ref)
    services = _services_in_range(start, end, worker, shop_id=shop_id)
    totals = summarize(services)

    # Per-worker breakdown when looking at the whole shop
    by_worker = None
    if worker is None:
        grouped = {}
        for s in services:
            grouped.setdefault(s.worker, []).append(s)
        by_worker = [
            {"worker": w, "totals": summarize(items)}
            for w, items in grouped.items()
        ]
        by_worker.sort(key=lambda r: r["totals"]["revenue"], reverse=True)

    if scope_label is None:
        scope_label = (f"Radnik: {worker.full_name}" if worker
                       else "Ceo servis (svi radnici)")

    return {
        "period": period,
        "period_label": PERIOD_LABELS.get(period, period),
        "start": start,
        "end": end,
        "scope_label": scope_label,
        "worker": worker,
        "services": services,
        "totals": totals,
        "by_worker": by_worker,
    }


@reports_bp.route("/reports")
@login_required
def index():
    period = request.args.get("period", "day")
    if period not in ("day", "week", "month"):
        period = "day"
    scope = request.args.get("scope", "me")
    ref_str = request.args.get("date", date.today().isoformat())
    try:
        ref = datetime.strptime(ref_str, "%Y-%m-%d").date()
    except ValueError:
        ref = date.today()

    worker, scope_label = _resolve_scope(scope, None)
    shop_id = None if current_user.is_moderator else current_user.shop_id
    journal = compose_journal(period, ref, worker, scope_label, shop_id=shop_id)
    workers = (User.query.filter_by(shop_id=current_user.shop_id).order_by(User.full_name).all()
               if current_user.is_admin and not current_user.is_moderator
               else User.query.order_by(User.full_name).all() if current_user.is_moderator else [])

    return render_template(
        "reports/index.html",
        journal=journal,
        workers=workers,
        ref=ref,
        period=period,
        scope=scope,
    )


@reports_bp.route("/reports/send", methods=["POST"])
@login_required
def send():
    period = request.form.get("period", "day")
    scope = request.form.get("scope", "me")
    ref_str = request.form.get("date", date.today().isoformat())
    try:
        ref = datetime.strptime(ref_str, "%Y-%m-%d").date()
    except ValueError:
        ref = date.today()

    # Overall journal may only be sent by (and to) an admin.
    if scope == "all" and not current_user.is_admin:
        abort(403)

    journal = compose_journal(period, ref, *_resolve_scope(scope, None))

    # Determine recipients per the rules:
    #  - worker journal  -> that worker's e-mail
    #  - overall journal -> admin(s) only
    if scope == "all":
        admins = User.query.filter_by(role=ROLE_ADMIN, active=True).all()
        recipients = [a.email for a in admins]
        recipients += [current_user.email]
    else:
        recipients = [journal["worker"].email] if journal["worker"] else []

    recipients = sorted(set(r for r in recipients if r))

    subject = (f"{journal['period_label']} žurnal — {journal['scope_label']} "
               f"({sr_date(journal['start'])} - {sr_date(journal['end'])})")
    html = render_template("email/journal.html", journal=journal)

    try:
        send_email(recipients, subject, html)
        flash(f"Žurnal je poslat na: {', '.join(recipients)}", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Slanje e-maila nije uspelo: {exc}", "danger")

    return redirect(url_for("reports.index", period=period, scope=scope,
                            date=ref.isoformat()))


@reports_bp.route("/analytics")
@login_required
def analytics():
    """Profit + parts price analysis over a custom date range."""
    today = date.today()
    start_str = request.args.get("start", today.replace(day=1).isoformat())
    end_str = request.args.get("end", today.isoformat())
    scope = request.args.get("scope", "me")
    try:
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
    except ValueError:
        start, end = today.replace(day=1), today

    service_type = request.args.get("service_type", "")

    worker, scope_label = _resolve_scope(scope, None)
    shop_id = None if current_user.is_moderator else current_user.shop_id
    services = _services_in_range(start, end, worker, shop_id=shop_id,
                                  service_type=service_type or None)
    totals = summarize(services)

    by_worker = None
    if worker is None:
        grouped = {}
        for s in services:
            grouped.setdefault(s.worker, []).append(s)
        by_worker = [
            {"worker": w, "totals": summarize(items)}
            for w, items in grouped.items()
        ]
        by_worker.sort(key=lambda r: r["totals"]["profit"], reverse=True)

    # Breakdown by service type
    by_type = {}
    all_services_unfiltered = _services_in_range(start, end, worker, shop_id=shop_id)
    for s in all_services_unfiltered:
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

    workers = User.query.order_by(User.full_name).all() if current_user.is_admin else []
    charts = _build_charts(services, totals, start, end, by_worker)
    from flask import current_app
    charts["currency"] = current_app.config.get("CURRENCY", "RSD")

    # Type distribution chart data
    charts["bytype"] = {
        "labels": [t["label"] for t in type_stats],
        "data": [round(t["revenue"], 2) for t in type_stats],
    }

    return render_template(
        "reports/analytics.html",
        totals=totals, services=services, start=start, end=end,
        scope=scope, scope_label=scope_label, by_worker=by_worker, workers=workers,
        charts=charts, type_stats=type_stats, service_type=service_type,
    )


@reports_bp.route("/analytics/export")
@login_required
def analytics_export():
    today = date.today()
    start_str = request.args.get("start", today.replace(day=1).isoformat())
    end_str = request.args.get("end", today.isoformat())
    scope = request.args.get("scope", "me")
    service_type = request.args.get("service_type", "")
    try:
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
    except ValueError:
        start, end = today.replace(day=1), today

    worker, scope_label = _resolve_scope(scope, None)
    shop_id = None if current_user.is_moderator else current_user.shop_id
    services = _services_in_range(start, end, worker, shop_id=shop_id,
                                  service_type=service_type or None)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Datum", "Vrsta", "Registracija", "Vozilo", "Vlasnik",
                "Radnik", "Delovi (prodajna)", "Delovi (nabavna)", "Rad",
                "Ukupno", "Profit"])
    for s in services:
        w.writerow([
            s.date.isoformat(), SERVICE_TYPE_LABELS.get(s.service_type, ""),
            s.car.plate, s.car.description, s.car.owner_name,
            s.worker.full_name,
            f"{s.parts_total_full:.2f}", f"{s.parts_total_cost:.2f}",
            f"{(s.labor_price or 0):.2f}",
            f"{s.total_full:.2f}", f"{s.total_profit:.2f}",
        ])

    buf.seek(0)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=analitika_{start}_{end}.csv"},
    )


@reports_bp.route("/top-customers")
@login_required
def top_customers():
    today = date.today()
    start_str = request.args.get("start", today.replace(month=1, day=1).isoformat())
    end_str = request.args.get("end", today.isoformat())
    try:
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
    except ValueError:
        start, end = today.replace(month=1, day=1), today

    shop_id = None if current_user.is_moderator else current_user.shop_id
    q = Service.query.filter(Service.date.between(start, end))
    if shop_id:
        q = q.filter(Service.shop_id == shop_id)
    if not current_user.is_admin:
        q = q.filter(Service.worker_id == current_user.id)
    services = q.all()

    by_owner = {}
    by_car = {}
    for s in services:
        car = s.car
        owner = car.owner_name
        by_owner.setdefault(owner, {"services": 0, "revenue": 0.0, "profit": 0.0, "phone": car.phone or ""})
        by_owner[owner]["services"] += 1
        by_owner[owner]["revenue"] += s.total_full
        by_owner[owner]["profit"] += s.total_profit

        by_car.setdefault(car.id, {"car": car, "services": 0, "revenue": 0.0, "profit": 0.0})
        by_car[car.id]["services"] += 1
        by_car[car.id]["revenue"] += s.total_full
        by_car[car.id]["profit"] += s.total_profit

    top_owners = sorted(by_owner.items(), key=lambda x: x[1]["revenue"], reverse=True)[:20]
    top_vehicles = sorted(by_car.values(), key=lambda x: x["revenue"], reverse=True)[:20]

    return render_template(
        "reports/top_customers.html",
        top_owners=top_owners, top_vehicles=top_vehicles,
        start=start, end=end,
    )
