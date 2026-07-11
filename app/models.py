"""Database models for the car-service application."""
from datetime import datetime, date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db

ROLE_MODERATOR = "moderator"
ROLE_ADMIN = "admin"
ROLE_WORKER = "radnik"

FUEL_TYPES = ["benzin", "dizel", "ev", "benzin/plin", "hibrid"]

SERVICE_TYPE_POPRAVKE = "popravke"
SERVICE_TYPE_VULKANIZERSKI = "vulkanizerski"
SERVICE_TYPE_MALI_SERVIS = "mali_servis"

SERVICE_TYPES = [
    (SERVICE_TYPE_POPRAVKE, "Popravke"),
    (SERVICE_TYPE_VULKANIZERSKI, "Vulkanizerski radovi"),
    (SERVICE_TYPE_MALI_SERVIS, "Mali servis"),
]

SERVICE_TYPE_LABELS = {k: v for k, v in SERVICE_TYPES}


class Shop(db.Model):
    """A service shop / tenant.  Moderators create these; each admin 'owns' one."""

    __tablename__ = "shops"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    address = db.Column(db.String(255))
    contact = db.Column(db.String(160))
    logo_path = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship("User", backref="shop", lazy=True)
    cars = db.relationship("Car", backref="shop", lazy=True)


class EmailConfig(db.Model):
    """Per-shop e-mail (SMTP) settings and automatic report schedule.

    Managed by system moderators — each service (shop) has its own mailbox and
    decides which journals (daily / weekly / monthly) are e-mailed automatically
    and to whom.  Kept as a separate 1:1 table (not columns on Shop) so that
    ``db.create_all()`` adds it to existing databases without a migration.

    Note: the SMTP password is stored as-is (plain text) in the local SQLite
    database, consistent with the app's existing ``.env`` based SMTP_PASSWORD.
    """

    __tablename__ = "email_configs"

    SECURITY_CHOICES = ("none", "starttls", "ssl")

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"),
                        unique=True, nullable=False, index=True)

    # ---- SMTP connection ----
    smtp_host = db.Column(db.String(255))
    smtp_port = db.Column(db.Integer, default=587)
    smtp_security = db.Column(db.String(10), default="starttls")  # none|starttls|ssl
    smtp_user = db.Column(db.String(255))
    smtp_password = db.Column(db.String(255))
    from_addr = db.Column(db.String(255))

    # ---- Automatic report schedule ----
    enabled = db.Column(db.Boolean, default=True)       # master on/off switch
    send_daily = db.Column(db.Boolean, default=False)
    send_weekly = db.Column(db.Boolean, default=False)
    send_monthly = db.Column(db.Boolean, default=False)
    recipients = db.Column(db.Text)  # comma / newline / semicolon separated

    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    shop = db.relationship(
        "Shop", backref=db.backref("email_config", uselist=False,
                                   cascade="all, delete-orphan"))

    @property
    def is_configured(self) -> bool:
        """True when at least an SMTP host is set."""
        return bool(self.smtp_host)

    def recipient_list(self) -> list:
        """Parsed, de-duplicated list of recipient e-mail addresses."""
        raw = (self.recipients or "").replace("\n", ",").replace(";", ",")
        seen, out = set(), []
        for addr in (a.strip() for a in raw.split(",")):
            if addr and addr.lower() not in seen:
                seen.add(addr.lower())
                out.append(addr)
        return out

    def wants(self, period: str) -> bool:
        """Whether this shop auto-sends the given period ('day'/'week'/'month')."""
        return {
            "day": self.send_daily,
            "week": self.send_weekly,
            "month": self.send_monthly,
        }.get(period, False)

    def smtp_settings(self) -> dict:
        """Settings dict consumed by ``email_utils.send_email``."""
        return {
            "host": self.smtp_host,
            "port": self.smtp_port or 587,
            "security": self.smtp_security or "starttls",
            "user": self.smtp_user,
            "password": self.smtp_password,
            "from_addr": self.from_addr or self.smtp_user,
        }


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_WORKER)
    active = db.Column(db.Boolean, default=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    services = db.relationship("Service", backref="worker", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_moderator(self) -> bool:
        return self.role == ROLE_MODERATOR

    @property
    def is_admin(self) -> bool:
        return self.role in (ROLE_ADMIN, ROLE_MODERATOR)

    @property
    def is_owner(self) -> bool:
        return self.role == ROLE_ADMIN

    # Flask-Login uses this; map to our `active` column
    @property
    def is_active(self) -> bool:  # noqa: D401
        return bool(self.active)


class Company(db.Model):
    """Single-row table with the shop's identity (set up on first run)."""

    __tablename__ = "company"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160))
    address = db.Column(db.String(255))
    contact = db.Column(db.String(160))
    logo_path = db.Column(db.String(255))  # relative to UPLOAD_FOLDER


class Car(db.Model):
    __tablename__ = "cars"

    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(20), unique=True, nullable=False, index=True)
    owner_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40))
    brand = db.Column(db.String(60))
    model = db.Column(db.String(60))
    engine = db.Column(db.String(60))          # e.g. "2.0"
    fuel_type = db.Column(db.String(20))       # benzin / dizel / ev ...
    year = db.Column(db.Integer)
    photo_path = db.Column(db.String(255))     # relative to UPLOAD_FOLDER
    mileage = db.Column(db.Integer)            # last recorded mileage
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    services = db.relationship(
        "Service",
        backref="car",
        lazy=True,
        order_by="Service.date.desc(), Service.id.desc()",
        cascade="all, delete-orphan",
    )

    @property
    def description(self) -> str:
        """Human readable car summary, e.g. 'BMW 320 2.0 dizel 2020'."""
        parts = [self.brand, self.model, self.engine, self.fuel_type,
                 str(self.year) if self.year else None]
        return " ".join(p for p in parts if p)


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey("cars.id"), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=True)
    date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    service_type = db.Column(db.String(30), nullable=False, default=SERVICE_TYPE_POPRAVKE, index=True)
    mileage = db.Column(db.Integer)
    labor_price = db.Column(db.Float, default=0.0)
    labor_description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parts = db.relationship(
        "Part", backref="service", lazy=True, cascade="all, delete-orphan"
    )

    # ---- Derived price fields -------------------------------------------
    @property
    def parts_total_full(self) -> float:
        """Sum of parts at full (non-discount) price — what the customer pays."""
        return sum(p.line_full for p in self.parts)

    @property
    def parts_total_cost(self) -> float:
        """Sum of parts at discounted price — the shop's cost."""
        return sum(p.line_cost for p in self.parts)

    @property
    def parts_profit(self) -> float:
        return self.parts_total_full - self.parts_total_cost

    @property
    def total_full(self) -> float:
        """Full service price: labor + parts (full price)."""
        return (self.labor_price or 0.0) + self.parts_total_full

    @property
    def total_profit(self) -> float:
        """Profit = labor + (parts full - parts discounted)."""
        return (self.labor_price or 0.0) + self.parts_profit


class Part(db.Model):
    __tablename__ = "parts"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    price = db.Column(db.Float, default=0.0)               # full / retail price
    price_with_discount = db.Column(db.Float, default=0.0)  # shop cost
    quantity = db.Column(db.Float, default=1.0)

    @property
    def line_full(self) -> float:
        return (self.price or 0.0) * (self.quantity or 1.0)

    @property
    def line_cost(self) -> float:
        return (self.price_with_discount or 0.0) * (self.quantity or 1.0)

    @property
    def line_profit(self) -> float:
        return self.line_full - self.line_cost
