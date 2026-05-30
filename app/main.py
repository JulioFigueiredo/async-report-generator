from fastapi import FastAPI
from app.api.v1.endpoints import reports

app = FastAPI(title="Async Report Generator")

app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
