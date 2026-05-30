# CLAUDE.md — async-report-generator

Technical spec for **async-report-generator**: a FastAPI API that receives structured
report parameters, queues generation via Celery + Redis, and delivers a CSV file once
the worker finishes processing.

The goal of this project is to learn and demonstrate the pattern:
**producer → queue → worker → result**

---

## Objective

The client sends structured parameters via POST and immediately receives a `task_id`.
The report is generated in the background by a Celery worker. The client polls for
status and downloads the CSV when ready.

No LLM. No external database. Synthetic data generated in memory.
100% focus on the async messaging pattern.

---

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI |
| Validation | Pydantic v2 |
| Configuration | pydantic-settings |
| Queue / Broker | Redis 7 |
| Worker | Celery 5 |
| Data generation | Python stdlib (random, csv) |
| Containerization | Docker + Docker Compose |
| Tests | pytest + httpx + pytest-asyncio |

Do not add extra dependencies without a clear reason.

---

## Architecture

This project follows a layered architecture with strict separation of concerns.
Each layer has a single responsibility and must not leak into adjacent layers.

```
Request → api/ → services/ → workers/ → builders/
                     ↑
                  schemas/
                  core/
```

### Layer responsibilities

- **`api/`** — HTTP only. Receives requests, validates input via schemas, calls services. No business logic.
- **`services/`** — Orchestration layer. Calls Celery tasks, checks task status. No HTTP concepts (no Request, no Response).
- **`workers/`** — Celery configuration and task definitions. Calls builders. No HTTP concepts.
- **`builders/`** — Pure functions. Generates synthetic data and writes the CSV. No I/O other than the output file.
- **`schemas/`** — Pydantic models for API request/response contracts.
- **`core/`** — App-wide settings and startup logic.

---

## Project Structure

```
async-report-generator/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           └── reports.py      # Route handlers — delegates to services
│   ├── core/
│   │   └── config.py               # Settings via pydantic-settings
│   ├── schemas/
│   │   └── report.py               # ReportRequest, ReportResponse, TaskStatusResponse
│   ├── services/
│   │   └── report_service.py       # enqueue_report(), get_status(), get_filepath()
│   ├── workers/
│   │   ├── celery_app.py           # Celery instance and configuration
│   │   └── tasks.py                # @celery.task generate_report()
│   ├── builders/
│   │   └── report_builder.py       # Pure build_report() function
│   └── main.py                     # App entrypoint — includes routers, middleware
├── tests/
│   ├── unit/
│   │   ├── test_report_builder.py  # Pure function tests, no HTTP
│   │   └── test_report_service.py  # Service tests with mocked Celery
│   └── integration/
│       └── test_reports_api.py     # End-to-end route tests with httpx
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── CLAUDE.md
```

Never create files outside this structure without explicit justification.

---

## API Endpoints

All routes are registered under the `/api/v1/reports` prefix.

### POST /api/v1/reports
Enqueues a new report generation task.

**Request body:**
```json
{
  "type": "sales",
  "region": "southeast",
  "month": "january"
}
```

**Response `202 Accepted`:**
```json
{
  "task_id": "a1b2c3d4-...",
  "status": "queued"
}
```

---

### GET /api/v1/reports/{task_id}
Returns the current status of a task.

**Response `200 OK`:**
```json
{
  "task_id": "a1b2c3d4-...",
  "status": "processing" | "done" | "failed",
  "error": null
}
```

---

### GET /api/v1/reports/{task_id}/download
Returns the generated CSV file.

- Returns `404` if task does not exist
- Returns `404` with message `"Report is not ready yet"` if status is not `done`
- Returns `200` with `Content-Type: text/csv` and the file as attachment

---

## Pydantic Schemas

```python
# app/schemas/report.py

from pydantic import BaseModel
from typing import Literal

class ReportRequest(BaseModel):
    type: Literal["sales", "inventory", "customers"]
    region: Literal["north", "northeast", "southeast", "south", "midwest"]
    month: Literal["january", "february", "march", "april", "may", "june",
                   "july", "august", "september", "october", "november", "december"]

class ReportResponse(BaseModel):
    task_id: str
    status: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    error: str | None = None
```

---

## Core Configuration

```python
# app/core/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    reports_dir: str = "/tmp/reports"

    class Config:
        env_file = ".env"

settings = Settings()
```

All configuration must go through `settings`. Never use `os.getenv()` directly outside this file.

---

## Service Layer

The service layer is the only place that knows about Celery. Routes must never import
from `workers/` directly.

```python
# app/services/report_service.py

from app.workers.tasks import generate_report
from app.workers.celery_app import celery
from app.core.config import settings
import os

def enqueue_report(report_type: str, region: str, month: str) -> str:
    """Enqueues the report task and returns the task_id."""
    task = generate_report.delay(report_type, region, month)
    return task.id

def get_status(task_id: str) -> dict:
    """Returns the current status of a task."""
    result = celery.AsyncResult(task_id)
    ...

def get_filepath(task_id: str) -> str | None:
    """Returns the CSV filepath if the task is done, otherwise None."""
    ...
```

---

## Workers

```python
# app/workers/celery_app.py

from celery import Celery
from app.core.config import settings

celery = Celery(
    "async_report",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_track_started=True,
)
```

```python
# app/workers/tasks.py

from app.workers.celery_app import celery
from app.builders.report_builder import build_report
from app.core.config import settings
import os

@celery.task(bind=True)
def generate_report(self, report_type: str, region: str, month: str):
    os.makedirs(settings.reports_dir, exist_ok=True)
    filepath = f"{settings.reports_dir}/{self.request.id}.csv"
    build_report(report_type, region, month, filepath)
    return {"filepath": filepath}
```

---

## Builder

`build_report()` must be a pure function. No HTTP, no Celery, no config imports.
Receives all inputs as parameters. Only side effect: writing the CSV file.

```python
# app/builders/report_builder.py

def build_report(report_type: str, region: str, month: str, output_path: str) -> None:
    """
    Generates a synthetic CSV report and writes it to output_path.
    Data is randomly generated — no external dependencies.
    """
    ...
```

**Sales report columns:** `date`, `product`, `quantity`, `unit_price`, `total`
**Inventory report columns:** `sku`, `product`, `stock`, `min_stock`, `status`
**Customers report columns:** `id`, `name`, `city`, `orders`, `total_spent`

Generate between 30 and 100 rows per report.

---

## App Entrypoint

```python
# app/main.py

from fastapi import FastAPI
from app.api.v1.endpoints import reports

app = FastAPI(title="Async Report Generator")

app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
```

Nothing else lives in `main.py`.

---

## Environment Variables

```env
# .env.example
REDIS_URL=redis://redis:6379/0
REPORTS_DIR=/tmp/reports
```

---

## Docker Compose

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - redis
    volumes:
      - report_files:/tmp/reports

  worker:
    build: .
    command: celery -A app.workers.celery_app worker --loglevel=info
    env_file: .env
    depends_on:
      - redis
    volumes:
      - report_files:/tmp/reports

  redis:
    image: redis:7-alpine

volumes:
  report_files:
```

Both `api` and `worker` must share the same `report_files` volume so the worker can
write the CSV and the API can serve the download.

---

## Error Handling

| Situation | Behavior |
|---|---|
| Invalid `task_id` | `404 Not Found` |
| Download before `done` | `404 Not Found` — `"Report is not ready yet"` |
| Worker failure | `status: "failed"` with `error` field populated |
| Invalid parameters | `422 Unprocessable Entity` (automatic via Pydantic) |

---

## Implementation Steps

Work through these in order. Do not skip ahead.

1. **Core config** — implement `Settings` in `core/config.py`
2. **Schemas** — define all Pydantic models in `schemas/report.py`
3. **Builder** — implement `build_report()` in `builders/report_builder.py`
4. **Builder unit tests** — write `tests/unit/test_report_builder.py`
5. **Celery instance** — create `workers/celery_app.py`
6. **Task** — implement `generate_report` in `workers/tasks.py`
7. **Service layer** — implement `report_service.py` with `enqueue_report()`, `get_status()`, `get_filepath()`
8. **Service unit tests** — write `tests/unit/test_report_service.py` with mocked Celery
9. **API endpoints** — implement all 3 routes in `api/v1/endpoints/reports.py`, calling only services
10. **App entrypoint** — wire router in `main.py`
11. **Integration tests** — write `tests/integration/test_reports_api.py` with `httpx.AsyncClient`
12. **Docker Compose** — containerize, verify full flow works end-to-end
13. **README** — architecture diagram, how to run, curl examples

---

## What NOT to do

- Do not import from `workers/` inside `api/` — always go through `services/`
- Do not put business logic in route handlers — routes only call services
- Do not use `os.getenv()` outside `core/config.py` — always use `settings`
- Do not use a database — Redis as broker/backend + shared volume for files is enough
- Do not add authentication — out of scope
- Do not use an LLM to generate data — synthetic data with `random` is sufficient
- Do not delete files after download — let them expire via Celery's `result_expires`
- Do not over-engineer the report builder — simple `random` values are fine