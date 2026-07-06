---
type: File
title: Utilities
description: 'Helper functions: Serbian currency formatting, Serbian date formatting,
  image upload with Pillow resizing, allowed extensions check, and period range calculation.'
tags:
- utilities
- formatting
- images
- pillow
- serbian
timestamp: '2026-07-06T17:33:05Z'
resource: file:///D:/Service/app/utils.py
---

# Utilities

`app/utils.py` provides small helper functions used across the application for formatting, image handling, and date period calculations.

## Functions

### `format_currency(value) → str`

Formats a number in Serbian style: `12.345,67 RSD`. Uses dot as thousands separator and comma as decimal separator. The currency code is taken from `app.config["CURRENCY"]` (default `"RSD"`).

Registered as a Jinja2 filter `currency` in the [Application Factory](../../modules/app.md).

### `sr_date(value) → str`

Formats a date as `"5. jul 2026."` using Serbian month names from `SR_MONTHS`. Registered as the Jinja2 filter `srdate`.

### `allowed_image(filename) → bool`

Checks if a filename has an allowed image extension: `png`, `jpg`, `jpeg`, `gif`, `webp`, `bmp`.

### `save_image(file_storage, subdir, max_dim=1280) → str`

Saves an uploaded image to `UPLOAD_FOLDER/<subdir>/` with a UUID-based filename:

1. Validates the file extension via `allowed_image()`
2. Creates the target directory if needed
3. If Pillow is available, opens the image, converts RGBA/P to RGB for JPEG, and thumbnails to `max_dim` pixels
4. Returns the path relative to `UPLOAD_FOLDER` (e.g., `"cars/abc123.jpg"`)

Used by [Car Management](cars.md) (car photos) and [Dashboard & Setup](main.md) (company logo, `max_dim=600`).

### `period_range(period, ref=None) → (start_date, end_date)`

Returns inclusive date boundaries for `"day"`, `"week"`, or `"month"`:

| Period | Start | End |
|--------|-------|-----|
| `day` | ref | ref |
| `week` | Monday of ref's week | Sunday of ref's week |
| `month` | 1st of ref's month | Last day of ref's month |

Used by [Dashboard & Setup](main.md) (today/month stats) and [Reports & Analytics](reports.md) (journal date ranges).

## Constants

| Constant | Value | Usage |
|----------|-------|-------|
| `ALLOWED_IMAGE_EXT` | `{"png", "jpg", "jpeg", "gif", "webp", "bmp"}` | Image upload validation |
| `FUEL_LABELS` | `{"benzin": "Benzin", ...}` | UI display labels for fuel types |
| `ROLE_LABELS` | `{"admin": "Administrator", "radnik": "Radnik"}` | UI display labels for roles |
| `PERIOD_LABELS` | `{"day": "Dnevni", "week": "Nedeljni", "month": "Mesečni"}` | Journal period labels |
| `SR_MONTHS` | 13-element list of Serbian month names | Date formatting |

## Connections

- Jinja2 filters registered in → [Application Factory](../../modules/app.md)
- Used by → [Dashboard & Setup](main.md), [Car Management](cars.md), [Reports & Analytics](reports.md), [Background Scheduler](../architecture/scheduler.md)
- Image handling powered by Pillow (listed in `requirements.txt`)

# Citations

- app/utils.py:1
- app/utils.py:16
- app/utils.py:27
- app/utils.py:30
- app/utils.py:39
- app/utils.py:50
- app/utils.py:57
- app/utils.py:62
- app/utils.py:93
