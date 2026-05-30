from unittest.mock import MagicMock, patch
import pytest

@patch("app.services.report_service.generate_report")
def test_enqueue_report_returns_task_id(mock_task):
    from app.services.report_service import enqueue_report

    mock_result = MagicMock()
    mock_result.id = "abc-123"
    mock_task.delay.return_value = mock_result

    task_id = enqueue_report("sales", "southeast", "january")

    mock_task.delay.assert_called_once_with("sales", "southeast", "january")
    assert task_id == "abc-123"


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
