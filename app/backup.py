"""Database + uploads backup: consistent SQLite snapshot zipped with media.

Exposed both as a blueprint (admin UI) and as importable functions used by the
CLI (`backup.py`) and the optional scheduler.
"""
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from flask import (
    Blueprint, current_app, render_template, redirect, url_for, flash,
    send_from_directory, request, abort,
)
from flask_login import login_required

from .extensions import db
from .security import moderator_required

backup_bp = Blueprint("backup", __name__)

_NAME_RE = re.compile(r"^backup_\d{8}_\d{6}\.zip$")


def _db_path():
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite:///"):
        return uri[len("sqlite:///"):]
    return None


def _human_size(num):
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def create_backup() -> Path:
    """Create a timestamped zip containing a consistent DB snapshot + uploads."""
    backup_dir = Path(current_app.config["BACKUP_DIR"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    tmp_db = backup_dir / f"_snapshot_{ts}.db"
    db_path = _db_path()
    if db_path and os.path.exists(db_path):
        # sqlite3 online backup API -> consistent even while the app is running
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(str(tmp_db))
        try:
            with dst:
                src.backup(dst)
        finally:
            src.close()
            dst.close()

    zip_path = backup_dir / f"backup_{ts}.zip"
    upload_root = current_app.config["UPLOAD_FOLDER"]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        if tmp_db.exists():
            z.write(tmp_db, arcname="carservice.db")
        if os.path.isdir(upload_root):
            for root, _dirs, files in os.walk(upload_root):
                for f in files:
                    fp = os.path.join(root, f)
                    arc = os.path.join("uploads", os.path.relpath(fp, upload_root))
                    z.write(fp, arcname=arc)

    if tmp_db.exists():
        try:
            tmp_db.unlink()
        except OSError:
            pass

    prune_backups(current_app.config.get("BACKUP_KEEP", 14))
    return zip_path


def prune_backups(keep: int) -> None:
    backup_dir = Path(current_app.config["BACKUP_DIR"])
    backups = sorted(backup_dir.glob("backup_*.zip"),
                     key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[max(keep, 0):]:
        try:
            old.unlink()
        except OSError:
            pass


def list_backups():
    backup_dir = Path(current_app.config["BACKUP_DIR"])
    items = []
    for p in sorted(backup_dir.glob("backup_*.zip"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        st = p.stat()
        items.append({
            "name": p.name,
            "size": _human_size(st.st_size),
            "mtime": datetime.fromtimestamp(st.st_mtime),
        })
    return items


def restore_from_zip(src_zip: Path) -> None:
    """Replace the live database and uploads with the contents of a backup zip.

    A safety backup of the current state is created first so a bad restore can
    still be rolled back.  Extraction is guarded against zip-slip.
    """
    src_zip = Path(src_zip)
    db_path = _db_path()
    if not db_path:
        raise ValueError("Vraćanje je podržano samo za SQLite bazu.")

    with zipfile.ZipFile(src_zip) as z:
        if "carservice.db" not in z.namelist():
            raise ValueError("Neispravna rezervna kopija: nedostaje carservice.db.")

    # Stage the source into a private temp copy first: create_backup() below
    # names files by second, so a source living in the backup dir could
    # otherwise be overwritten by the safety backup before we read it.
    fd, staged = tempfile.mkstemp(prefix="_restore_", suffix=".zip")
    os.close(fd)
    try:
        shutil.copyfile(src_zip, staged)

        # Safety backup of the current data before we overwrite anything.
        try:
            create_backup()
        except Exception:  # noqa: BLE001 — best effort, never block a restore
            pass

        upload_root = os.path.abspath(current_app.config["UPLOAD_FOLDER"])

        # Release SQLite file handles so the DB file can be replaced.
        db.session.remove()
        db.engine.dispose()

        with zipfile.ZipFile(staged) as z:
            # --- database ---
            with z.open("carservice.db") as srcf, open(db_path, "wb") as dstf:
                shutil.copyfileobj(srcf, dstf)
            # Drop stale WAL/SHM sidecars so the restored DB is authoritative.
            for ext in ("-wal", "-shm"):
                side = db_path + ext
                if os.path.exists(side):
                    try:
                        os.remove(side)
                    except OSError:
                        pass

            # --- uploads ---
            if os.path.isdir(upload_root):
                shutil.rmtree(upload_root, ignore_errors=True)
            os.makedirs(upload_root, exist_ok=True)
            for member in z.namelist():
                if not member.startswith("uploads/") or member.endswith("/"):
                    continue
                rel = member[len("uploads/"):]
                dest = os.path.abspath(os.path.join(upload_root, rel))
                # zip-slip guard: stay inside the uploads folder
                if dest != upload_root and not dest.startswith(upload_root + os.sep):
                    continue
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with z.open(member) as srcf, open(dest, "wb") as dstf:
                    shutil.copyfileobj(srcf, dstf)
    finally:
        try:
            os.remove(staged)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Admin UI
# ---------------------------------------------------------------------------
@backup_bp.route("/backup")
@login_required
@moderator_required
def index():
    return render_template("backup.html", backups=list_backups(),
                           keep=current_app.config.get("BACKUP_KEEP", 14))


@backup_bp.route("/backup/create", methods=["POST"])
@login_required
@moderator_required
def create():
    try:
        path = create_backup()
        flash(f"Rezervna kopija je napravljena: {path.name}", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Izrada rezervne kopije nije uspela: {exc}", "danger")
    return redirect(url_for("backup.index"))


@backup_bp.route("/backup/download/<name>")
@login_required
@moderator_required
def download(name):
    if not _NAME_RE.match(name):
        abort(404)
    backup_dir = current_app.config["BACKUP_DIR"]
    if not os.path.exists(os.path.join(backup_dir, name)):
        abort(404)
    return send_from_directory(backup_dir, name, as_attachment=True)


@backup_bp.route("/backup/restore", methods=["POST"])
@login_required
@moderator_required
def restore():
    file = request.files.get("backup")
    if not file or not file.filename:
        flash("Niste izabrali fajl.", "warning")
        return redirect(url_for("backup.index"))
    if not file.filename.lower().endswith(".zip"):
        flash("Rezervna kopija mora biti .zip fajl.", "danger")
        return redirect(url_for("backup.index"))

    backup_dir = Path(current_app.config["BACKUP_DIR"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    tmp = backup_dir / f"_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    try:
        file.save(str(tmp))
        if not zipfile.is_zipfile(tmp):
            raise ValueError("Fajl nije ispravan .zip arhiva.")
        restore_from_zip(tmp)
        flash("Podaci su uspešno vraćeni iz rezervne kopije. "
              "Preporučuje se ponovno pokretanje servisa.", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Vraćanje nije uspelo: {exc}", "danger")
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return redirect(url_for("backup.index"))
