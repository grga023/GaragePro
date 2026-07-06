# Entrypoint

* [Dashboard & Setup](main.md) - The main_bp blueprint providing the dashboard with today/month stats and the admin-only company setup page.

# File

* [Authentication & Users](auth.md) - Login, self-registration, user management, role toggling, login throttling, and the admin_required decorator.
* [Backup System](backup.md) - Consistent SQLite snapshot + uploads zip via admin UI, CLI script, and scheduled automatic backups with configurable retention pruning.
* [Car Management](cars.md) - CRUD operations for vehicles: registration by plate, search, photo upload, editing, and detail view with service history.
* [Data Models](models.md) - SQLAlchemy models (User, Company, Car, Service, Part) with relationships and derived pricing/profit properties.
* [Printing & PDF](printing.md) - HTML and PDF print views for services and cars in customer and owner modes, using xhtml2pdf with DejaVu font for Serbian glyphs.
* [Reports & Analytics](reports.md) - Journals (daily/weekly/monthly by worker or shop-wide), profit summaries, Chart.js analytics, and e-mail delivery.
* [Service Records](services.md) - The plate-first service workflow: start by plate, create/edit/delete services with parts and labor, and automatic mileage recompute.
* [Utilities](utils.md) - Helper functions: Serbian currency formatting, Serbian date formatting, image upload with Pillow resizing, allowed extensions check, and period range calculation.
