"""Optional background scheduler that e-mails journals automatically.

Enabled only when ENABLE_SCHEDULER=true. On the Pi you can instead rely on a
systemd timer / cron calling the /reports/send endpoint, but this keeps
everything self-contained.
"""
from datetime import date

from flask import render_template

from .utils import sr_date


def _dispatch(app, period):
    """Send the given period's shop journal to every shop that has enabled it.

    Each shop uses its own SMTP settings and recipient list (falling back to the
    shop owner's e-mail when no recipients are configured).
    """
    from .reports import compose_journal
    from .models import EmailConfig, User, ROLE_ADMIN
    from .email_utils import send_email

    ref = date.today()
    with app.app_context():
        configs = EmailConfig.query.filter_by(enabled=True).all()
        for ec in configs:
            if not ec.wants(period) or not ec.is_configured:
                continue
            shop = ec.shop
            if not shop or not shop.is_active:
                continue

            recipients = ec.recipient_list()
            if not recipients:
                owners = User.query.filter_by(
                    shop_id=shop.id, role=ROLE_ADMIN, active=True).all()
                recipients = [o.email for o in owners if o.email]
            if not recipients:
                app.logger.warning("Servis %s: nema primalaca za žurnal.", shop.name)
                continue

            journal = compose_journal(period, ref, worker=None, shop_id=shop.id,
                                      scope_label=f"Servis: {shop.name}")
            if journal["totals"]["count"] == 0:
                continue

            subject = (f"{journal['period_label']} žurnal — {shop.name} "
                       f"({sr_date(journal['start'])} - {sr_date(journal['end'])})")
            html = render_template("email/journal.html", journal=journal)
            try:
                send_email(recipients, subject, html, settings=ec.smtp_settings())
                app.logger.info("Žurnal (%s) poslat za servis %s.", period, shop.name)
            except Exception as exc:  # noqa: BLE001
                app.logger.warning("Žurnal za servis %s nije poslat: %s", shop.name, exc)


def start_scheduler(app):
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(timezone="Europe/Belgrade")
    scheduler.add_job(lambda: _dispatch(app, "day"),
                      "cron", hour=20, minute=0, id="daily")
    scheduler.add_job(lambda: _dispatch(app, "week"),
                      "cron", day_of_week="sun", hour=20, minute=5, id="weekly")
    scheduler.add_job(lambda: _dispatch(app, "month"),
                      "cron", day="last", hour=20, minute=10, id="monthly")
    scheduler.add_job(lambda: _do_backup(app),
                      "cron", hour=2, minute=30, id="backup")
    scheduler.start()
    app.logger.info("Scheduler pokrenut: žurnali (dnevni/nedeljni/mesečni) + dnevna rezervna kopija.")
    return scheduler


def _do_backup(app):
    from .backup import create_backup
    with app.app_context():
        try:
            path = create_backup()
            app.logger.info("Automatska rezervna kopija: %s", path)
        except Exception as exc:  # noqa: BLE001
            app.logger.warning("Automatska rezervna kopija nije uspela: %s", exc)
