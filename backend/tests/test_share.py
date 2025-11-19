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

def register_and_login():
    client.post("/api/auth/register", json={"username": "u1", "password": "StrongPassw0rd!"})
    r = client.post("/api/auth/login", json={"username": "u1", "password": "StrongPassw0rd!"})
    assert r.status_code == 200
    return r.json()["access_token"]

def test_share_flow():
    token = register_and_login()
    audio = gen_wav(1)
    files = {"file": ("test.wav", audio, "audio/wav")}
    r = client.post("/api/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    job_id = r.json()["job_id"]

    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        run_job(db, job)

    r2 = client.post(f"/api/share/{job_id}", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    url = r2.json()["url"]
    share_token = url.split("/")[-1]

    r3 = client.get(f"/api/share/{share_token}?format=markdown")
    assert r3.status_code == 200
    assert "text/markdown" in r3.headers.get("content-type", "")

    r4 = client.delete(f"/api/share/{share_token}", headers={"Authorization": f"Bearer {token}"})
    assert r4.status_code == 200
    assert r4.json().get("revoked") is True

    r5 = client.get(f"/api/share/{share_token}?format=markdown")
    assert r5.status_code == 404