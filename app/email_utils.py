"""E-mail sending (SMTP) for journals."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app


def send_email(to_addrs, subject: str, html_body: str) -> None:
    cfg = current_app.config
    host = cfg.get("SMTP_HOST")
    if not host:
        raise RuntimeError("SMTP nije konfigurisan (SMTP_HOST je prazan).")

    if isinstance(to_addrs, str):
        to_addrs = [to_addrs]
    to_addrs = [a for a in to_addrs if a]
    if not to_addrs:
        raise RuntimeError("Primalac nema podešenu e-mail adresu.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.get("SMTP_FROM")
    msg["To"] = ", ".join(to_addrs)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    port = int(cfg.get("SMTP_PORT", 587))
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
        if cfg.get("SMTP_TLS"):
            server.starttls()
    try:
        if cfg.get("SMTP_USER"):
            server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        server.sendmail(cfg.get("SMTP_FROM"), to_addrs, msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            pass
