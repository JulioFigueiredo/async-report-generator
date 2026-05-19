from unittest.mock import patch, MagicMock
import pytest

VALID_PAYLOAD = {"type": "sales", "region": "southeast", "month": "january"}

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


@patch("app.services.report_service.celery")
async def test_get_status_returns_200(mock_celery, client):
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
    mock_result = MagicMock()
    mock_result.state = "FAILURE"
    mock_result.info = ValueError("something went wrong")
    mock_celery.AsyncResult.return_value = mock_result

    response = await client.get("/api/v1/reports/task-abc")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert "something went wrong" in body["error"]


@patch("app.services.report_service.celery")
async def test_download_not_ready_returns_404(mock_celery, client):
    mock_result = MagicMock()
    mock_result.state = "PENDING"
    mock_celery.AsyncResult.return_value = mock_result

    response = await client.get("/api/v1/reports/task-abc/download")

    assert response.status_code == 404
    assert response.json()["detail"] == "Report is not ready yet"


@patch("app.services.report_service.celery")
async def test_download_ready_returns_csv(mock_celery, client, tmp_path):
    import csv

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
