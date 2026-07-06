"""Create a backup from the command line (for cron / systemd timer).

    python backup.py
Creates instance/backups/backup_YYYYmmdd_HHMMSS.zip and prunes old ones.
"""
from app import create_app
from app.backup import create_backup

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        path = create_backup()
        print(f"Rezervna kopija napravljena: {path}")
