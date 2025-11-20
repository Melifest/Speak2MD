import io, wave, struct, math
from datetime import datetime
from fastapi.testclient import TestClient
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["DATA_DIR"] = "./tmp_data"
os.environ["MOCK_PIPELINE"] = "true"

from app.main import app
from app.db import Base, engine, SessionLocal
from app.models import Job
from app.services.pipeline import run_job

Base.metadata.create_all(bind=engine)
client = TestClient(app)

def gen_wav(duration_sec=1, samplerate=8000, freq=440.0):
    nframes = int(duration_sec * samplerate)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(samplerate)
        for i in range(nframes):
            val = int(32767.0 * 0.3 * math.sin(2*math.pi*freq * i / samplerate))
            w.writeframesraw(struct.pack('<h', val))
    return buf.getvalue()

def register_and_login(username="planuser"):
    client.post("/api/auth/register", json={"username": username, "password": "StrongPassw0rd!"})  # базовый минимум (юзер)
    r = client.post("/api/auth/login", json={"username": username, "password": "StrongPassw0rd!"})
    assert r.status_code == 200
    return r.json()["access_token"]

def test_plans_endpoint():
    r = client.get("/api/plans")  # справочник тарифов
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) == 3
    ids = {p["id"] for p in data}
    assert ids == {"free", "pro", "team"}

def test_change_plan_and_usage():
    token = register_and_login("planuser2")
    r = client.post("/api/subscription/change-plan", json={"plan": "pro"}, headers={"Authorization": f"Bearer {token}"})  # меняем тариф
    assert r.status_code == 200
    assert r.json()["plan"] == "pro"

    audio = gen_wav(1)  #короткий звук, чтобы быстро
    files = {"file": ("test.wav", audio, "audio/wav")}
    r2 = client.post("/api/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    job_id = r2.json()["job_id"]

    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        run_job(db, job)
        job.duration_seconds = 120
        job.created_at = datetime.utcnow()
        db.add(job)
        db.commit()

    period = datetime.utcnow().strftime("%Y-%m")
    r3 = client.get(f"/api/usage?period={period}", headers={"Authorization": f"Bearer {token}"})  # usage на месяц
    assert r3.status_code == 200
    usage = r3.json()
    assert usage["period"] == period
    assert usage["minutes_used"] >= 2
    assert usage["jobs_total"] >= 1