import uuid
from fastapi import HTTPException, status

def validate_job_id(job_id: str) -> str:
    if not job_id or not job_id.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Job ID cannot be empty")
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid job ID format")
    return job_id.strip()
