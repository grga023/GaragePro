---
type: File
title: Backup System
description: SQLite online-backup to ZIP archive with uploaded media, admin UI for
  create/download/prune, and automatic nightly scheduling.
tags:
- backup
- sqlite
- zip
- admin
- blueprint
timestamp: '2026-07-06T17:35:41Z'
resource: file:///D:/Service/app/backup.py
---

# Backup System

`app/backup.py` provides both a **blueprint** (admin UI) and **importable functions** for creating consistent database backups. Backups are timestamped ZIP archives containing a SQLite snapshot and all uploaded media.

## How backups work

`create_backup()` performs these steps:

1. **SQLite online backup** — uses Python's `sqlite3.backup()` API to create a consistent snapshot of the live database, even while the app is running and handling requests. The snapshot is written to a temporary `.db` file.
2. **ZIP creation** — the snapshot and the entire `uploads/` directory (car photos, company logo) are compressed into a timestamped archive: `backup_YYYYMMDD_HHMMSS.zip`.
3. **Cleanup** — the temporary snapshot file is removed.
4. **Pruning** — `prune_backups(keep)` retains only the N most recent backups (default 14, configurable via `BACKUP_KEEP`), deleting older ones.

## Admin UI endpoints

| Route | Method | Function | Description |
|-------|--------|----------|-------------|
| `/backup` | GET | `index()` | List existing backups with sizes and timestamps |
| `/backup/create` | POST | `create()` | Trigger a new backup |
| `/backup/download/<name>` | GET | `download(name)` | Download a backup ZIP |

All routes are protected by `@login_required` and `@admin_required`.

### Download security

The `download()` route validates the filename against a regex (`backup_\\d{8}_\\d{6}\\.zip`) to prevent path traversal attacks — arbitrary filenames are rejected with 404.

## Importable functions

These functions are also used by the [Scheduler](../architecture/scheduler.md) for automatic nightly backups and could be called from a CLI script:

| Function | Purpose |
|----------|---------|
| `create_backup()` | Full backup → returns `Path` to ZIP |
| `prune_backups(keep)` | Delete oldest backups beyond `keep` count |
| `list_backups()` | Return list of backup metadata (name, size, mtime) |

## ZIP contents

```
backup_20260706_023000.zip
├── carservice.db          ← consistent SQLite snapshot
└── uploads/
    ├── cars/
    │   └── abc123.jpg     ← car photos
    └── logo/
        └── def456.png     ← company logo
```

## Connections

- Protected by `admin_required` from [Authentication & Users](auth.md)
- Automatic backups via [Scheduler](../architecture/scheduler.md) (`_do_backup`)
- Backup retention configured in [Configuration](../architecture/configuration.md) (`BACKUP_KEEP`)
- Database path derived from [Configuration](../architecture/configuration.md) (`SQLALCHEMY_DATABASE_URI`)

# Citations
- app/backup.py:1
- app/backup.py:23
- app/backup.py:43
- app/backup.py:83
- app/backup.py:92
- app/backup.py:108
- app/backup.py:115
- app/backup.py:125
- app/backup.py:133
