import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, JSON, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from .db import Base

def uuidpk():
    return str(uuid.uuid4())

class JobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    ready = "ready"
    error = "error"

class ArtifactType(str, enum.Enum):
    input = "input"
    intermediate = "intermediate"
    result = "result"

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, default=uuidpk)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.processing)
    progress = Column(Integer, nullable=False, default=0)
    original_filename = Column(String, nullable=True)
    content_type = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    result_md_path = Column(String, nullable=True)
    result_json_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    artifacts = relationship("Artifact", back_populates="job", cascade="all, delete-orphan")
    events = relationship("JobEvent", back_populates="job", cascade="all, delete-orphan")

class Artifact(Base):
    __tablename__ = "artifacts"
    id = Column(String, primary_key=True, default=uuidpk)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    type = Column(Enum(ArtifactType), nullable=False, default=ArtifactType.input)
    path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="artifacts")

class JobEvent(Base):
    __tablename__ = "job_events"
    id = Column(String, primary_key=True, default=uuidpk)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="events")

# юзер  для аутентификации и профиля
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=uuidpk)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True) # возможно на будущее, сейчас используем username
    plan = Column(String, nullable=False, default="free")
    role = Column(String, nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

# хранилище рефреш-токенов (opaque), в БД только хеш
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(String, primary_key=True, default=uuidpk)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    replaced_by = Column(String, nullable=True)

    user = relationship("User", back_populates="refresh_tokens")
