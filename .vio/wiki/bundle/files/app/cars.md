---
type: File
title: Car Management
description: 'CRUD operations for vehicles: registration by plate, search, photo upload,
  editing, and detail view with service history.'
tags:
- cars
- crud
- vehicles
- blueprint
- upload
timestamp: '2026-07-06T17:34:03Z'
resource: file:///D:/Service/app/cars.py
---

# Car Management

`app/cars.py` defines the `cars_bp` blueprint handling vehicle registration, listing, detail view, and editing. Cars are the central entity around which services are organized — every service is attached to a car identified by its license plate.

## Endpoints

| Route | Method | Function | Description |
|-------|--------|----------|-------------|
| `/cars` | GET | `list_cars()` | Searchable list of all cars |
| `/car/<id>` | GET | `detail(car_id)` | Car details + service history |
| `/car/new` | GET/POST | `new()` | Register a new car |
| `/car/<id>/edit` | GET/POST | `edit(car_id)` | Edit car details |

## Plate-first integration

The `new()` route accepts optional query parameters:
- `plate` — pre-fills the registration plate (passed from the [Service Records](services.md) plate-first flow).
- `then=service` — after saving the new car, redirects to create a service for it instead of the car detail page.

This enables the seamless flow: enter plate → car doesn't exist → register it → immediately create a service.

## Search

`list_cars()` supports a `q` query parameter that filters cars by plate, owner name, brand, or model using case-insensitive `ILIKE` matching across all four fields with `db.or_()`.

## Photo upload

Both `new()` and `edit()` accept an uploaded photo file. The photo is saved via `save_image()` from [Utilities](utils.md) into the `cars/` subdirectory of the upload folder. On edit, the old photo file is deleted from disk before saving the new one.

## Plate normalization

`_normalise_plate(plate)` strips spaces, converts to uppercase — ensuring plates like `"bg 123 ab"` and `"BG123AB"` are treated as the same vehicle. Duplicate plates are checked before insert.

## Access control

- All routes require login.
- The detail page filters services: workers see only their own; admins see all.

## Connections

- Uses [Data Models](models.md) — `Car`, `Service`, `FUEL_TYPES`
- Photo handling via `save_image()` from [Utilities](utils.md)
- Multi-tenant: new cars are assigned `shop_id=current_user.shop_id`; listing uses `scoped_query()` for admin view
- Integrated with [Service Records](services.md) plate-first flow
- Service history links to [Printing & PDF](printing.md)

# Citations
- app/cars.py:1
- app/cars.py:15
- app/cars.py:17
- app/cars.py:22
- app/cars.py:38
- app/cars.py:50
- app/cars.py:87
- app/cars.py:118
