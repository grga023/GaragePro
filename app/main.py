"""Dashboard and first-run company setup."""
import os

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, current_app,
    Response,
)
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from .extensions import db
from .models import Company, Car, Service, Shop, SERVICE_TYPES, SERVICE_TYPE_LABELS
from .security import admin_required, scoped_query
from .utils import save_image, period_range
from .landing_content import LANDING

main_bp = Blueprint("main", __name__)


def _site_url() -> str:
    """Canonical base URL for SEO tags (config override or request host)."""
    configured = current_app.config.get("SITE_URL")
    if configured:
        return configured
    return f"https://{request.host}"


def _render_landing(lang: str):
    from datetime import date
    content = LANDING.get(lang, LANDING["sr"])
    site = _site_url()
    return render_template(
        "landing.html",
        c=content,
        lang=lang,
        site_url=site,
        contact_email=current_app.config.get("CONTACT_EMAIL", ""),
        now_year=date.today().year,
        sent=request.args.get("sent"),
    )


@main_bp.route("/")
def index():
    """Public landing page (Serbian). Logged-in users go straight to the app."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return _render_landing("sr")


@main_bp.route("/en")
def index_en():
    """Public landing page (English)."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return _render_landing("en")


@main_bp.route("/contact", methods=["POST"])
def contact():
    """Handle the landing-page demo request form and e-mail it to CONTACT_EMAIL."""
    from .email_utils import send_email

    lang = request.form.get("lang", "sr")
    back = url_for("main.index_en") if lang == "en" else url_for("main.index")

    # Honeypot: bots fill the hidden 'website' field — pretend success, drop it.
    if request.form.get("website"):
        return redirect(f"{back}?sent=ok#contact")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    shop = request.form.get("shop", "").strip()
    message = request.form.get("message", "").strip()

    if not name or "@" not in email or not message:
        return redirect(f"{back}?sent=err#contact")

    to_addr = current_app.config.get("CONTACT_EMAIL")
    if not to_addr:
        current_app.logger.warning("Kontakt forma: CONTACT_EMAIL nije podešen.")
        return redirect(f"{back}?sent=err#contact")

    html = render_template("email/contact.html", name=name, email=email,
                           phone=phone, shop=shop, message=message)
    try:
        send_email([to_addr], f"GaragePro — upit za demo: {name}", html,
                   reply_to=email)
        return redirect(f"{back}?sent=ok#contact")
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning("Kontakt forma nije poslata: %s", exc)
        return redirect(f"{back}?sent=err#contact")


@main_bp.route("/robots.txt")
def robots_txt():
    body = (
        "User-agent: *\n"
        "Allow: /$\n"
        "Allow: /en\n"
        "Disallow: /dashboard\n"
        "Disallow: /moderator\n"
        "Disallow: /reports\n"
        "Disallow: /services\n"
        "Disallow: /cars\n"
        "Disallow: /auth\n"
        "Disallow: /media\n"
        f"Sitemap: {_site_url()}/sitemap.xml\n"
    )
    return Response(body, mimetype="text/plain")


@main_bp.route("/sitemap.xml")
def sitemap_xml():
    site = _site_url()
    urls = [
        (f"{site}/", "sr", f"{site}/en"),
        (f"{site}/en", "en", f"{site}/"),
    ]
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
             'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for loc, lang, alt in urls:
        other = "en" if lang == "sr" else "sr"
        parts.append("  <url>")
        parts.append(f"    <loc>{loc}</loc>")
        parts.append(f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{loc}"/>')
        parts.append(f'    <xhtml:link rel="alternate" hreflang="{other}" href="{alt}"/>')
        parts.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{site}/"/>')
        parts.append("    <changefreq>weekly</changefreq>")
        parts.append("    <priority>1.0</priority>")
        parts.append("  </url>")
    parts.append("</urlset>")
    return Response("\n".join(parts), mimetype="application/xml")


@main_bp.route("/dashboard")
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
