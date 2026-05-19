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
