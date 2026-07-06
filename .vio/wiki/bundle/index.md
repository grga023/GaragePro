# Repo

* [Overview](overview.md) - Auto Servis — a Flask + SQLite car-service-shop management application targeting Raspberry Pi and Windows, with Serbian (Latin) UI.

# Subdirectories

* [architecture](architecture/index.md) - Analytics — Chart.js-powered analytics page: time-series revenue/profit, revenue structure doughnut, parts price comparison, and per-worker profit breakdown; Deployment — Production deployment with Waitress (serve.py), Raspberry Pi systemd setup, dev server (run.py), database initialization (init_db.py), and environment configuration; Configuration — All environment variables and the Config class covering database, uploads, SMTP, security settings, scheduler toggle, and deployment options; and 8 more.
* [files](files/index.md) - Verification Tests — Integration test script (_verify2.py) that exercises CSRF, page rendering, PDF generation, backup creation, security headers, dark theme, and mileage recomputation; app — Authentication & Users — Login, self-registration, user management, role toggling, login throttling, and the admin_required decorator; Backup System — Consistent SQLite snapshot + uploads zip via admin UI, CLI script, and scheduled automatic backups with configurable retention pruning; Car Management — CRUD operations for vehicles: registration by plate, search, photo upload, editing, and detail view with service history; and 6 more.
* [modules](modules/index.md) - app — Client-side JavaScript modules: Chart.js analytics charts, dynamic service-form parts table with live price recalculation, and Bootstrap dark/light theme toggle; Application Factory — The create_app() factory in app/__init__.py wires together blueprints, extensions, middleware, error handlers, and the optional scheduler.
