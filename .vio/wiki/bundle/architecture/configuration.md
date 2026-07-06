---
type: Architecture
title: Configuration
description: All environment variables and the Config class covering database, uploads,
  SMTP, security settings, scheduler toggle, and deployment options.
tags:
- configuration
- environment
- dotenv
- smtp
- deployment
timestamp: '2026-07-06T17:34:29Z'
---

# Configuration

`app/config.py` defines the `Config` class that loads all settings from environment variables (or a `.env` file via `python-dotenv`). The app factory passes this class to `app.config.from_object()`.

## Settings Reference

### Core

| Setting | Env Var | Default | Purpose |
|---------|---------|---------|---------|
| `SECRET_KEY` | `SECRET_KEY` | `"promeni-me-u-produkciji"` | Flask session signing key (warning logged if default) |
| `SQLALCHEMY_DATABASE_URI` | `DATABASE_URL` | `sqlite:///instance/carservice.db` | Database connection string |

### File Uploads

| Setting | Default | Purpose |
|---------|---------|---------|
| `UPLOAD_FOLDER` | `instance/uploads/` | Root directory for car photos and company logo |
| `MAX_CONTENT_LENGTH` | 8 MB | Maximum upload file size |

Upload subdirectories (`cars/`, `logo/`) are created automatically by `create_app()`.

### Backups

| Setting | Env Var | Default | Purpose |
|---------|---------|---------|---------|
| `BACKUP_DIR` | — | `instance/backups/` | Directory for ZIP backup files |
| `BACKUP_KEEP` | `BACKUP_KEEP` | 14 | Number of backups to retain |

### Locale

| Setting | Env Var | Default | Purpose |
|---------|---------|---------|---------|
| `CURRENCY` | `CURRENCY` | `"RSD"` | Currency code displayed in formatting |

### Security

| Setting | Env Var | Default | Purpose |
|---------|---------|---------|---------|
| `SESSION_COOKIE_HTTPONLY` | — | `True` | Prevent JS access to session cookie |
| `SESSION_COOKIE_SAMESITE` | — | `"Lax"` | SameSite cookie policy |
| `SESSION_COOKIE_SECURE` | `SECURE_COOKIES` | `False` | Set `True` for HTTPS |
| `PERMANENT_SESSION_LIFETIME` | `SESSION_HOURS` | 12h | Session expiry |
| `LOGIN_MAX_ATTEMPTS` | `LOGIN_MAX_ATTEMPTS` | 8 | Failed logins before lockout |
| `LOGIN_LOCKOUT_MINUTES` | `LOGIN_LOCKOUT_MINUTES` | 10 | Lockout duration |
| `TRUST_PROXY` | `TRUST_PROXY` | `False` | Trust X-Forwarded-* headers (nginx on Pi) |

### SMTP (E-mail)

| Setting | Env Var | Default | Purpose |
|---------|---------|---------|---------|
| `SMTP_HOST` | `SMTP_HOST` | `""` | SMTP server hostname |
| `SMTP_PORT` | `SMTP_PORT` | 587 | SMTP port (465 = SSL, 587 = STARTTLS) |
| `SMTP_USER` | `SMTP_USER` | `""` | SMTP login username |
| `SMTP_PASSWORD` | `SMTP_PASSWORD` | `""` | SMTP login password |
| `SMTP_FROM` | `SMTP_FROM` | `"servis@example.com"` | Sender address |
| `SMTP_TLS` | `SMTP_TLS` | `True` | Use STARTTLS |
| `ADMIN_EMAIL` | `ADMIN_EMAIL` | `""` | Admin notification address |

### Scheduler

| Setting | Env Var | Default | Purpose |
|---------|---------|---------|---------|
| `ENABLE_SCHEDULER` | `ENABLE_SCHEDULER` | `False` | Enable APScheduler background jobs |

### SQLite Engine Options

Configured in `SQLALCHEMY_ENGINE_OPTIONS`:
- `connect_args.timeout = 30` — SQLite busy timeout
- `pool_pre_ping = True` — connection health check

Additional SQLite pragmas are set via an engine event listener in `__init__.py`:
- `journal_mode=WAL` — write-ahead logging
- `foreign_keys=ON` — enforce FK constraints
- `busy_timeout=30000` — 30-second wait

## Directory Layout

```
instance/
  carservice.db        SQLite database
  uploads/
    cars/              Car photo uploads
    logo/              Company logo uploads
  backups/             ZIP backup files
```

## Key Connections

- [Application Factory](../modules/app.md) — loads Config, creates directories, applies pragmas
- [Security Architecture](security.md) — session cookie and throttle settings
- [Background Scheduler](scheduler.md) — `ENABLE_SCHEDULER` toggle
- [Backup System](../files/app/backup.md) — `BACKUP_DIR`, `BACKUP_KEEP`
- [Overview](../overview.md)

# Citations

- app/config.py:1-4 (module docstring)
- app/config.py:10-13 (BASE_DIR, INSTANCE_DIR, dotenv loading)
- app/config.py:16-17 (_bool helper for env var parsing)
- app/config.py:20-21 (SECRET_KEY with default warning value)
- app/config.py:23-28 (SQLALCHEMY_DATABASE_URI and engine options)
- app/config.py:36-37 (UPLOAD_FOLDER, MAX_CONTENT_LENGTH)
- app/config.py:40-41 (BACKUP_DIR, BACKUP_KEEP)
- app/config.py:44 (CURRENCY)
- app/config.py:47-55 (session cookie and security settings)
- app/config.py:57-59 (LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_MINUTES, TRUST_PROXY)
- app/config.py:61-68 (SMTP settings)
- app/config.py:71 (ENABLE_SCHEDULER)
- app/__init__.py:18-28 (SQLite pragma listener)
