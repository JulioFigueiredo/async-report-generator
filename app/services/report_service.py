from app.workers.tasks import generate_report
from app.workers.celery_app import celery

_STATE_MAP = {
    "PENDING": "queued",
    "STARTED": "processing",
    "SUCCESS": "done",
    "FAILURE": "failed",
}


def enqueue_report(report_type: str, region: str, month: str) -> str:
    task = generate_report.delay(report_type, region, month)
    return task.id


def get_status(task_id: str) -> dict:
    # NOTE: Celery returns PENDING for both "waiting to run" and "never existed".
    # A fabricated task_id will appear as status "queued" rather than 404.
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
