"""E-mail sending (SMTP) for journals.

``send_email`` accepts an optional ``settings`` dict so each shop can send from
its own mailbox (see models.EmailConfig.smtp_settings).  When ``settings`` is
omitted it falls back to the global ``.env`` / app config SMTP values.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app


def global_settings() -> dict:
    """SMTP settings for the single, system-wide mailbox.

    Prefers the moderator-managed global mailbox stored in the database
    (``GlobalMailConfig``); falls back to the ``.env`` / app-config SMTP values
    when it has not been configured yet.
    """
    try:
        from .extensions import db
        from .models import GlobalMailConfig
        row = db.session.get(GlobalMailConfig, 1)
        if row and row.is_configured:
            return row.smtp_settings()
    except Exception:  # noqa: BLE001 - DB may be unavailable during setup
        pass

    cfg = current_app.config
    port = int(cfg.get("SMTP_PORT", 587) or 587)
    if port == 465:
        security = "ssl"
    elif cfg.get("SMTP_TLS"):
        security = "starttls"
    else:
        security = "none"
    return {
        "host": cfg.get("SMTP_HOST"),
        "port": port,
        "security": security,
        "user": cfg.get("SMTP_USER"),
        "password": cfg.get("SMTP_PASSWORD"),
        "from_addr": cfg.get("SMTP_FROM"),
    }


def send_email(to_addrs, subject: str, html_body: str, settings: dict = None,
               bcc=None) -> None:
    s = settings or global_settings()
    host = s.get("host")
    if not host:
        raise RuntimeError("SMTP nije konfigurisan (SMTP_HOST je prazan).")

    if isinstance(to_addrs, str):
        to_addrs = [to_addrs]
    to_addrs = [a for a in (to_addrs or []) if a]
    if isinstance(bcc, str):
        bcc = [bcc]
    # BCC recipients: kept out of the headers, only in the SMTP envelope, so
    # recipients cannot see each other — they see only the sender/To.
    to_lower = {a.lower() for a in to_addrs}
    bcc = [a for a in (bcc or []) if a and a.lower() not in to_lower]
    # De-duplicate BCC case-insensitively.
    seen = set()
    bcc = [a for a in bcc if not (a.lower() in seen or seen.add(a.lower()))]

    envelope = to_addrs + bcc
    if not envelope:
        raise RuntimeError("Primalac nema podešenu e-mail adresu.")

    from_addr = s.get("from_addr") or s.get("user") or host
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs) if to_addrs else from_addr
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    port = int(s.get("port") or 587)
    security = (s.get("security") or "").lower()
    if security == "ssl" or port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
        if security == "starttls":
            server.starttls()
    try:
        if s.get("user"):
            server.login(s["user"], s.get("password") or "")
        server.sendmail(from_addr, envelope, msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            pass


def sender_address(settings: dict = None) -> str:
    """The 'From' / sender address used for reports (the global mailbox)."""
    s = settings or global_settings()
    return s.get("from_addr") or s.get("user") or ""
