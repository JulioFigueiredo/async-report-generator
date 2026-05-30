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
docker compose -f docker/docker-compose.yml up --build
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
