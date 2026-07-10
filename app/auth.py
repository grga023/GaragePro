"""Authentication and user management (login, registration, roles)."""
import time
from collections import defaultdict

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, abort,
    current_app,
)
from datetime import timedelta

from flask_login import login_user, logout_user, login_required, current_user

from .extensions import db
from .models import User, ROLE_ADMIN, ROLE_MODERATOR, ROLE_WORKER
from .security import admin_required

auth_bp = Blueprint("auth", __name__)

# Simple in-memory login throttle (per client IP). Waitress runs a single
# process so this is effective for a small shop; it resets on restart.
_login_failures = defaultdict(list)


def _client_key():
    return request.remote_addr or "unknown"


def _seconds_left():
    cfg = current_app.config
    if not cfg.get("LOGIN_THROTTLE", True):
        return 0
    window = cfg["LOGIN_LOCKOUT_MINUTES"] * 60
    now = time.time()
    key = _client_key()
    recent = [t for t in _login_failures[key] if now - t < window]
    _login_failures[key] = recent
    if len(recent) >= cfg["LOGIN_MAX_ATTEMPTS"]:
        return int(window - (now - recent[0]))
    return 0


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        locked = _seconds_left()
        if locked > 0:
            flash(f"Previše neuspešnih pokušaja. Pokušajte ponovo za "
                  f"{locked // 60 + 1} min.", "danger")
            return render_template("auth/login.html")

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.active:
                flash("Nalog je deaktiviran. Obratite se administratoru.", "danger")
                return redirect(url_for("auth.login"))
            _login_failures.pop(_client_key(), None)
            remember = request.form.get("remember") == "on"
            duration = timedelta(days=30) if remember else None
            login_user(user, remember=remember, duration=duration)
            flash(f"Dobrodošli, {user.full_name}!", "success")
            next_url = request.args.get("next")
            if next_url and not next_url.startswith("/"):
                next_url = None  # only allow local redirects
            return redirect(next_url or url_for("main.dashboard"))
        if current_app.config.get("LOGIN_THROTTLE", True):
            _login_failures[_client_key()].append(time.time())
        flash("Pogrešno korisničko ime ili lozinka.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Uspešno ste se odjavili.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Self-registration. The very first account becomes the system moderator;
    all later accounts are workers (radnik) unless promoted."""
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        errors = []
        if not full_name or not username or not email:
            errors.append("Sva polja su obavezna.")
        if len(password) < 8:
            errors.append("Lozinka mora imati najmanje 8 karaktera.")
        if password.isdigit() or password.isalpha():
            errors.append("Lozinka mora sadržati i slova i brojeve.")
        if password != password2:
            errors.append("Lozinke se ne poklapaju.")
        if User.query.filter_by(username=username).first():
            errors.append("Korisničko ime već postoji.")
        if User.query.filter_by(email=email).first():
            errors.append("E-mail adresa je već registrovana.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html",
                                   full_name=full_name, username=username, email=email)

        first_user = User.query.count() == 0
        user = User(
            full_name=full_name,
            username=username,
            email=email,
            role=ROLE_MODERATOR if first_user else ROLE_WORKER,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        role_txt = "moderator" if first_user else "radnik"
        flash(f"Nalog je kreiran ({role_txt}). Možete se prijaviti.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


# ---------------------------------------------------------------------------
# Admin-only user management
# ---------------------------------------------------------------------------
@auth_bp.route("/users")
@login_required
@admin_required
def users():
    q = User.query.order_by(User.created_at)
    if not current_user.is_moderator:
        q = q.filter(User.role != ROLE_MODERATOR)
    return render_template("auth/users.html", users=q.all())


@auth_bp.route("/users/new", methods=["POST"])
@login_required
@admin_required
def create_user():
    full_name = request.form.get("full_name", "").strip()
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", ROLE_WORKER)

    if not (full_name and username and email and len(password) >= 8):
        flash("Neispravni podaci. Lozinka mora imati bar 8 karaktera (slova + brojevi).", "danger")
        return redirect(url_for("auth.users"))
    if User.query.filter((User.username == username) | (User.email == email)).first():
        flash("Korisničko ime ili e-mail već postoji.", "danger")
        return redirect(url_for("auth.users"))

    role_val = ROLE_WORKER
    if role == ROLE_ADMIN:
        role_val = ROLE_ADMIN
    elif role == ROLE_MODERATOR and current_user.is_moderator:
        role_val = ROLE_MODERATOR
    user = User(full_name=full_name, username=username, email=email,
                role=role_val, shop_id=current_user.shop_id)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash("Korisnik je dodat.", "success")
    return redirect(url_for("auth.users"))


@auth_bp.route("/users/<int:user_id>/role", methods=["POST"])
@login_required
@admin_required
def toggle_role(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.role == ROLE_MODERATOR and not current_user.is_moderator:
        flash("Nemate dozvolu da menjate moderatora.", "danger")
        return redirect(url_for("auth.users"))
    if user.role == ROLE_WORKER:
        user.role = ROLE_ADMIN
    elif user.role == ROLE_ADMIN:
        user.role = ROLE_WORKER
    db.session.commit()
    flash(f"Uloga korisnika {user.username} je promenjena.", "success")
    return redirect(url_for("auth.users"))


@auth_bp.route("/users/<int:user_id>/active", methods=["POST"])
@login_required
@admin_required
def toggle_active(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash("Ne možete deaktivirati sopstveni nalog.", "danger")
        return redirect(url_for("auth.users"))
    user.active = not user.active
    db.session.commit()
    flash("Status naloga je promenjen.", "success")
    return redirect(url_for("auth.users"))
