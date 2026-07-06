---
type: Data Flow
title: Data Flow
description: 'End-to-end data flow from browser through Flask blueprints to SQLite:
  the plate-first service workflow, journal generation, and print/PDF pipeline.'
tags:
- data-flow
- workflow
- request-lifecycle
- flask
- sqlite
timestamp: '2026-07-06T17:32:22Z'
---

# Data Flow

This page traces the key data flows through the Auto Servis application — from HTTP request to database and back.

## Request Lifecycle

```mermaid
sequenceDiagram
    participant Browser
    participant Waitress
    participant Flask as Flask App
    participant BP as Blueprint Handler
    participant DB as SQLite (WAL)

    Browser->>Waitress: HTTP Request
    Waitress->>Flask: WSGI call
    Flask->>Flask: before_request (deactivation check)
    Flask->>Flask: CSRF validation (POST)
    Flask->>BP: Route dispatch
    BP->>DB: SQLAlchemy query / commit
    DB-->>BP: Result set
    BP-->>Flask: render_template()
    Flask->>Flask: after_request (security headers)
    Flask-->>Waitress: HTTP Response
    Waitress-->>Browser: HTML / PDF / JSON
```

## Plate-First Service Creation

The primary business workflow — creating a new service record:

```mermaid
sequenceDiagram
    participant W as Worker
    participant Start as /service/start
    participant Cars as /car/new
    participant New as /service/new
    participant DB as SQLite

    W->>Start: POST (plate: "NS123AB")
    Start->>DB: Car.query.filter_by(plate)
    alt Car found
        DB-->>Start: Car object
        Start-->>W: Redirect to /service/new?car_id=X
    else Car not found
        DB-->>Start: None
        Start-->>W: Redirect to /car/new?plate=NS123AB&then=service
        W->>Cars: POST (car details)
        Cars->>DB: INSERT Car
        Cars-->>W: Redirect to /service/new?car_id=X
    end
    W->>New: POST (date, mileage, labor, parts[])
    New->>DB: INSERT Service
    New->>DB: INSERT Parts (from form arrays)
    New->>DB: UPDATE Car.mileage (recompute)
    New-->>W: Redirect to /service/<id>
```

## Journal Generation Flow

How journals are produced (both on-demand and scheduled):

```mermaid
flowchart TD
    Trigger{"Source"} -->|Web UI| ReportsIndex["/reports GET"]
    Trigger -->|Scheduler| Dispatch["_dispatch()"]
    ReportsIndex --> ComposeJournal["compose_journal(period, ref, worker)"]
    Dispatch --> ComposeJournal
    ComposeJournal --> PeriodRange["period_range() → (start, end)"]
    PeriodRange --> QueryServices["Service.query.filter(date between)"]
    QueryServices --> Summarize["summarize(services)"]
    Summarize --> ByWorker{"worker is None?"}
    ByWorker -->|yes| GroupByWorker["Group by worker, summarize each"]
    ByWorker -->|no| JournalDict["Return journal dict"]
    GroupByWorker --> JournalDict
    JournalDict -->|Web| RenderHTML["render reports/index.html"]
    JournalDict -->|Email| RenderEmail["render email/journal.html"]
    RenderEmail --> SendEmail["send_email() via SMTP"]
```

## Print & PDF Pipeline

```mermaid
flowchart LR
    Request["/print/service/1?mode=owner"] --> Context["_service_context()"]
    Context --> Access{"_can_access()?"}
    Access -->|no| Abort["403"]
    Access -->|yes| Template["render print/services.html"]
    Template --> BrowserPrint["Browser Print Dialog"]

    RequestPDF["/pdf/service/1?mode=owner"] --> ContextPDF["_service_context()"]
    ContextPDF --> TemplatePDF["render print/pdf.html"]
    TemplatePDF --> xhtml2pdf["xhtml2pdf.pisa.CreatePDF()"]
    xhtml2pdf --> LinkCallback["_link_callback() maps URLs to paths"]
    xhtml2pdf --> PDFBytes["PDF bytes response"]
```

## Data Access Patterns

| Blueprint | Reads | Writes |
|-----------|-------|--------|
| `auth_bp` | User | User |
| `main_bp` | Service, Car, Company | Company |
| `cars_bp` | Car, Service | Car |
| `services_bp` | Car, Service, Part | Service, Part, Car (mileage) |
| `reports_bp` | Service, User | — |
| `print_bp` | Service, Car | — |
| `backup_bp` | — (raw SQLite) | Filesystem (zip) |

## How It Connects

- Blueprint details: [Authentication](../files/app/auth.md), [Dashboard](../files/app/main.md), [Cars](../files/app/cars.md), [Services](../files/app/services.md), [Reports](../files/app/reports.md), [Printing](../files/app/printing.md), [Backup](../files/app/backup.md)
- Data model: [Data Models](../files/app/models.md)
- Security hooks: [Security Architecture](security.md)
- Scheduler trigger: [Background Scheduler](scheduler.md)
- Server entry: [Deployment](build-and-deploy.md)

# Citations
- app/__init__.py:62-67
- app/__init__.py:92-112
- app/services.py:42-89
- app/reports.py:120-160
- app/printing.py:42-73
- app/pdf.py:48-56
