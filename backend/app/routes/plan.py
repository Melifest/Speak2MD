from fastapi import APIRouter, HTTPException, status, Header, Query
from datetime import datetime
from calendar import monthrange
from ..db import SessionLocal
from ..models import User, Job, JobStatus
from ..utils.security import get_current_user
from ..schemas import UserProfile

router = APIRouter()

#планы и usage, пока так
PLANS = [
    {"id": "free", "name": "Free", "minutes_per_month": 60},
    {"id": "pro", "name": "Pro", "minutes_per_month": 500},
    {"id": "team", "name": "Team", "minutes_per_month": 2000},
]
ALLOWED = {"free", "pro", "team"}

@router.get("/plans")
def get_plans():
    return PLANS# статический справочник, на фронт пойдет

@router.post("/subscription/change-plan", response_model=UserProfile)
def change_plan(payload: dict, authorization: str = Header(None)):
    user = get_current_user(authorization)# кто меняет план
    plan = (payload or {}).get("plan")#новый план
    if plan not in ALLOWED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan")  # не ругаемся долго
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == user.id).first() #берём пользователя из бд
        if not u:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        u.plan = plan  #охраняем новый тариф
        db.add(u)
        db.commit()
        db.refresh(u)
        return UserProfile(
            id=u.id,
            username=u.username,
            full_name=u.full_name,
            email=u.email,
            plan=u.plan,
        )

@router.get("/usage")
def get_usage(period: str = Query(...), authorization: str = Header(None)):
    user = get_current_user(authorization)
    try:
        year_str, month_str = period.split("-", 1)
        year = int(year_str)
        month = int(month_str)
        last_day = monthrange(year, month)[1]
        start = datetime(year, month, 1) #начало месяца
        end = datetime(year, month, last_day, 23, 59, 59)  #конец месяца включительно
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid period format")  # формат yyyy-mm
    with SessionLocal() as db:
        q = db.query(Job).filter(Job.user_id == user.id)
        # фильтруем по периоду и только готовые
        jobs = [
            j for j in q.all()
            if j.created_at >= start and j.created_at <= end
            and (j.status.value if hasattr(j.status, "value") else str(j.status)) == "ready"
        ]
        total_seconds = sum(int(j.duration_seconds or 0) for j in jobs)
        minutes_used = total_seconds // 60
        jobs_total = len(jobs)
        return {"period": period, "minutes_used": minutes_used, "jobs_total": jobs_total}#фронту хватает