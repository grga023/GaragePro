"""GaragePro application configuration.

All settings can be overridden through environment variables or a .env file
placed in the project root (see .env.example).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"

load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _load_secret_key() -> str:
    """SECRET_KEY from env, otherwise a persistent random key stored in the
    instance folder. Avoids the shared default key (which made dev/prod session
    cookies interchangeable) while surviving restarts."""
    env = os.environ.get("SECRET_KEY")
    if env:
        return env
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    key_file = INSTANCE_DIR / "secret_key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    import secrets
    key = secrets.token_hex(32)
    key_file.write_text(key, encoding="utf-8")
    try:
        os.chmod(key_file, 0o600)
    except OSError:
        pass
    return key


class Config:
    SECRET_KEY = _load_secret_key()

    # Environment label: "prod" (default) or "dev". Shown as a badge in the UI
    # and lets a dev copy run side by side with prod (separate dir -> separate DB).
    APP_ENV = os.environ.get("APP_ENV", "prod")

    # Database (SQLite by default, ideal for the Pi Zero 2W)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{(INSTANCE_DIR / 'carservice.db').as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Robustness for SQLite under concurrent access (WAL + busy timeout set on connect)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"timeout": 30},
        "pool_pre_ping": True,
    }

    # Uploaded files (car photos, company logo)
    UPLOAD_FOLDER = str(INSTANCE_DIR / "uploads")
    # Max request size. Generous enough to allow restoring a full backup .zip
    # (database + uploaded images) through the admin UI. Override via MAX_UPLOAD_MB.
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "64")) * 1024 * 1024

    # Backups
    BACKUP_DIR = str(INSTANCE_DIR / "backups")
    BACKUP_KEEP = int(os.environ.get("BACKUP_KEEP", "14"))  # how many to retain

    # Locale / display
    CURRENCY = os.environ.get("CURRENCY", "RSD")

    # Internationalisation (Flask-Babel). Serbian is the source/default language;
    # English is offered as an option (per-user, set in the profile).
    BABEL_DEFAULT_LOCALE = "sr"
    BABEL_DEFAULT_TIMEZONE = "Europe/Belgrade"
    LANGUAGES = {"sr": "Srpski", "en": "English"}

    # Public landing page: contact address (shown on the marketing page) and an
    # optional canonical site URL (used for SEO tags / sitemap). When SITE_URL is
    # empty the request host is used, so it also works behind the Cloudflare tunnel.
    CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "kontakt@garagepro.rs")
    SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")

    # ---- Security / hardening ----
    # Set SECURE_COOKIES=true when serving over HTTPS.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SECURE_COOKIES", "false")
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = int(os.environ.get("REMEMBER_DAYS", "30")) * 86400
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = _bool("SECURE_COOKIES", "false")
    WTF_CSRF_TIME_LIMIT = None  # token valid for the whole session
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("SESSION_HOURS", "12")) * 3600
    # Trust X-Forwarded-* headers (enable when behind nginx/reverse proxy on the Pi)
    TRUST_PROXY = _bool("TRUST_PROXY", "false")
    # Login throttling
    LOGIN_THROTTLE = _bool("LOGIN_THROTTLE", "true")  # set false to disable lockout
    LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_MINUTES = int(os.environ.get("LOGIN_LOCKOUT_MINUTES", "15"))

    # E-mail (SMTP) settings for journals
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "servis@example.com")
    SMTP_TLS = _bool("SMTP_TLS", "true")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")

    # Background scheduler for automatic journals (off by default on Windows)
    ENABLE_SCHEDULER = _bool("ENABLE_SCHEDULER", "false")

    INSTANCE_DIR = INSTANCE_DIR
    BASE_DIR = BASE_DIR
