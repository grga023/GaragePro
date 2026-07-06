"""Small helper utilities: money/date formatting, image handling, periods."""
import os
import uuid
from datetime import date, timedelta

from flask import current_app
from werkzeug.utils import secure_filename

try:
    from PIL import Image
    _HAS_PIL = True
except Exception:  # pragma: no cover - Pillow should be installed
    _HAS_PIL = False

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp", "bmp"}

FUEL_LABELS = {
    "benzin": "Benzin",
    "dizel": "Dizel",
    "ev": "Električni",
    "benzin/plin": "Benzin/Plin",
    "hibrid": "Hibrid",
}

ROLE_LABELS = {"moderator": "Moderator", "admin": "Vlasnik servisa", "radnik": "Radnik"}

PERIOD_LABELS = {"day": "Dnevni", "week": "Nedeljni", "month": "Mesečni"}

SR_MONTHS = [
    "", "januar", "februar", "mart", "april", "maj", "jun",
    "jul", "avgust", "septembar", "oktobar", "novembar", "decembar",
]


def format_currency(value) -> str:
    """Format a number the Serbian way: 12.345,67 RSD."""
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0.0
    whole = f"{value:,.2f}"  # 12,345.67
    whole = whole.replace(",", "_").replace(".", ",").replace("_", ".")
    cur = current_app.config.get("CURRENCY", "RSD") if current_app else "RSD"
    return f"{whole} {cur}"


def sr_date(value) -> str:
    """Format a date as '5. jul 2026.'."""
    if not value:
        return ""
    if isinstance(value, str):
        return value
    return f"{value.day}. {SR_MONTHS[value.month]} {value.year}."


def allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXT


def save_image(file_storage, subdir: str, max_dim: int = 1280) -> str:
    """Save an uploaded image (optionally down-scaled) and return its
    path relative to the UPLOAD_FOLDER. Returns '' when nothing uploaded."""
    if not file_storage or not file_storage.filename:
        return ""
    if not allowed_image(file_storage.filename):
        return ""

    upload_root = current_app.config["UPLOAD_FOLDER"]
    target_dir = os.path.join(upload_root, subdir)
    os.makedirs(target_dir, exist_ok=True)

    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    name = f"{uuid.uuid4().hex}.{ext}"
    abs_path = os.path.join(target_dir, name)

    if _HAS_PIL:
        try:
            img = Image.open(file_storage.stream)
            if img.mode in ("RGBA", "P") and ext in ("jpg", "jpeg"):
                img = img.convert("RGB")
            img.thumbnail((max_dim, max_dim))
            img.save(abs_path)
        except Exception:
            file_storage.stream.seek(0)
            file_storage.save(abs_path)
    else:  # pragma: no cover
        file_storage.save(abs_path)

    return f"{subdir}/{name}".replace("\\", "/")


def period_range(period: str, ref: date = None):
    """Return (start_date, end_date) inclusive for 'day' | 'week' | 'month'."""
    ref = ref or date.today()
    if period == "day":
        return ref, ref
    if period == "week":
        start = ref - timedelta(days=ref.weekday())  # Monday
        return start, start + timedelta(days=6)
    if period == "month":
        start = ref.replace(day=1)
        if start.month == 12:
            nxt = start.replace(year=start.year + 1, month=1)
        else:
            nxt = start.replace(month=start.month + 1)
        return start, nxt - timedelta(days=1)
    return ref, ref
