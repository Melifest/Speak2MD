from pydantic import BaseModel, Field
from typing import Optional

class UploadResponse(BaseModel):
    job_id: str = Field(..., description="ID созданной задачи")
    status: str = Field(..., description="Статус задачи (processing|ready|error)")

class StatusResponse(BaseModel):
    status: str
    progress: int

class ErrorResponse(BaseModel):
    error: str

