import os, io, wave, struct, math, tempfile
from fastapi.testclient import TestClient

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

def test_upload_and_process_mock():
    audio = gen_wav(1)
    files = {"file": ("test.wav", audio, "audio/wav")}
    r = client.post("/api/upload", files=files)
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    # Имитируем работу воркера синхронно
    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        run_job(db, job)

    r2 = client.get(f"/api/status/{job_id}")
    assert r2.status_code == 200
    assert r2.json()["status"] == "ready"
    assert r2.json()["progress"] == 100

    r3 = client.get(f"/api/result/{job_id}?format=markdown")
    assert r3.status_code == 200
    assert "text/markdown" in r3.headers["content-type"]
