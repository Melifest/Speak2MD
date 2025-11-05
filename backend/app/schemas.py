from pydantic import BaseModel, Field
from typing import Optional

class UploadResponse(BaseModel):
    job_id: str = Field(..., description="ID созданной задачи")
    status: str = Field(..., description="Статус задачи (processing|ready|error)")

class StatusResponse(BaseModel):
    job_id: str = Field(..., description="ID задачи")
    status: str = Field(..., description="Статус задачи (processing|ready|completed|error)")
    progress: int = Field(..., ge=0, le=100, description="Прогресс в процентах")
    message: Optional[str] = Field(None, description="Дополнительное сообщение")

class ResultResponse(BaseModel):
    job_id: str = Field(..., description="ID задачи")
    content: str = Field(..., description="Содержимое результата")
    format: str = Field(..., description="Формат результата (markdown|json)")

class ErrorResponse(BaseModel):
    error: str

