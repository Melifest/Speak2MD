from pydantic import BaseModel, Field
from typing import Optional

class UploadResponse(BaseModel):
    job_id: str = Field(..., description="ID созданной задачи")
    status: str = Field(..., description="Статус задачи (processing|ready|error)")

class StatusResponse(BaseModel):
    job_id: str = Field(..., description="ID задачи")
    status: str = Field(..., description="Статус задачи (processing|completed|error)")
    progress: int = Field(..., ge=0, le=100, description="Прогресс в процентах")
    message: Optional[str] = Field(None, description="Дополнительное сообщение")

class ErrorResponse(BaseModel):
    error: str

