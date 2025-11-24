from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status

from ..db import SessionLocal
from ..models import User, Job, JobStatus, RefreshToken
from ..utils.security import get_current_admin

# Админ‑роутер: управление пользователями и задачами
router = APIRouter()


#список пользователе с фильтрами;
#поля ровно те, что нужны в панели: id/username/email/full_name/plan/role/is_active/created_at
@router.get("/admin/users")
def list_users(
    plan: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin=Depends(get_current_admin),
):
    with SessionLocal() as db:
        query = db.query(User)
        if plan:
            query = query.filter(User.plan == plan)
        if role:
            query = query.filter(User.role == role)
        if active is not None:
            query = query.filter(User.is_active == active)
        items = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
        if q:
            ql = str(q).lower()
            def match(u: User):
                return (
                    (u.username or "").lower().find(ql) != -1
                    or (u.email or "").lower().find(ql) != -1
                    or (u.full_name or "").lower().find(ql) != -1
                )
            items = [u for u in items if match(u)]
        return [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "plan": u.plan,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at,
            }
            for u in items
        ]


# получить одного пользователя карточкой)
@router.get("/admin/users/{user_id}")
def get_user(user_id: str, admin=Depends(get_current_admin)):
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "plan": u.plan,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }


# обновление полей: plan/role/is_active/full_name/email
@router.put("/admin/users/{user_id}")
def update_user(user_id: str, payload: dict, admin=Depends(get_current_admin)):
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        allowed = {"plan", "role", "is_active", "full_name", "email"}
        for k, v in (payload or {}).items():
            if k in allowed:
                setattr(u, k, v)
        db.add(u)
        db.commit()
        db.refresh(u)
        return {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "plan": u.plan,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }


# деактивировать пользователя
@router.post("/admin/users/{user_id}/deactivate")
def deactivate_user(user_id: str, admin=Depends(get_current_admin)):
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        u.is_active = False
        db.add(u)
        db.commit()
        return {"id": u.id, "is_active": u.is_active}


# активировать пользователя (is_active=true)
@router.post("/admin/users/{user_id}/activate")
def activate_user(user_id: str, admin=Depends(get_current_admin)):
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        u.is_active = True
        db.add(u)
        db.commit()
        return {"id": u.id, "is_active": u.is_active}


# принудительно разлогинить: revoke все refresh‑токены
@router.post("/admin/users/{user_id}/tokens/revoke")
def revoke_tokens(user_id: str, admin=Depends(get_current_admin)):
    with SessionLocal() as db:
        tokens = db.query(RefreshToken).filter(RefreshToken.user_id == user_id, RefreshToken.revoked == False).all()
        for t in tokens:
            t.revoked = True
            db.add(t)
        db.commit()
        return {"revoked": len(tokens)}


# список задач (фильтры по статусу/пользователю/диапазону дат);
# возвращаем самые базовые поля для таблицы
@router.get("/admin/jobs")
def list_jobs(
    status_q: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin=Depends(get_current_admin),
):
    with SessionLocal() as db:
        query = db.query(Job)
        if user_id:
            query = query.filter(Job.user_id == user_id)
        if status_q:
            try:
                s_val = JobStatus(status_q)
                query = query.filter(Job.status == s_val)
            except Exception:
                pass
        if since:
            try:
                dt = datetime.fromisoformat(since)
                query = query.filter(Job.created_at >= dt)
            except Exception:
                pass
        if until:
            try:
                dt = datetime.fromisoformat(until)
                query = query.filter(Job.created_at <= dt)
            except Exception:
                pass
        jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
        return [
            {
                "id": j.id,
                "user_id": j.user_id,
                "status": j.status.value if hasattr(j.status, "value") else str(j.status),
                "duration_seconds": j.duration_seconds,
                "created_at": j.created_at,
            }
            for j in jobs
        ]


# карточка одной задачи
@router.get("/admin/jobs/{job_id}")
def get_job(job_id: str, admin=Depends(get_current_admin)):
    with SessionLocal() as db:
        j = db.query(Job).filter(Job.id == job_id).first()
        if not j:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return {
            "id": j.id,
            "user_id": j.user_id,
            "status": j.status.value if hasattr(j.status, "value") else str(j.status),
            "duration_seconds": j.duration_seconds,
            "error_message": j.error_message,
            "created_at": j.created_at,
            "updated_at": j.updated_at,
        }


#удалить задачу, КАСКАДНО!! удалятся артефакты/события по настройкам моделей
@router.delete("/admin/jobs/{job_id}")
def delete_job(job_id: str, admin=Depends(get_current_admin)):
    with SessionLocal() as db:
        j = db.query(Job).filter(Job.id == job_id).first()
        if not j:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        db.delete(j)
        db.commit()
        return {"deleted": True}


#простая сводка по периоду (как usage, но по всем): users_total/minutes_total/jobs_total
@router.get("/admin/stats")
def stats(period: Optional[str] = Query(None), admin=Depends(get_current_admin)):
    with SessionLocal() as db:
        users_total = db.query(User).count()
        q = db.query(Job)
        jobs = q.all()
        if period:
            try:
                year_str, month_str = period.split("-", 1)
                year = int(year_str)
                month = int(month_str)
                start = datetime(year, month, 1)
                if month == 12:
                    end = datetime(year + 1, 1, 1)
                else:
                    end = datetime(year, month + 1, 1)
                jobs = [j for j in jobs if j.created_at >= start and j.created_at < end]
            except Exception:
                pass
        ready_jobs = [j for j in jobs if (j.status.value if hasattr(j.status, "value") else str(j.status)) == "ready"]
        total_seconds = sum(int(j.duration_seconds or 0) for j in ready_jobs)
        return {
            "users_total": users_total,
            "minutes_total": total_seconds // 60,
            "jobs_total": len(ready_jobs),
        }


#сводка по произвольному диапазону; можно сгруппировать по plan|status
@router.get("/admin/stats/range")
def stats_range(
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
    by: Optional[str] = Query(None),
    admin=Depends(get_current_admin),
):
    with SessionLocal() as db:
        q = db.query(Job)
        jobs = q.all()
        def in_range(dt: datetime) -> bool:
            ok = True
            if since:
                try:
                    ok = ok and (dt >= datetime.fromisoformat(since))
                except Exception:
                    pass
            if until:
                try:
                    ok = ok and (dt <= datetime.fromisoformat(until))
                except Exception:
                    pass
            return ok
        jobs = [j for j in jobs if in_range(j.created_at)]
        ready_jobs = [j for j in jobs if (j.status.value if hasattr(j.status, "value") else str(j.status)) == "ready"]
        if by == "plan":
            users = {u.id: u for u in db.query(User).all()}
            agg = {}
            for j in ready_jobs:
                plan = (users.get(j.user_id).plan if users.get(j.user_id) else "unknown")
                agg.setdefault(plan, {"minutes": 0, "jobs": 0})
                agg[plan]["minutes"] += int(j.duration_seconds or 0) // 60
                agg[plan]["jobs"] += 1
            return agg
        if by == "status":
            agg = {}
            for j in jobs:
                s = j.status.value if hasattr(j.status, "value") else str(j.status)
                agg.setdefault(s, {"minutes": 0, "jobs": 0})
                agg[s]["minutes"] += int(j.duration_seconds or 0) // 60
                agg[s]["jobs"] += 1
            return agg
        total_seconds = sum(int(j.duration_seconds or 0) for j in ready_jobs)
        return {"minutes_total": total_seconds // 60, "jobs_total": len(ready_jobs)}
