---
type: File
title: Verification Tests
description: Integration test script (_verify2.py) that exercises CSRF, page rendering,
  PDF generation, backup creation, security headers, dark theme, and mileage recomputation.
tags:
- testing
- integration-tests
- verification
- csrf
- pdf
timestamp: '2026-07-06T17:34:56Z'
resource: file:///D:/Service/_verify2.py
---

# Verification Tests

`_verify2.py` is a standalone integration test script that exercises the application end-to-end using Flask's test client. It validates CSRF protection, page rendering, PDF generation, backup operations, security headers, and data integrity.

## How It Works

The script creates the app via `create_app()`, obtains a test client, and runs a series of `check(label, condition)` assertions. Each check prints `PASS` or `FAIL`. The final line reports `ALL PASS` or `SOME FAILED`.

A helper `token(path)` extracts the CSRF token from a page's HTML by regex-matching the `csrf_token` hidden input.

## Test Categories

### CSRF Protection
- Verifies the login page exposes a CSRF token
- Confirms POST without token returns 400
- Confirms POST with valid token succeeds and logs in

### Page Rendering
Tests that all major pages return HTTP 200:
- `/` (dashboard), `/services`, `/cars`, `/car/1`, `/service/1`
- `/reports`, `/analytics`, `/users`, `/setup`, `/backup`

### Analytics Charts
Verifies the analytics page embeds:
- `id="chartData"` — the JSON data block
- `chart.umd.min.js` — Chart.js library
- `analytics.js` — custom chart renderer

### Dark Theme
Checks the dashboard includes:
- `id="themeToggle"` button
- `theme.js` script
- `data-bs-theme` attribute on `<html>`

### Security Headers
Validates `X-Content-Type-Options: nosniff` and `Content-Security-Policy` presence.

### Logo Upload
Generates a synthetic PNG via Pillow, uploads it through `/setup`, and validates the flow.

### PDF Export
Tests four PDF endpoints with both customer and owner modes:
- `/pdf/service/1?mode=customer` and `?mode=owner`
- `/pdf/car/1?mode=customer` and `?mode=owner`

Verifies: status 200, `application/pdf` mimetype, valid `%PDF` header, and DejaVu font embedding (for Serbian glyphs).

### Backup Operations
- Creates a backup via POST to `/backup/create`
- Lists backups and finds the new file
- Downloads the backup ZIP
- Verifies ZIP contains `carservice.db` and `uploads/` entries
- Tests path traversal rejection (bad filename returns 400/404)

### Service Creation & Mileage
- Creates a service with CSRF token, setting mileage to 150000
- Verifies the car's detail page shows the updated mileage

## Key Connections

- [Security Architecture](../architecture/security.md) — CSRF and headers tested here
- [Printing & PDF Export](../files/app/printing.md) — PDF generation tested
- [Backup System](../files/app/backup.md) — backup create/download/traversal tested
- [Service Records](../files/app/services.md) — service creation and mileage tested
- [Frontend Assets](../modules/app/static/js.md) — analytics and theme assets verified
- [Overview](../overview.md)

# Citations

- _verify2.py:1-3 (imports and app creation)
- _verify2.py:5-6 (test client creation)
- _verify2.py:8-10 (check helper function)
- _verify2.py:12-16 (token extraction helper)
- _verify2.py:18-26 (CSRF tests — without/with token)
- _verify2.py:28-31 (page rendering tests for all major routes)
- _verify2.py:33-36 (analytics chart data verification)
- _verify2.py:38-40 (dark theme toggle verification)
- _verify2.py:42-44 (security headers check)
- _verify2.py:46-54 (logo upload via Pillow-generated PNG)
- _verify2.py:56-63 (PDF export tests with %PDF header and DejaVu check)
- _verify2.py:66-80 (backup create/list/download/ZIP contents/path traversal)
- _verify2.py:82-87 (service creation with CSRF and mileage recompute)
