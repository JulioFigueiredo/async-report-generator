# Async Report Generator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI API that receives report parameters, queues generation via Celery + Redis, and delivers a CSV file once the Celery worker finishes.

**Architecture:** HTTP layer delegates to a service layer, which enqueues Celery tasks that call pure builder functions. The API and worker share a Docker volume for the generated CSV files. Redis acts as both broker and result backend.

**Tech Stack:** FastAPI, Pydantic v2, pydantic-settings, Celery 5, Redis 7, pytest, httpx, Docker + Docker Compose

---

## File Map

| File | Role |
|---|---|
| `app/core/config.py` | `Settings` via pydantic-settings — single source of env vars |
| `app/schemas/report.py` | Pydantic request/response models |
| `app/builders/report_builder.py` | Pure `build_report()` — generates synthetic CSV |
| `app/workers/celery_app.py` | Celery instance and configuration |
| `app/workers/tasks.py` | `@celery.task generate_report()` — calls builder |
| `app/services/report_service.py` | `enqueue_report()`, `get_status()`, `get_filepath()` |
| `app/api/v1/endpoints/reports.py` | 3 route handlers — delegates to service only |
| `app/main.py` | FastAPI app entrypoint — includes router |
| `tests/unit/test_report_builder.py` | Pure function tests, no HTTP, no Celery |
| `tests/unit/test_report_service.py` | Service tests with mocked Celery |
| `tests/integration/test_reports_api.py` | Route tests with httpx AsyncClient + mocked services |
| `conftest.py` | Shared pytest fixtures |
| `requirements.txt` | Pinned dependencies |
| `.env.example` | Example environment variables |
| `Dockerfile` | Single image for both api and worker |
| `docker-compose.yml` | api + worker + redis services |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `conftest.py`
- Create: all `__init__.py` files for every package

- [ ] **Step 1: Create all package directories with `__init__.py`**

```bash
mkdir -p app/core app/schemas app/builders app/workers app/services
mkdir -p app/api/v1/endpoints
mkdir -p tests/unit tests/integration

touch app/__init__.py
touch app/core/__init__.py
touch app/schemas/__init__.py
touch app/builders/__init__.py
touch app/workers/__init__.py
touch app/services/__init__.py
touch app/api/__init__.py
touch app/api/v1/__init__.py
touch app/api/v1/endpoints/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
celery==5.4.0
redis==5.1.0
pydantic-settings==2.4.0
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
anyio==4.6.0
```

- [ ] **Step 3: Create `.env.example`**

```env
REDIS_URL=redis://redis:6379/0
REPORTS_DIR=/tmp/reports
```

- [ ] **Step 4: Create `conftest.py`** at the repo root

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
```

- [ ] **Step 5: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example conftest.py pytest.ini app/ tests/
git commit -m "chore: scaffold project structure"
```

---

## Task 2: Core Configuration

**Files:**
- Create: `app/core/config.py`

- [ ] **Step 1: Implement `app/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    reports_dir: str = "/tmp/reports"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
python -c "from app.core.config import settings; print(settings.redis_url)"
```

Expected output: `redis://localhost:6379/0`

- [ ] **Step 3: Commit**

```bash
git add app/core/config.py
git commit -m "feat: add core settings via pydantic-settings"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `app/schemas/report.py`

- [ ] **Step 1: Implement `app/schemas/report.py`**

```python
from pydantic import BaseModel
from typing import Literal


class ReportRequest(BaseModel):
    type: Literal["sales", "inventory", "customers"]
    region: Literal["north", "northeast", "southeast", "south", "midwest"]
    month: Literal[
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december"
    ]


class ReportResponse(BaseModel):
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    error: str | None = None
```

- [ ] **Step 2: Verify schemas import cleanly**

```bash
python -c "from app.schemas.report import ReportRequest, ReportResponse, TaskStatusResponse; print('ok')"
```

Expected output: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/schemas/report.py
git commit -m "feat: add Pydantic schemas for report API"
```

---

## Task 4: Report Builder (TDD)

**Files:**
- Create: `app/builders/report_builder.py`
- Create: `tests/unit/test_report_builder.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_report_builder.py
import csv
import os
import tempfile
import pytest
from app.builders.report_builder import build_report


SALES_COLUMNS = ["date", "product", "quantity", "unit_price", "total"]
INVENTORY_COLUMNS = ["sku", "product", "stock", "min_stock", "status"]
CUSTOMERS_COLUMNS = ["id", "name", "city", "orders", "total_spent"]


@pytest.fixture
def tmp_path_csv(tmp_path):
    return str(tmp_path / "report.csv")


def _read_csv(filepath):
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def test_build_report_creates_file(tmp_path_csv):
    build_report("sales", "southeast", "january", tmp_path_csv)
    assert os.path.exists(tmp_path_csv)


def test_sales_report_has_correct_columns(tmp_path_csv):
    build_report("sales", "southeast", "january", tmp_path_csv)
    rows = _read_csv(tmp_path_csv)
    assert rows[0].keys() == set(SALES_COLUMNS)


def test_sales_report_row_count_in_range(tmp_path_csv):
    build_report("sales", "southeast", "january", tmp_path_csv)
    rows = _read_csv(tmp_path_csv)
    assert 30 <= len(rows) <= 100


def test_inventory_report_has_correct_columns(tmp_path_csv):
    build_report("inventory", "north", "march", tmp_path_csv)
    rows = _read_csv(tmp_path_csv)
    assert rows[0].keys() == set(INVENTORY_COLUMNS)


def test_inventory_report_row_count_in_range(tmp_path_csv):
    build_report("inventory", "north", "march", tmp_path_csv)
    rows = _read_csv(tmp_path_csv)
    assert 30 <= len(rows) <= 100


def test_customers_report_has_correct_columns(tmp_path_csv):
    build_report("customers", "midwest", "july", tmp_path_csv)
    rows = _read_csv(tmp_path_csv)
    assert rows[0].keys() == set(CUSTOMERS_COLUMNS)


def test_customers_report_row_count_in_range(tmp_path_csv):
    build_report("customers", "midwest", "july", tmp_path_csv)
    rows = _read_csv(tmp_path_csv)
    assert 30 <= len(rows) <= 100


def test_sales_total_equals_quantity_times_price(tmp_path_csv):
    build_report("sales", "south", "february", tmp_path_csv)
    rows = _read_csv(tmp_path_csv)
    for row in rows:
        expected = round(int(row["quantity"]) * float(row["unit_price"]), 2)
        assert float(row["total"]) == expected
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/unit/test_report_builder.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `build_report` does not exist yet.

- [ ] **Step 3: Implement `app/builders/report_builder.py`**

```python
import csv
import random

_MONTH_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

_PRODUCTS = ["Widget A", "Widget B", "Gadget X", "Gadget Y", "Component Z"]
_SKUS = [f"SKU-{i:04d}" for i in range(1, 21)]
_CITIES = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Salvador", "Curitiba"]
_FIRST_NAMES = ["Alice", "Bruno", "Carol", "Diego", "Eva", "Felipe"]
_LAST_NAMES = ["Silva", "Santos", "Costa", "Oliveira", "Lima"]


def _row_count():
    return random.randint(30, 100)


def _build_sales(writer, month: str) -> None:
    month_num = _MONTH_NUM[month]
    for _ in range(_row_count()):
        quantity = random.randint(1, 50)
        unit_price = round(random.uniform(10.0, 500.0), 2)
        writer.writerow({
            "date": f"2024-{month_num:02d}-{random.randint(1, 28):02d}",
            "product": random.choice(_PRODUCTS),
            "quantity": quantity,
            "unit_price": unit_price,
            "total": round(quantity * unit_price, 2),
        })


def _build_inventory(writer) -> None:
    for _ in range(_row_count()):
        stock = random.randint(0, 200)
        min_stock = random.randint(10, 50)
        if stock >= min_stock:
            status = "ok"
        elif stock >= min_stock // 2:
            status = "low"
        else:
            status = "critical"
        writer.writerow({
            "sku": random.choice(_SKUS),
            "product": random.choice(_PRODUCTS),
            "stock": stock,
            "min_stock": min_stock,
            "status": status,
        })


def _build_customers(writer) -> None:
    for i in range(_row_count()):
        writer.writerow({
            "id": i + 1,
            "name": f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}",
            "city": random.choice(_CITIES),
            "orders": random.randint(1, 50),
            "total_spent": round(random.uniform(100.0, 10000.0), 2),
        })


_COLUMNS = {
    "sales": ["date", "product", "quantity", "unit_price", "total"],
    "inventory": ["sku", "product", "stock", "min_stock", "status"],
    "customers": ["id", "name", "city", "orders", "total_spent"],
}

_BUILDERS = {
    "sales": lambda writer, month: _build_sales(writer, month),
    "inventory": lambda writer, month: _build_inventory(writer),
    "customers": lambda writer, month: _build_customers(writer),
}


def build_report(report_type: str, region: str, month: str, output_path: str) -> None:
    """
    Generates a synthetic CSV report and writes it to output_path.
    Data is randomly generated — no external dependencies.
    """
    columns = _COLUMNS[report_type]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        _BUILDERS[report_type](writer, month)
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/unit/test_report_builder.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/builders/report_builder.py tests/unit/test_report_builder.py
git commit -m "feat: implement report builder with TDD"
```

---

## Task 5: Celery App

**Files:**
- Create: `app/workers/celery_app.py`

- [ ] **Step 1: Implement `app/workers/celery_app.py`**

```python
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

- [ ] **Step 2: Verify it imports cleanly**

```bash
python -c "from app.workers.celery_app import celery; print(celery.main)"
```

Expected output: `async_report`

- [ ] **Step 3: Commit**

```bash
git add app/workers/celery_app.py
git commit -m "feat: add Celery app instance"
```

---

## Task 6: Celery Task

**Files:**
- Create: `app/workers/tasks.py`

- [ ] **Step 1: Implement `app/workers/tasks.py`**

```python
import os
from app.workers.celery_app import celery
from app.builders.report_builder import build_report
from app.core.config import settings


@celery.task(bind=True)
def generate_report(self, report_type: str, region: str, month: str):
    os.makedirs(settings.reports_dir, exist_ok=True)
    filepath = f"{settings.reports_dir}/{self.request.id}.csv"
    build_report(report_type, region, month, filepath)
    return {"filepath": filepath}
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
python -c "from app.workers.tasks import generate_report; print(generate_report.name)"
```

Expected output: `app.workers.tasks.generate_report`

- [ ] **Step 3: Commit**

```bash
git add app/workers/tasks.py
git commit -m "feat: add generate_report Celery task"
```

---

## Task 7: Service Layer (TDD)

**Files:**
- Create: `app/services/report_service.py`
- Create: `tests/unit/test_report_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_report_service.py
from unittest.mock import MagicMock, patch
import pytest


# ── enqueue_report ────────────────────────────────────────────────────────────

@patch("app.services.report_service.generate_report")
def test_enqueue_report_returns_task_id(mock_task):
    from app.services.report_service import enqueue_report

    mock_result = MagicMock()
    mock_result.id = "abc-123"
    mock_task.delay.return_value = mock_result

    task_id = enqueue_report("sales", "southeast", "january")

    mock_task.delay.assert_called_once_with("sales", "southeast", "january")
    assert task_id == "abc-123"


# ── get_status ────────────────────────────────────────────────────────────────

def _make_async_result(state, info=None):
    mock = MagicMock()
    mock.state = state
    mock.info = info
    return mock


@patch("app.services.report_service.celery")
def test_get_status_pending_maps_to_queued(mock_celery):
    from app.services.report_service import get_status

    mock_celery.AsyncResult.return_value = _make_async_result("PENDING")
    result = get_status("abc-123")

    assert result == {"task_id": "abc-123", "status": "queued", "error": None}


@patch("app.services.report_service.celery")
def test_get_status_started_maps_to_processing(mock_celery):
    from app.services.report_service import get_status

    mock_celery.AsyncResult.return_value = _make_async_result("STARTED")
    result = get_status("abc-123")

    assert result == {"task_id": "abc-123", "status": "processing", "error": None}


@patch("app.services.report_service.celery")
def test_get_status_success_maps_to_done(mock_celery):
    from app.services.report_service import get_status

    mock_celery.AsyncResult.return_value = _make_async_result("SUCCESS")
    result = get_status("abc-123")

    assert result == {"task_id": "abc-123", "status": "done", "error": None}


@patch("app.services.report_service.celery")
def test_get_status_failure_maps_to_failed_with_error(mock_celery):
    from app.services.report_service import get_status

    mock_celery.AsyncResult.return_value = _make_async_result(
        "FAILURE", info=ValueError("boom")
    )
    result = get_status("abc-123")

    assert result["status"] == "failed"
    assert "boom" in result["error"]


# ── get_filepath ──────────────────────────────────────────────────────────────

@patch("app.services.report_service.celery")
def test_get_filepath_returns_path_when_done(mock_celery):
    from app.services.report_service import get_filepath

    mock_result = _make_async_result("SUCCESS")
    mock_result.result = {"filepath": "/tmp/reports/abc-123.csv"}
    mock_celery.AsyncResult.return_value = mock_result

    assert get_filepath("abc-123") == "/tmp/reports/abc-123.csv"


@patch("app.services.report_service.celery")
def test_get_filepath_returns_none_when_not_done(mock_celery):
    from app.services.report_service import get_filepath

    mock_celery.AsyncResult.return_value = _make_async_result("PENDING")

    assert get_filepath("abc-123") is None
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/unit/test_report_service.py -v
```

Expected: `ImportError` — `report_service` does not exist yet.

- [ ] **Step 3: Implement `app/services/report_service.py`**

```python
import os
from app.workers.tasks import generate_report
from app.workers.celery_app import celery
from app.core.config import settings

_STATE_MAP = {
    "PENDING": "queued",
    "STARTED": "processing",
    "SUCCESS": "done",
    "FAILURE": "failed",
}


def enqueue_report(report_type: str, region: str, month: str) -> str:
    """Enqueues the report task and returns the task_id."""
    task = generate_report.delay(report_type, region, month)
    return task.id


def get_status(task_id: str) -> dict:
    """Returns the current status of a task."""
    result = celery.AsyncResult(task_id)
    status = _STATE_MAP.get(result.state, "queued")
    error = str(result.info) if result.state == "FAILURE" else None
    return {"task_id": task_id, "status": status, "error": error}


def get_filepath(task_id: str) -> str | None:
    """Returns the CSV filepath if the task is done, otherwise None."""
    result = celery.AsyncResult(task_id)
    if result.state == "SUCCESS":
        return result.result.get("filepath")
    return None
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/unit/test_report_service.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/report_service.py tests/unit/test_report_service.py
git commit -m "feat: implement service layer with TDD"
```

---

## Task 8: API Endpoints

**Files:**
- Create: `app/api/v1/endpoints/reports.py`

- [ ] **Step 1: Implement `app/api/v1/endpoints/reports.py`**

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.schemas.report import ReportRequest, ReportResponse, TaskStatusResponse
import app.services.report_service as report_service

router = APIRouter()


@router.post("", status_code=202, response_model=ReportResponse)
def enqueue_report(request: ReportRequest):
    task_id = report_service.enqueue_report(request.type, request.region, request.month)
    return ReportResponse(task_id=task_id, status="queued")


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_status(task_id: str):
    status = report_service.get_status(task_id)
    return TaskStatusResponse(**status)


@router.get("/{task_id}/download")
def download_report(task_id: str):
    filepath = report_service.get_filepath(task_id)
    if filepath is None:
        raise HTTPException(status_code=404, detail="Report is not ready yet")
    return FileResponse(
        path=filepath,
        media_type="text/csv",
        filename=f"report-{task_id}.csv",
    )
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
python -c "from app.api.v1.endpoints.reports import router; print('ok')"
```

Expected output: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/api/v1/endpoints/reports.py
git commit -m "feat: add API route handlers"
```

---

## Task 9: App Entrypoint

**Files:**
- Create: `app/main.py`

- [ ] **Step 1: Implement `app/main.py`**

```python
from fastapi import FastAPI
from app.api.v1.endpoints import reports

app = FastAPI(title="Async Report Generator")

app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
```

- [ ] **Step 2: Verify the app starts**

```bash
python -c "from app.main import app; print(app.title)"
```

Expected output: `Async Report Generator`

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: wire FastAPI app entrypoint"
```

---

## Task 10: Integration Tests

**Files:**
- Create: `tests/integration/test_reports_api.py`

- [ ] **Step 1: Write the integration tests**

```python
# tests/integration/test_reports_api.py
from unittest.mock import patch
import pytest


VALID_PAYLOAD = {"type": "sales", "region": "southeast", "month": "january"}


# ── POST /api/v1/reports ──────────────────────────────────────────────────────

@patch("app.services.report_service.generate_report")
async def test_post_report_returns_202(mock_task, client):
    mock_task.delay.return_value.id = "task-abc"

    response = await client.post("/api/v1/reports", json=VALID_PAYLOAD)

    assert response.status_code == 202
    body = response.json()
    assert body["task_id"] == "task-abc"
    assert body["status"] == "queued"


async def test_post_report_invalid_type_returns_422(client):
    response = await client.post(
        "/api/v1/reports",
        json={"type": "invalid", "region": "southeast", "month": "january"},
    )
    assert response.status_code == 422


async def test_post_report_invalid_region_returns_422(client):
    response = await client.post(
        "/api/v1/reports",
        json={"type": "sales", "region": "europe", "month": "january"},
    )
    assert response.status_code == 422


# ── GET /api/v1/reports/{task_id} ─────────────────────────────────────────────

@patch("app.services.report_service.celery")
async def test_get_status_returns_200(mock_celery, client):
    from unittest.mock import MagicMock

    mock_result = MagicMock()
    mock_result.state = "SUCCESS"
    mock_result.info = None
    mock_celery.AsyncResult.return_value = mock_result

    response = await client.get("/api/v1/reports/task-abc")

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == "task-abc"
    assert body["status"] == "done"
    assert body["error"] is None


@patch("app.services.report_service.celery")
async def test_get_status_failed_includes_error(mock_celery, client):
    from unittest.mock import MagicMock

    mock_result = MagicMock()
    mock_result.state = "FAILURE"
    mock_result.info = ValueError("something went wrong")
    mock_celery.AsyncResult.return_value = mock_result

    response = await client.get("/api/v1/reports/task-abc")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert "something went wrong" in body["error"]


# ── GET /api/v1/reports/{task_id}/download ────────────────────────────────────

@patch("app.services.report_service.celery")
async def test_download_not_ready_returns_404(mock_celery, client):
    from unittest.mock import MagicMock

    mock_result = MagicMock()
    mock_result.state = "PENDING"
    mock_celery.AsyncResult.return_value = mock_result

    response = await client.get("/api/v1/reports/task-abc/download")

    assert response.status_code == 404
    assert response.json()["detail"] == "Report is not ready yet"


@patch("app.services.report_service.celery")
async def test_download_ready_returns_csv(mock_celery, client, tmp_path):
    from unittest.mock import MagicMock
    import csv

    # create a real CSV file for FileResponse to serve
    csv_path = str(tmp_path / "report.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "product"])
        writer.writeheader()
        writer.writerow({"date": "2024-01-01", "product": "Widget"})

    mock_result = MagicMock()
    mock_result.state = "SUCCESS"
    mock_result.result = {"filepath": csv_path}
    mock_celery.AsyncResult.return_value = mock_result

    response = await client.get("/api/v1/reports/task-abc/download")

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
```

- [ ] **Step 2: Run all tests**

```bash
pytest -v
```

Expected: all tests PASS (unit + integration).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_reports_api.py
git commit -m "test: add integration tests for report API"
```

---

## Task 11: Docker

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create `docker-compose.yml`**

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

- [ ] **Step 3: Create `.env` from example**

```bash
cp .env.example .env
```

- [ ] **Step 4: Build and start the stack**

```bash
docker compose up --build -d
```

Expected: api, worker, and redis containers start without errors.

- [ ] **Step 5: Smoke test the full flow**

```bash
# Enqueue a report
curl -s -X POST http://localhost:8000/api/v1/reports \
  -H "Content-Type: application/json" \
  -d '{"type": "sales", "region": "southeast", "month": "january"}'
```

Expected response:
```json
{"task_id": "<uuid>", "status": "queued"}
```

```bash
# Poll status (replace <task_id> with actual value)
curl -s http://localhost:8000/api/v1/reports/<task_id>
```

Expected response:
```json
{"task_id": "<uuid>", "status": "done", "error": null}
```

```bash
# Download the CSV
curl -s http://localhost:8000/api/v1/reports/<task_id>/download -o report.csv
head report.csv
```

Expected: CSV with `date,product,quantity,unit_price,total` header and rows.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile docker-compose.yml .env.example
git commit -m "feat: add Docker and Docker Compose setup"
```

---

## Task 12: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# Async Report Generator

A FastAPI service that demonstrates the **producer → queue → worker → result** pattern.

The client POSTs report parameters and immediately receives a `task_id`. A Celery worker generates the CSV in the background. The client polls for status and downloads the file when ready.

## Architecture

```
Request → api/ → services/ → workers/ → builders/
                     ↑
                  schemas/
                  core/
```

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI |
| Validation | Pydantic v2 |
| Queue / Broker | Redis 7 |
| Worker | Celery 5 |
| Data generation | Python stdlib (random, csv) |
| Containerization | Docker + Docker Compose |

## How to Run

```bash
cp .env.example .env
docker compose up --build
```

## API Usage

### Enqueue a report

```bash
curl -X POST http://localhost:8000/api/v1/reports \
  -H "Content-Type: application/json" \
  -d '{"type": "sales", "region": "southeast", "month": "january"}'
```

```json
{"task_id": "a1b2c3d4-...", "status": "queued"}
```

### Poll status

```bash
curl http://localhost:8000/api/v1/reports/<task_id>
```

```json
{"task_id": "a1b2c3d4-...", "status": "done", "error": null}
```

### Download CSV

```bash
curl http://localhost:8000/api/v1/reports/<task_id>/download -o report.csv
```

### Report types

| Parameter | Values |
|---|---|
| `type` | `sales`, `inventory`, `customers` |
| `region` | `north`, `northeast`, `southeast`, `south`, `midwest` |
| `month` | `january` … `december` |

## Running Tests

```bash
pip install -r requirements.txt
pytest -v
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with architecture and usage"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered in |
|---|---|
| POST /api/v1/reports → 202 + task_id | Task 8, integration tests Task 10 |
| GET /api/v1/reports/{task_id} → status | Task 8, integration tests Task 10 |
| GET /api/v1/reports/{task_id}/download → CSV | Task 8, integration tests Task 10 |
| 404 download before done | Task 8, integration tests Task 10 |
| status: queued / processing / done / failed | Task 7 |
| Worker failure → failed + error field | Task 7, integration tests Task 10 |
| Invalid params → 422 | Automatic via Pydantic, tested in Task 10 |
| Sales columns: date, product, quantity, unit_price, total | Task 4 |
| Inventory columns: sku, product, stock, min_stock, status | Task 4 |
| Customers columns: id, name, city, orders, total_spent | Task 4 |
| 30–100 rows per report | Task 4 |
| Routes never import from workers/ | Task 8 — imports only from services/ |
| No os.getenv() outside config.py | All tasks use `settings` |
| Shared Docker volume for CSV files | Task 11 |
| Redis as broker + backend | Task 5 |
| result_expires=3600 | Task 5 |
| task_track_started=True | Task 5 |

All spec requirements are covered. No placeholders or TODOs found.
