---
type: File
title: Data Models
description: SQLAlchemy models (User, Company, Car, Service, Part) with relationships
  and derived pricing/profit properties.
tags:
- sqlalchemy
- models
- database
- pricing
- orm
timestamp: '2026-07-06T17:33:01Z'
resource: file:///D:/Service/app/models.py
---

# Data Models

`app/models.py` defines the five SQLAlchemy models that form the application's data layer. All tables live in a single SQLite database (`instance/carservice.db`).

## Model Relationships

```mermaid
classDiagram
    class User {
        +int id
        +str username
        +str email
        +str full_name
        +str role
        +bool active
        +set_password()
        +check_password()
        +is_admin bool
    }
    class Company {
        +int id
        +str name
        +str address
        +str contact
        +str logo_path
    }
    class Car {
        +int id
        +str plate
        +str owner_name
        +str brand
        +int mileage
        +description() str
    }
    class Service {
        +int id
        +date date
        +float labor_price
        +total_full() float
        +total_profit() float
    }
    class Part {
        +int id
        +str name
        +float price
        +float price_with_discount
        +float quantity
        +line_full() float
        +line_profit() float
    }
    User "1" --> "*" Service : worker
    Car "1" --> "*" Service : has
    Service "1" --> "*" Part : contains
```

## User

Extends Flask-Login's `UserMixin`. Two roles defined by constants:
- `ROLE_ADMIN = "admin"` — can see all services, manage users, access setup/backup.
- `ROLE_WORKER = "radnik"` — sees only their own services.

Key methods:
- `set_password(password)` / `check_password(password)` — bcrypt-style hashing via Werkzeug.
- `is_admin` property — checks `self.role == ROLE_ADMIN`.
- `is_active` property — maps to the `active` column (Flask-Login interface).

## Company

A **single-row** table (always `id=1`) holding the shop's identity: name, address, contact info, and logo path. Populated on first run via the [Dashboard & Setup](main.md) page.

## Car

Indexed by `plate` (unique). Tracks vehicle details (brand, model, engine, fuel type, year), owner contact info, photo, and last-known mileage. Has a one-to-many relationship with `Service` (cascade delete-orphan).

The `description` property produces a human-readable summary like `"BMW 320 2.0 dizel 2020"`.

Fuel types are defined as a constant list: `benzin`, `dizel`, `ev`, `benzin/plin`, `hibrid`.

## Service

Links a `Car` to a `worker` (User) for a specific date. Stores labor price/description and odometer reading. Parts are a cascade-delete-orphan relationship.

### Derived price properties

| Property | Formula | Meaning |
|----------|---------|---------|
| `parts_total_full` | Σ part.line_full | What the customer pays for parts |
| `parts_total_cost` | Σ part.line_cost | Shop's actual parts cost |
| `parts_profit` | full − cost | Margin on parts |
| `total_full` | labor + parts_full | Total charged to customer |
| `total_profit` | labor + parts_profit | Shop's total profit |

These properties drive the [Pricing & Profit Model](../architecture/pricing.md) used throughout [Reports](reports.md) and [Printing](printing.md).

## Part

Each part has two price columns:
- `price` — retail / full price (what the customer sees).
- `price_with_discount` — shop's purchase cost (with supplier discount).

Line totals multiply by `quantity`:
- `line_full = price × quantity`
- `line_cost = price_with_discount × quantity`
- `line_profit = line_full − line_cost`

## Connections

- Used by every blueprint: [Service Records](services.md), [Car Management](cars.md), [Authentication & Users](auth.md), [Reports & Analytics](reports.md), [Printing & PDF](printing.md)
- Created/migrated by `init_db.py`
- Pricing logic documented in [Pricing & Profit Model](../architecture/pricing.md)

# Citations
- app/models.py:1
- app/models.py:9
- app/models.py:15
- app/models.py:30
- app/models.py:48
- app/models.py:59
- app/models.py:89
- app/models.py:104
- app/models.py:112
- app/models.py:131
- app/models.py:141
