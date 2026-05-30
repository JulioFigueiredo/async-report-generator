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
