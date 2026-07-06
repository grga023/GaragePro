"""Optional background scheduler that e-mails journals automatically.

Enabled only when ENABLE_SCHEDULER=true. On the Pi you can instead rely on a
systemd timer / cron calling the /reports/send endpoint, but this keeps
everything self-contained.
"""
from datetime import date

from flask import render_template

from .utils import sr_date


def _dispatch(app, period, ref):
    from .reports import compose_journal
    from .models import User, ROLE_ADMIN
    from .email_utils import send_email

    with app.app_context():
        # Per-worker journals -> each worker's own e-mail
        for worker in User.query.filter_by(active=True).all():
            if not worker.email:
                continue
            journal = compose_journal(period, ref, worker=worker)
            if journal["totals"]["count"] == 0:
                continue
            subject = (f"{journal['period_label']} žurnal — {worker.full_name} "
                       f"({sr_date(journal['start'])} - {sr_date(journal['end'])})")
            html = render_template("email/journal.html", journal=journal)
            try:
                send_email(worker.email, subject, html)
            except Exception as exc:  # noqa: BLE001
                app.logger.warning("Žurnal za %s nije poslat: %s", worker.username, exc)

        # Overall journal -> admins only
        admins = User.query.filter_by(role=ROLE_ADMIN, active=True).all()
        recipients = [a.email for a in admins if a.email]
        if recipients:
            journal = compose_journal(period, ref, worker=None)
            subject = (f"{journal['period_label']} žurnal — ceo servis "
                       f"({sr_date(journal['start'])} - {sr_date(journal['end'])})")
            html = render_template("email/journal.html", journal=journal)
            try:
                send_email(recipients, subject, html)
            except Exception as exc:  # noqa: BLE001
                app.logger.warning("Zbirni žurnal nije poslat: %s", exc)


def start_scheduler(app):
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(timezone="Europe/Belgrade")
    scheduler.add_job(lambda: _dispatch(app, "day", date.today()),
                      "cron", hour=20, minute=0, id="daily")
    scheduler.add_job(lambda: _dispatch(app, "week", date.today()),
                      "cron", day_of_week="sun", hour=20, minute=5, id="weekly")
    scheduler.add_job(lambda: _dispatch(app, "month", date.today()),
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
