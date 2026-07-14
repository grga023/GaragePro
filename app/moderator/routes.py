"""System moderator panel: manage shops, assign owners, overview."""
import csv
import io
import os
from datetime import date, datetime, timedelta
from collections import OrderedDict

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, abort,
    current_app, Response,
)
from flask_login import login_required, current_user
from sqlalchemy import func

from ..extensions import db
from ..models import (
    Shop, User, Car, Service, Part, EmailConfig, GlobalMailConfig,
    ROLE_ADMIN, ROLE_MODERATOR, ROLE_WORKER,
    SERVICE_TYPES, SERVICE_TYPE_LABELS,
)
from ..security import moderator_required
from ..utils import save_image, period_range, SR_MONTHS
from ..email_utils import send_email
from ..updater import (
    current_version, list_tags, is_git_repo, validate_ref, perform_update,
    service_name,
)

moderator_bp = Blueprint("moderator", __name__, url_prefix="/moderator")


def _summarize(services):
    return {
        "count": len(services),
        "parts_full": sum(s.parts_total_full for s in services),
        "parts_cost": sum(s.parts_total_cost for s in services),
        "parts_profit": sum(s.parts_profit for s in services),
        "labor": sum((s.labor_price or 0.0) for s in services),
        "revenue": sum(s.total_full for s in services),
        "profit": sum(s.total_profit for s in services),
    }


@moderator_bp.route("/")
@login_required
@moderator_required
def index():
    return redirect(url_for("moderator.dashboard"))


@moderator_bp.route("/dashboard")
@login_required
@moderator_required
def dashboard():
    today = date.today()

    # Period filter (default: this month)
    period = request.args.get("period", "month")
    if period == "today":
        period_start, period_end = today, today
        period_label = "Danas"
    elif period == "week":
        period_start = today - timedelta(days=today.weekday())
        period_end = today
        period_label = "Ova nedelja"
    elif period == "year":
        period_start = today.replace(month=1, day=1)
        period_end = today
        period_label = "Ova godina"
    else:
        period = "month"
        period_start = today.replace(day=1)
        period_end = today
        period_label = "Ovaj mesec"

    # Service type filter
    filter_type = request.args.get("service_type", "")

    all_services = Service.query.all()
    today_services = [s for s in all_services if s.date == today]
    period_services = [s for s in all_services if period_start <= s.date <= period_end]

    # Apply service type filter for filtered stats
    if filter_type and filter_type in SERVICE_TYPE_LABELS:
        filtered_services = [s for s in period_services if s.service_type == filter_type]
    else:
        filtered_services = period_services

    stats = {
        "total_shops": Shop.query.count(),
        "total_users": User.query.filter(User.role != ROLE_MODERATOR).count(),
        "total_cars": Car.query.count(),
        "total_services": len(all_services),
        "today_count": len(today_services),
        "today_revenue": sum(s.total_full for s in today_services),
        "period_count": len(filtered_services),
        "period_revenue": sum(s.total_full for s in filtered_services),
        "period_profit": sum(s.total_profit for s in filtered_services),
        "period_labor": sum((s.labor_price or 0.0) for s in filtered_services),
        "period_parts_full": sum(s.parts_total_full for s in filtered_services),
        "period_parts_cost": sum(s.parts_total_cost for s in filtered_services),
        "period_parts_profit": sum(s.parts_profit for s in filtered_services),
    }

    # Type breakdown (always from unfiltered period services)
    by_type = {}
    for s in period_services:
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
            "labor": sum((s.labor_price or 0.0) for s in svcs),
            "parts_full": sum(s.parts_total_full for s in svcs),
            "parts_cost": sum(s.parts_total_cost for s in svcs),
        })

    # Shop breakdown
    by_shop = {}
    for s in filtered_services:
        by_shop.setdefault(s.shop_id, []).append(s)
    shop_stats = []
    shops = {sh.id: sh for sh in Shop.query.all()}
    for shop_id, svcs in by_shop.items():
        shop = shops.get(shop_id)
        if not shop:
            continue
        shop_stats.append({
            "shop": shop,
            "count": len(svcs),
            "revenue": sum(s.total_full for s in svcs),
            "profit": sum(s.total_profit for s in svcs),
        })
    shop_stats.sort(key=lambda r: r["revenue"], reverse=True)

    # Worker performance
    by_worker = {}
    for s in filtered_services:
        by_worker.setdefault(s.worker_id, []).append(s)
    worker_stats = []
    all_users = {u.id: u for u in User.query.filter(User.role != ROLE_MODERATOR).all()}
    for wid, svcs in by_worker.items():
        user = all_users.get(wid)
        if not user:
            continue
        worker_stats.append({
            "name": user.full_name,
            "count": len(svcs),
            "revenue": sum(s.total_full for s in svcs),
            "profit": sum(s.total_profit for s in svcs),
            "labor": sum((s.labor_price or 0.0) for s in svcs),
        })
    worker_stats.sort(key=lambda r: r["revenue"], reverse=True)
    worker_chart = {
        "labels": [w["name"] for w in worker_stats],
        "revenue": [round(w["revenue"], 2) for w in worker_stats],
        "profit": [round(w["profit"], 2) for w in worker_stats],
        "count": [w["count"] for w in worker_stats],
    }

    # Recent services (filtered by type if selected)
    recent_q = Service.query
    if filter_type and filter_type in SERVICE_TYPE_LABELS:
        recent_q = recent_q.filter(Service.service_type == filter_type)
    recent = recent_q.order_by(
        Service.date.desc(), Service.id.desc()
    ).limit(20).all()

    # Chart: service type distribution (doughnut)
    type_chart = {
        "labels": [t["label"] for t in type_stats],
        "data": [t["count"] for t in type_stats],
        "revenue": [round(t["revenue"], 2) for t in type_stats],
    }

    # Chart: daily/monthly trend for the period
    span = (period_end - period_start).days
    monthly = span > 62
    trend_buckets = OrderedDict()
    if monthly:
        y, m = period_start.year, period_start.month
        while (y, m) <= (period_end.year, period_end.month):
            trend_buckets[(y, m)] = [0.0, 0.0, 0]
            m += 1
            if m > 12:
                m, y = 1, y + 1
    else:
        cur = period_start
        while cur <= period_end:
            trend_buckets[cur] = [0.0, 0.0, 0]
            cur += timedelta(days=1)

    for s in filtered_services:
        key = (s.date.year, s.date.month) if monthly else s.date
        if key in trend_buckets:
            trend_buckets[key][0] += s.total_full
            trend_buckets[key][1] += s.total_profit
            trend_buckets[key][2] += 1

    trend_labels, trend_revenue, trend_profit, trend_count = [], [], [], []
    for key, vals in trend_buckets.items():
        if monthly:
            trend_labels.append(f"{SR_MONTHS[key[1]][:3]} {key[0]}")
        else:
            trend_labels.append(f"{key.day}.{key.month}.")
        trend_revenue.append(round(vals[0], 2))
        trend_profit.append(round(vals[1], 2))
        trend_count.append(vals[2])

    trend_chart = {
        "labels": trend_labels,
        "revenue": trend_revenue,
        "profit": trend_profit,
        "count": trend_count,
    }

    alerts = []
    if stats["today_count"] == 0:
        alerts.append({"type": "warning", "msg": "⚠️ Danas nema nijednog servisa u celom sistemu."})
    inactive_shops = [sh for sh in shops.values()
                      if sh.is_active and sh.id not in by_shop]
    if inactive_shops and (period_end - period_start).days >= 6:
        names = ", ".join(s.name for s in inactive_shops[:3])
        alerts.append({"type": "danger", "msg": f"🔴 Neaktivne radnje ({period_label.lower()}): {names}"})
    if stats["period_count"] > 0:
        days = max((period_end - period_start).days, 1)
        avg = stats["period_count"] / days
        alerts.append({"type": "info", "msg": f"📊 Prosečno {avg:.1f} servisa/dan. Profit: {stats['period_profit']:,.0f} RSD."})

    return render_template(
        "moderator/dashboard.html",
        stats=stats, type_stats=type_stats, shop_stats=shop_stats,
        worker_stats=worker_stats, worker_chart=worker_chart,
        recent=recent, type_chart=type_chart, trend_chart=trend_chart,
        period=period, period_label=period_label,
        period_start=period_start, period_end=period_end,
        filter_type=filter_type, alerts=alerts,
    )


@moderator_bp.route("/shops")
@login_required
@moderator_required
def shops():
    shops = Shop.query.order_by(Shop.name).all()
    shop_stats = []
    for shop in shops:
        users_count = User.query.filter_by(shop_id=shop.id).count()
        cars_count = Car.query.filter_by(shop_id=shop.id).count()
        services_count = Service.query.filter_by(shop_id=shop.id).count()
        owner = User.query.filter_by(shop_id=shop.id, role=ROLE_ADMIN).first()
        shop_stats.append({
            "shop": shop,
            "owner": owner,
            "users": users_count,
            "cars": cars_count,
            "services": services_count,
        })
    return render_template("moderator/shops.html", shop_stats=shop_stats)


@moderator_bp.route("/shop/new", methods=["GET", "POST"])
@login_required
@moderator_required
def new_shop():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Naziv servisa je obavezan.", "danger")
            return render_template("moderator/shop_form.html", shop=None)

        shop = Shop(
            name=name,
            address=request.form.get("address", "").strip(),
            contact=request.form.get("contact", "").strip(),
        )
        logo = request.files.get("logo")
        if logo and logo.filename:
            shop.logo_path = save_image(logo, "logo", max_dim=600)

        db.session.add(shop)
        db.session.commit()
        flash(f'Servis "{shop.name}" je kreiran.', "success")
        return redirect(url_for("moderator.shop_detail", shop_id=shop.id))

    return render_template("moderator/shop_form.html", shop=None)


@moderator_bp.route("/shop/<int:shop_id>")
@login_required
@moderator_required
def shop_detail(shop_id):
    shop = db.session.get(Shop, shop_id) or abort(404)
    users = User.query.filter_by(shop_id=shop.id).order_by(User.full_name).all()
    cars = Car.query.filter_by(shop_id=shop.id).order_by(Car.owner_name).all()
    services = (Service.query.filter_by(shop_id=shop.id)
                .order_by(Service.date.desc(), Service.id.desc())
                .limit(20).all())
    all_users = User.query.filter(
        (User.shop_id.is_(None)) | (User.shop_id == shop.id),
        User.role != ROLE_MODERATOR,
    ).order_by(User.full_name).all()
    return render_template("moderator/shop_detail.html",
                           shop=shop, users=users, cars=cars,
                           services=services, all_users=all_users)


@moderator_bp.route("/shop/<int:shop_id>/edit", methods=["GET", "POST"])
@login_required
@moderator_required
def edit_shop(shop_id):
    shop = db.session.get(Shop, shop_id) or abort(404)
    if request.method == "POST":
        shop.name = request.form.get("name", "").strip() or shop.name
        shop.address = request.form.get("address", "").strip()
        shop.contact = request.form.get("contact", "").strip()

        logo = request.files.get("logo")
        if logo and logo.filename:
            if shop.logo_path:
                old = os.path.join(current_app.config["UPLOAD_FOLDER"], shop.logo_path)
                if os.path.exists(old):
                    try:
                        os.remove(old)
                    except OSError:
                        pass
            shop.logo_path = save_image(logo, "logo", max_dim=600)

        db.session.commit()
        flash("Podaci o servisu su ažurirani.", "success")
        return redirect(url_for("moderator.shop_detail", shop_id=shop.id))

    return render_template("moderator/shop_form.html", shop=shop)


@moderator_bp.route("/shop/<int:shop_id>/email", methods=["GET", "POST"])
@login_required
@moderator_required
def email_config(shop_id):
    """Per-shop automatic report schedule and recipient list.

    SMTP delivery uses the single global mailbox (see ``mail_config``); here the
    moderator only picks which shop members (and any extra addresses) receive
    the automatic journals.
    """
    shop = db.session.get(Shop, shop_id) or abort(404)
    ec = shop.email_config

    # Shop members that can be picked as recipients (owners + workers).
    shop_users = (User.query
                  .filter(User.shop_id == shop.id,
                          User.role != ROLE_MODERATOR,
                          User.email.isnot(None), User.email != "")
                  .order_by(User.full_name).all())

    if request.method == "POST":
        if ec is None:
            ec = EmailConfig(shop_id=shop.id)
            db.session.add(ec)

        f = request.form
        # Merge the checked shop members with any extra typed-in addresses.
        picked = request.form.getlist("recipient_users")
        extra_raw = f.get("recipients", "")
        merged = (",".join(picked) + "," + extra_raw).replace("\n", ",").replace(";", ",")
        seen, out = set(), []
        for addr in (a.strip() for a in merged.split(",")):
            if addr and addr.lower() not in seen:
                seen.add(addr.lower())
                out.append(addr)
        ec.recipients = "\n".join(out)

        ec.enabled = f.get("enabled") == "on"
        ec.send_daily = f.get("send_daily") == "on"
        ec.send_weekly = f.get("send_weekly") == "on"
        ec.send_monthly = f.get("send_monthly") == "on"
        db.session.commit()
        flash("E-mail podešavanja su sačuvana.", "success")
        return redirect(url_for("moderator.email_config", shop_id=shop.id))

    ec = ec or EmailConfig(shop_id=shop.id)
    current = ec.recipient_list()
    selected_emails = {a.lower() for a in current}
    user_emails = {u.email.lower() for u in shop_users}
    extra_recipients = "\n".join(a for a in current if a.lower() not in user_emails)

    return render_template("moderator/email_config.html",
                           shop=shop, ec=ec, shop_users=shop_users,
                           selected_emails=selected_emails,
                           extra_recipients=extra_recipients)


@moderator_bp.route("/shop/<int:shop_id>/email/test", methods=["POST"])
@login_required
@moderator_required
def email_test(shop_id):
    """Send a test e-mail using the global mailbox settings."""
    shop = db.session.get(Shop, shop_id) or abort(404)
    ec = shop.email_config
    gcfg = GlobalMailConfig.get()
    if not gcfg.smtp_host:
        flash("Globalni SMTP nalog nije podešen. Otvorite ✉️ E-mail (globalno).",
              "danger")
        return redirect(url_for("moderator.email_config", shop_id=shop.id))

    test_to = request.form.get("test_to", "").strip()
    recipients = [test_to] if test_to else (ec.recipient_list() if ec else [])
    if not recipients:
        owners = User.query.filter_by(shop_id=shop.id, role=ROLE_ADMIN, active=True).all()
        recipients = [o.email for o in owners if o.email]
    if not recipients:
        flash("Nema primalaca. Unesite test adresu ili podesite primaoce.", "danger")
        return redirect(url_for("moderator.email_config", shop_id=shop.id))

    html = render_template("email/test.html", shop=shop)
    try:
        send_email(recipients, f"GaragePro — test e-mail ({shop.name})", html,
                   settings=gcfg.smtp_settings())
        flash(f"Test e-mail je poslat na: {', '.join(recipients)}", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Slanje test e-maila nije uspelo: {exc}", "danger")
    return redirect(url_for("moderator.email_config", shop_id=shop.id))


@moderator_bp.route("/shop/<int:shop_id>/toggle", methods=["POST"])
@login_required
@moderator_required
def toggle_shop(shop_id):
    shop = db.session.get(Shop, shop_id) or abort(404)
    shop.is_active = not shop.is_active
    db.session.commit()
    status = "aktiviran" if shop.is_active else "deaktiviran"
    flash(f'Servis "{shop.name}" je {status}.', "success")
    return redirect(url_for("moderator.index"))


@moderator_bp.route("/shop/<int:shop_id>/assign", methods=["POST"])
@login_required
@moderator_required
def assign_user(shop_id):
    shop = db.session.get(Shop, shop_id) or abort(404)
    user_id = request.form.get("user_id", type=int)
    role = request.form.get("role", ROLE_WORKER)
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        flash("Korisnik nije pronađen.", "danger")
        return redirect(url_for("moderator.shop_detail", shop_id=shop.id))

    user.shop_id = shop.id
    if role == ROLE_ADMIN:
        user.role = ROLE_ADMIN
    else:
        user.role = ROLE_WORKER
    db.session.commit()
    flash(f'Korisnik {user.full_name} je dodeljen servisu "{shop.name}".', "success")
    return redirect(url_for("moderator.shop_detail", shop_id=shop.id))


@moderator_bp.route("/shop/<int:shop_id>/remove/<int:user_id>", methods=["POST"])
@login_required
@moderator_required
def remove_user(shop_id, user_id):
    shop = db.session.get(Shop, shop_id) or abort(404)
    user = db.session.get(User, user_id) or abort(404)
    if user.shop_id != shop.id:
        abort(400)
    user.shop_id = None
    user.role = ROLE_WORKER
    db.session.commit()
    flash(f"Korisnik {user.full_name} je uklonjen iz servisa.", "success")
    return redirect(url_for("moderator.shop_detail", shop_id=shop.id))


@moderator_bp.route("/dashboard/export")
@login_required
@moderator_required
def dashboard_export():
    today = date.today()
    period = request.args.get("period", "month")
    if period == "today":
        period_start, period_end = today, today
    elif period == "week":
        period_start = today - timedelta(days=today.weekday())
        period_end = today
    elif period == "year":
        period_start = today.replace(month=1, day=1)
        period_end = today
    else:
        period_start = today.replace(day=1)
        period_end = today

    filter_type = request.args.get("service_type", "")
    q = Service.query.filter(Service.date.between(period_start, period_end))
    if filter_type and filter_type in SERVICE_TYPE_LABELS:
        q = q.filter(Service.service_type == filter_type)
    services = q.order_by(Service.date.desc()).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Datum", "Vrsta", "Radnja", "Registracija", "Vozilo", "Vlasnik",
                "Radnik", "Delovi (prodajna)", "Delovi (nabavna)", "Rad",
                "Ukupno", "Profit"])
    for s in services:
        shop_name = ""
        if s.shop_id:
            shop = Shop.query.get(s.shop_id)
            shop_name = shop.name if shop else ""
        w.writerow([
            s.date.isoformat(), SERVICE_TYPE_LABELS.get(s.service_type, ""),
            shop_name, s.car.plate, s.car.description, s.car.owner_name,
            s.worker.full_name,
            f"{s.parts_total_full:.2f}", f"{s.parts_total_cost:.2f}",
            f"{(s.labor_price or 0):.2f}",
            f"{s.total_full:.2f}", f"{s.total_profit:.2f}",
        ])

    buf.seek(0)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=dashboard_{period_start}_{period_end}.csv"},
    )


# ─────────────────────────── Global e-mail (single mailbox) ────────────────
@moderator_bp.route("/mail", methods=["GET", "POST"])
@login_required
@moderator_required
def mail_config():
    """One SMTP mailbox shared by every service. Moderator-only."""
    cfg = GlobalMailConfig.get()

    if request.method == "POST":
        f = request.form
        cfg.smtp_host = f.get("smtp_host", "").strip()
        cfg.smtp_port = f.get("smtp_port", type=int) or 587
        sec = f.get("smtp_security", "starttls")
        cfg.smtp_security = sec if sec in GlobalMailConfig.SECURITY_CHOICES else "starttls"
        cfg.smtp_user = f.get("smtp_user", "").strip()
        # Only overwrite the stored password when a new value is entered.
        new_pw = f.get("smtp_password", "")
        if new_pw:
            cfg.smtp_password = new_pw
        cfg.from_addr = f.get("from_addr", "").strip()
        cfg.enabled = f.get("enabled") == "on"
        db.session.commit()
        flash("E-mail podešavanja su sačuvana.", "success")
        return redirect(url_for("moderator.mail_config"))

    return render_template("moderator/mail_config.html", cfg=cfg)


@moderator_bp.route("/mail/test", methods=["POST"])
@login_required
@moderator_required
def mail_test():
    """Send a test e-mail using the global mailbox settings."""
    cfg = GlobalMailConfig.get()
    if not cfg.smtp_host:
        flash("Prvo sačuvajte SMTP podešavanja (SMTP host je obavezan).", "danger")
        return redirect(url_for("moderator.mail_config"))

    test_to = request.form.get("test_to", "").strip() or cfg.from_addr or cfg.smtp_user
    if not test_to:
        flash("Unesite test adresu.", "danger")
        return redirect(url_for("moderator.mail_config"))

    html = render_template("email/test.html", shop=None)
    try:
        send_email([test_to], "GaragePro — test e-mail", html,
                   settings=cfg.smtp_settings())
        flash(f"Test e-mail je poslat na: {test_to}", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Slanje test e-maila nije uspelo: {exc}", "danger")
    return redirect(url_for("moderator.mail_config"))


# ─────────────────────────────── One-click update ─────────────────────────
@moderator_bp.route("/update")
@login_required
@moderator_required
def update():
    """Show current version and a form to update to a GitHub tag."""
    return render_template(
        "moderator/update.html",
        version=current_version(),
        is_git=is_git_repo(),
        service=service_name(),
        tags=list_tags(),
    )


@moderator_bp.route("/update/run", methods=["POST"])
@login_required
@moderator_required
def update_run():
    """Fetch and check out the requested tag, then restart the service."""
    ref = request.form.get("ref", "").strip()
    if not validate_ref(ref):
        flash("Neispravna oznaka. Dozvoljeni su slova, brojevi i znaci . _ - /.",
              "danger")
        return redirect(url_for("moderator.update"))

    try:
        perform_update(ref)
        flash(f"Ažuriranje na „{ref}“ je pokrenuto. Servis se restartuje za "
              f"nekoliko sekundi — osvežite stranicu.", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Ažuriranje nije uspelo: {exc}", "danger")
    return redirect(url_for("moderator.update"))
