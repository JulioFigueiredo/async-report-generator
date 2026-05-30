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
