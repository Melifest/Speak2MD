import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, JSON, Text
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
