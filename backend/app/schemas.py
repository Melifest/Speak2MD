from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

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

# Схемы аутентификации 
class AuthRegisterRequest(BaseModel):
    username: str = Field(..., description="Имя пользователя (уникальное)")
    password: str = Field(..., min_length=8, description="Пароль (минимум 8 символов)")
    full_name: Optional[str] = Field(None, description="Полное имя")

class AuthLoginRequest(BaseModel):
    username: str = Field(..., description="Имя пользователя")
    password: str = Field(..., description="Пароль")

class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh-токен")

class AuthTokensResponse(BaseModel):
    access_token: str = Field(..., description="JWT access-токен")
    refresh_token: str = Field(..., description="Opaque refresh-токен")
    token_type: str = Field("bearer", description="Тип токена")
    expires_in: int = Field(..., description="Время жизни access-токена в секундах")

class UserUsage(BaseModel):
    minutes_used: int = 0
    jobs_active: int = 0

class UserProfile(BaseModel):
    id: str
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    plan: str = "free"
    usage: UserUsage = Field(default_factory=UserUsage)

# схемы транскриптов
class TranscriptItem(BaseModel):
    id: str
    title: str
    created_at: datetime
    duration_sec: Optional[int] = None
    status: str
    tags: Optional[List[str]] = None

class TranscriptListResponse(BaseModel):
    total: int
    items: List[TranscriptItem]

class TagsUpdateRequest(BaseModel):
    tags: List[str]
