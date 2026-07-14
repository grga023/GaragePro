"""GaragePro application factory."""
import os
import logging

from flask import Flask, send_from_directory, render_template
from flask_login import login_required, current_user, logout_user
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .config import Config
from .extensions import db, login_manager, csrf
from . import models, utils
from .models import SERVICE_TYPES, SERVICE_TYPE_LABELS


def _asset_version(app):
    """Cache-busting token = mtime of style.css. Stable in prod (until the file
    changes), auto-updates in dev — unlike a random value it lets the browser
    actually cache the stylesheet."""
    try:
        css = os.path.join(app.static_folder, "css", "style.css")
        return int(os.path.getmtime(css))
    except OSError:
        return 0


# Apply pragmatic SQLite settings on every new connection: WAL journaling for
# better concurrency, enforced foreign keys, and a busy timeout so the Pi does
# not throw "database is locked" under light concurrent use.
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _rec):
    try:
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()
    except Exception:  # pragma: no cover - non-SQLite backends
        pass


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Make sure instance + upload + backup directories exist
    os.makedirs(app.config["INSTANCE_DIR"], exist_ok=True)
    os.makedirs(app.config["BACKUP_DIR"], exist_ok=True)
    for sub in ("", "cars", "logo"):
        os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], sub), exist_ok=True)

    # Trust reverse-proxy headers when configured (e.g. behind nginx on the Pi)
    if app.config.get("TRUST_PROXY"):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    # ---- Blueprints -----------------------------------------------------
    from .auth import auth_bp
    from .main import main_bp
    from .cars import cars_bp
    from .services import services_bp
    from .reports import reports_bp
    from .printing import print_bp
    from .backup import backup_bp
    from .moderator.routes import moderator_bp

    for bp in (auth_bp, main_bp, cars_bp, services_bp, reports_bp, print_bp, backup_bp, moderator_bp):
        app.register_blueprint(bp)

    # ---- Serve uploaded media (login required) --------------------------
    @app.route("/media/<path:filename>")
    @login_required
    def media(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # ---- PWA: manifest + service worker (public, no login) --------------
    @app.route("/manifest.webmanifest")
    def web_manifest():
        resp = send_from_directory(app.static_folder, "manifest.webmanifest")
        resp.headers["Content-Type"] = "application/manifest+json"
        return resp

    @app.route("/sw.js")
    def service_worker():
        # Served from root so its scope covers the whole app.
        resp = send_from_directory(os.path.join(app.static_folder, "js"), "sw.js")
        resp.headers["Content-Type"] = "application/javascript"
        resp.headers["Service-Worker-Allowed"] = "/"
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    # ---- Jinja helpers --------------------------------------------------
    app.jinja_env.filters["currency"] = utils.format_currency
    app.jinja_env.filters["srdate"] = utils.sr_date

    @app.context_processor
    def inject_globals():
        company = db.session.get(models.Company, 1)
        return {
            "company": company,
            "FUEL_LABELS": utils.FUEL_LABELS,
            "ROLE_LABELS": utils.ROLE_LABELS,
            "PERIOD_LABELS": utils.PERIOD_LABELS,
            "currency_code": app.config.get("CURRENCY", "RSD"),
            "SERVICE_TYPES": SERVICE_TYPES,
            "SERVICE_TYPE_LABELS": SERVICE_TYPE_LABELS,
            "APP_ENV": app.config.get("APP_ENV", "prod"),
            "ASSET_VERSION": _asset_version(app),
        }

    # ---- Log out users who were deactivated mid-session -----------------
    @app.before_request
    def _reject_deactivated():
        if current_user.is_authenticated and not current_user.active:
            logout_user()

    # ---- Security headers -----------------------------------------------
    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
            "frame-ancestors 'self'",
        )
        return resp

    # ---- Error handlers -------------------------------------------------
    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(_e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def handle_csrf(e):
        return render_template("errors/csrf.html", reason=e.description), 400

    if not app.debug:
        app.logger.setLevel(logging.INFO)

    # Ensure any newly-added tables exist (idempotent; SQLite-friendly, no
    # migration needed for additive model changes such as GlobalMailConfig).
    with app.app_context():
        try:
            db.create_all()
        except Exception as exc:  # noqa: BLE001
            app.logger.warning("db.create_all() nije uspeo pri startu: %s", exc)

    # Optional background scheduler for automatic journals / backups
    if app.config.get("ENABLE_SCHEDULER"):
        from .scheduler import start_scheduler
        start_scheduler(app)

    return app
