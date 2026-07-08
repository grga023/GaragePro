---
type: Entrypoint
title: Dashboard & Setup
description: The main_bp blueprint providing the dashboard with today/month stats
  and the admin-only company setup page.
tags:
- dashboard
- setup
- blueprint
- entrypoint
- statistics
timestamp: '2026-07-06T17:33:43Z'
resource: file:///D:/Service/app/main.py
---

# Dashboard & Setup

`app/main.py` defines the `main_bp` blueprint with two routes: the **dashboard** (landing page after login) and the **company setup** page (admin-only, used on first run and to update shop identity). Moderators are redirected to the [Moderator Panel](../../architecture/moderator.md) dashboard.

## Dashboard (`/`)

The dashboard is the default route and requires login. It calculates and displays:

| Stat | Scope |
|------|-------|
| Today's service count | Worker's own (or all if admin) |
| Today's revenue | Sum of `total_full` |
| Month's service count | Current calendar month |
| Month's revenue | Sum of `total_full` |
| Month's profit | Sum of `total_profit` |
| Total cars registered | All cars (admin) or distinct cars served (worker) |

It also shows:
- The **10 most recent services** ordered by date descending.
- **Service type breakdown** for the current month (revenue/profit per type: popravke, vulkanizerski, mali servis).
- **Smart alerts**: warnings when no services today, no services this week (mid-week), and average daily stats.

Workers see only their own services; admins see everything within their shop — enforced via `scoped_query()` and filtering on `Service.worker_id`.

## Company setup (`/setup`)

Admin-only (protected by `@admin_required`). Moderators are redirected to the moderator panel. Manages both the legacy `Company` record and the user's `Shop` record:
- **Name**, **address**, **contact** — text fields (synced to both Company and Shop).
- **Logo** — uploaded image, resized to max 600px via `save_image()`. Old logo files are removed on replacement. Logo path is also synced to the Shop.

On the very first visit, if no Company row exists, one is auto-created with `id=1`.

## Key symbols

| Symbol | Role |
|--------|------|
| `main_bp` | Flask Blueprint instance |
| `dashboard()` | GET `/` — stats + recent services |
| `setup()` | GET/POST `/setup` — company identity form |

## Connections

- Queries [Data Models](models.md) — `Company`, `Car`, `Service`, `Shop`, `SERVICE_TYPES`
- Uses `period_range()` and `save_image()` from [Utilities](utils.md)
- Uses `scoped_query()` from `security.py` for multi-tenant data isolation
- Protected by `admin_required` from [Authentication & Users](auth.md)
- Stats feed into the [Pricing & Profit Model](../architecture/pricing.md) calculations
- Moderators redirect to [Moderator Panel](../../architecture/moderator.md)

# Citations
- app/main.py:1
- app/main.py:15
- app/main.py:19
- app/main.py:27
- app/main.py:39
- app/main.py:47
- app/main.py:50
- app/main.py:67
