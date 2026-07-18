"""Optional background scheduler that e-mails journals automatically.

Enabled only when ENABLE_SCHEDULER=true. On the Pi you can instead rely on a
systemd timer / cron calling the /reports/send endpoint, but this keeps
everything self-contained.
"""
from datetime import date

from flask import render_template

from .utils import sr_date


_SR_WEEKDAYS = ["ponedeljak", "utorak", "sreda", "četvrtak", "petak", "subota", "nedelja"]


def _sr_day_label(d):
    """e.g. 'petak, 19. jul 2026.'"""
    return f"{_SR_WEEKDAYS[d.weekday()]}, {sr_date(d)}"


def _automation_enabled(app) -> bool:
    """Whether the moderator has switched on automatic tasks (in-app flag)."""
    from .models import GlobalMailConfig
    try:
        cfg = GlobalMailConfig.get()
        return bool(cfg and cfg.scheduler_enabled)
    except Exception:  # noqa: BLE001
        return False


def _dispatch(app, period):
    """Send the given period's shop journal to every shop that has enabled it.

    Each shop uses its own SMTP settings and recipient list (falling back to the
    shop owner's e-mail when no recipients are configured).
    """
    from .reports import compose_journal
    from .models import EmailConfig, User, GlobalMailConfig, ROLE_ADMIN
    from .email_utils import send_email, sender_address
    from .extensions import db

    ref = date.today()
    with app.app_context():
        if not _automation_enabled(app):
            return
        gcfg = db.session.get(GlobalMailConfig, 1)
        global_recipients = gcfg.recipient_list() if gcfg else []
        sender = sender_address()
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

            journal = compose_journal(period, ref, worker=None, shop_id=shop.id,
                                      scope_label=f"Servis: {shop.name}")
            if journal["totals"]["count"] == 0:
                continue

            # Sender in To, everyone else in BCC (recipients see only the sender).
            all_recipients = sorted(set(r for r in (recipients + global_recipients) if r))
            if sender:
                to_addr, bcc = [sender], all_recipients
            else:
                to_addr, bcc = all_recipients, None
            if not to_addr:
                app.logger.warning("Servis %s: nema primalaca za žurnal.", shop.name)
                continue

            subject = (f"{journal['period_label']} žurnal — {shop.name} "
                       f"({sr_date(journal['start'])} - {sr_date(journal['end'])})")
            html = render_template("email/journal.html", journal=journal)
            try:
                send_email(to_addr, subject, html, bcc=bcc)
                app.logger.info("Žurnal (%s) poslat za servis %s.", period, shop.name)
            except Exception as exc:  # noqa: BLE001
                app.logger.warning("Žurnal za servis %s nije poslat: %s", shop.name, exc)


def _dispatch_agenda(app):
    """E-mail each worker/owner their appointments for TOMORROW.

    Workers get only their own appointments; owners (admins) get the whole
    shop's schedule.  A user with no appointments tomorrow gets no e-mail, and
    a shop with no appointments at all is skipped entirely.  Uses the single
    global SMTP mailbox.
    """
    from datetime import timedelta, datetime, time as dtime

    from .extensions import db
    from .models import (
        Shop, User, Appointment, Company, ROLE_ADMIN, ROLE_MODERATOR,
        APPOINTMENT_CANCELLED, service_type_map,
    )
    from .email_utils import send_email, global_settings

    with app.app_context():
        if not _automation_enabled(app):
            return
        settings = global_settings()
        if not settings.get("host"):
            app.logger.info("Podsetnik (sutra): globalni SMTP nije podešen — preskačem.")
            return

        company = db.session.get(Company, 1)
        tomorrow = date.today() + timedelta(days=1)
        start = datetime.combine(tomorrow, dtime.min)
        end = datetime.combine(tomorrow, dtime.max)
        day_label = _sr_day_label(tomorrow)

        for shop in Shop.query.filter_by(is_active=True).all():
            appts = (Appointment.query
                     .filter(Appointment.shop_id == shop.id,
                             Appointment.status != APPOINTMENT_CANCELLED,
                             Appointment.start_at >= start,
                             Appointment.start_at <= end)
                     .order_by(Appointment.start_at).all())
            if not appts:
                continue

            tmap = service_type_map(shop.id)

            def _items(subset):
                rows = []
                for a in subset:
                    st = tmap.get(a.service_type)
                    rows.append({
                        "time": f"{a.start_at:%H:%M}\u2013{a.end_at:%H:%M}",
                        "plate": a.car.plate if a.car else "",
                        "car_desc": a.car.description if a.car else "",
                        "owner": a.car.owner_name if a.car else "",
                        "phone": (a.car.phone if a.car else "") or "",
                        "worker": a.worker.full_name if a.worker else "",
                        "stype_label": st.label if st else a.service_type,
                        "color": st.color if st else "#6c757d",
                        "note": a.note or "",
                    })
                return rows

            members = (User.query
                       .filter(User.shop_id == shop.id, User.active.is_(True),
                               User.role != ROLE_MODERATOR,
                               User.email.isnot(None), User.email != "")
                       .all())
            for user in members:
                if user.role == ROLE_ADMIN:
                    subset, show_worker = appts, True   # owner: whole shop
                else:
                    subset = [a for a in appts if a.worker_id == user.id]
                    show_worker = False
                if not subset:
                    continue

                html = render_template(
                    "email/agenda.html",
                    items=_items(subset),
                    user_name=user.full_name,
                    day_label=day_label,
                    show_worker=show_worker,
                    company=company,
                )
                subject = f"Raspored za sutra — {shop.name} ({day_label})"
                try:
                    send_email([user.email], subject, html, settings=settings)
                    app.logger.info("Podsetnik za sutra poslat: %s (%s).",
                                    user.email, shop.name)
                except Exception as exc:  # noqa: BLE001
                    app.logger.warning("Podsetnik nije poslat za %s: %s",
                                       user.email, exc)


def start_scheduler(app):
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(timezone="Europe/Belgrade")
    scheduler.add_job(lambda: _dispatch(app, "day"),
                      "cron", hour=20, minute=0, id="daily")
    scheduler.add_job(lambda: _dispatch(app, "week"),
                      "cron", day_of_week="sun", hour=20, minute=5, id="weekly")
    scheduler.add_job(lambda: _dispatch(app, "month"),
                      "cron", day="last", hour=20, minute=10, id="monthly")
    scheduler.add_job(lambda: _dispatch_agenda(app),
                      "cron", hour=21, minute=0, id="agenda")
    scheduler.add_job(lambda: _do_backup(app),
                      "cron", hour=2, minute=30, id="backup")
    scheduler.start()
    app.logger.info("Scheduler aktivan (žurnali + podsetnik 21h + rezervna kopija); "
                    "rad je uslovljen moderator prekidačem.")
    return scheduler


def _do_backup(app):
    from .backup import create_backup
    with app.app_context():
        if not _automation_enabled(app):
            return
        try:
            path = create_backup()
            app.logger.info("Automatska rezervna kopija: %s", path)
        except Exception as exc:  # noqa: BLE001
            app.logger.warning("Automatska rezervna kopija nije uspela: %s", exc)
