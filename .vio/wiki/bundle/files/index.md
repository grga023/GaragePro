# File

* [Verification Tests](_verify2.md) - Integration test script (_verify2.py) that exercises CSRF, page rendering, PDF generation, backup creation, security headers, dark theme, and mileage recomputation.

# Subdirectories

* [app](app/index.md) - Authentication & Users — Login, self-registration, user management, role toggling, login throttling, and the admin_required decorator; Backup System — Consistent SQLite snapshot + uploads zip via admin UI, CLI script, and scheduled automatic backups with configurable retention pruning; Car Management — CRUD operations for vehicles: registration by plate, search, photo upload, editing, and detail view with service history; and 6 more.
