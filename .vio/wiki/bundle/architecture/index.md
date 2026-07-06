# Architecture

* [Analytics](analytics.md) - Chart.js-powered analytics page: time-series revenue/profit, revenue structure doughnut, parts price comparison, and per-worker profit breakdown.
* [Background Scheduler](scheduler.md) - APScheduler integration for automatic daily/weekly/monthly journal e-mailing and nightly database backups.
* [Configuration](configuration.md) - All environment variables and the Config class covering database, uploads, SMTP, security settings, scheduler toggle, and deployment options.
* [Deployment](build-and-deploy.md) - Production deployment with Waitress (serve.py), Raspberry Pi systemd setup, dev server (run.py), database initialization (init_db.py), and environment configuration.
* [Deployment](deployment.md) - Production deployment on Raspberry Pi Zero 2W (systemd + Waitress), Windows quick start, database initialization with init_db.py, and .env configuration.
* [Plate-First Service Flow](plate-first-flow.md) - End-to-end user journey from entering a license plate number through optional car registration to creating a service record with parts and labor.
* [Pricing & Profit Model](pricing-model.md) - The dual-price system with retail and discounted part prices, per-service profit calculation, and how journals and analytics aggregate financial data.
* [Pricing & Profit Model](pricing.md) - End-to-end pricing: how retail/discounted part prices, labor, and profit are calculated across Part, Service, reports, journals, and print copies.
* [Scheduler & Email](scheduler-email.md) - APScheduler background jobs for automatic journal delivery and nightly backups, plus the SMTP email sending utility.
* [Security Architecture](security.md) - Cross-cutting security: CSRF via Flask-WTF, IP-based login throttling, admin_required decorator, security response headers, session hardening, and deactivated-user ejection.

# Data Flow

* [Data Flow](data-flow.md) - End-to-end data flow from browser through Flask blueprints to SQLite: the plate-first service workflow, journal generation, and print/PDF pipeline.
