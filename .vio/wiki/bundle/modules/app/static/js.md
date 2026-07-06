---
type: Module
title: Frontend Assets
description: 'Client-side JavaScript modules: Chart.js analytics charts, dynamic service-form
  parts table with live price recalculation, and Bootstrap dark/light theme toggle.'
tags:
- javascript
- chartjs
- bootstrap
- dark-theme
- frontend
timestamp: '2026-07-06T17:34:00Z'
resource: file:///D:/Service/app/static/js
---

# Frontend Assets

The `app/static/js/` directory contains three custom JavaScript modules plus two vendor libraries (Chart.js and Bootstrap). All scripts are vanilla ES5 IIFEs (no build step required).

## Custom Modules

### `analytics.js` (73 LOC)
Renders four Chart.js charts on the `/analytics` page. Reads chart data from a `<script id="chartData">` JSON block embedded by the server.

**Charts rendered:**
- `#chTime` — combo bar + line chart: revenue (bars) and profit (line) over time
- `#chStruct` — doughnut chart: revenue structure (parts vs labor)
- `#chParts` — bar chart: parts full price vs discounted vs margin
- `#chWorker` — horizontal bar chart: profit per worker (admin-only)

All monetary values are formatted with `Number.toLocaleString("sr-RS")` plus the configured currency code.

### `service_form.js` (61 LOC)
Manages the dynamic parts table on the service create/edit form:

- **`recalc()`** — iterates all `.part-row` elements, computes `qty × price` for each, updates line totals and the summary (parts total, labor, grand total)
- **`addRow()`** — clones the `<template id="partRowTemplate">` and appends to `#partsBody`
- **Event delegation** — listens for `click` (add/remove part) and `input` (qty/price/disc/labor changes) events at the document level
- Starts with one empty row if none exist on DOM load

### `theme.js` (22 LOC)
Implements the dark/light theme toggle:
- Reads/writes the `data-bs-theme` attribute on `<html>` (Bootstrap 5 dark mode)
- Persists the choice in `localStorage`
- Updates the toggle button icon (☀️ / 🌙)

## Vendor Libraries

| File | Purpose |
|------|---------|
| `chart.umd.min.js` | Chart.js 4.x UMD bundle |
| `bootstrap.bundle.min.js` | Bootstrap 5 JS + Popper |

## Key Connections

- [Reports & Analytics](../../files/app/reports.md) — `_build_charts()` prepares the JSON data consumed by `analytics.js`
- [Service Records](../../files/app/services.md) — service form uses `service_form.js`
- [Pricing & Profit Model](../../architecture/pricing.md) — `service_form.js` mirrors the pricing logic client-side
- [Overview](../../overview.md)

# Citations

- app/static/js/analytics.js:1-3 (IIFE, reads chartData JSON element)
- app/static/js/analytics.js:10-11 (Serbian money formatting with sr-RS locale)
- app/static/js/analytics.js:21-38 (chTime — combo bar+line chart)
- app/static/js/analytics.js:40-47 (chStruct — doughnut chart)
- app/static/js/analytics.js:49-57 (chParts — bar chart)
- app/static/js/analytics.js:59-68 (chWorker — horizontal bar chart)
- app/static/js/service_form.js:1-2 (IIFE start)
- app/static/js/service_form.js:10-26 (recalc — live price computation)
- app/static/js/service_form.js:28-32 (addRow — template cloning)
- app/static/js/service_form.js:34-46 (event delegation for click and input)
- app/static/js/theme.js:1-22 (dark/light toggle with localStorage persistence)
