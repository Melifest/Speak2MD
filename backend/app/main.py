import os
import logging
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from prometheus_fastapi_instrumentator import Instrumentator
from .services import storage
from .db import Base, engine

from .routes.upload import router as upload_router
from .routes.status import router as status_router
from .routes.result import router as result_router
from .routes.ws import router as ws_router

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("speak2md")

app = FastAPI(title="Speak2MD API", version="0.1.0")

# CORS (пока простая конфигурация для MVP)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Маршруты API
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(status_router, prefix="/api", tags=["status"])
app.include_router(result_router, prefix="/api", tags=["result"])
app.include_router(ws_router, prefix="/api", tags=["ws"])

# метрики (добавляем middleware до старта приложения)
Instrumentator().instrument(app).expose(app)

# Статика (пока простой фронт)
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")

@app.on_event("startup")
def on_startup():
    # Инициализация бд, создаём таблицы, if нет + базовый лог
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("DB initialized. Speak2MD started. DATA_DIR=%s", storage.DATA_DIR)
    except Exception as e:
        logger.exception("DB initialization failed: %s", e)
        # продолжаем старт, но загрузка/обработка может упасть при использовании БД
        logger.warning("Continuing without confirmed DB init; uploads may fail.")

    # Фоновый прогрев модели ASR — не блокируем старт приложения и /health (заколебал залипать уже)
    def _background_warmup():
        try:
            model_name = os.getenv("WHISPER_MODEL", "tiny")
            download_root = os.getenv("WHISPER_CACHE_DIR") or os.getenv("DATA_DIR")
            from faster_whisper import WhisperModel
            logger.info(
                "ASR warm-up (background): initializing WhisperModel('%s'), download_root=%s",
                model_name,
                download_root,
            )
            WhisperModel(model_name, device="cpu", compute_type="int8", download_root=download_root)
            try:
                (storage.DATA_DIR/".whisper_ready").write_text(model_name, encoding="utf-8")
            except Exception:
                pass
            logger.info("ASR warm-up completed for model '%s'", model_name)
        except Exception as e:
            logger.warning("ASR warm-up skipped/failed: %s", e)

    try:
        sentinel = storage.DATA_DIR/".whisper_ready"
        if not sentinel.exists():
            threading.Thread(target=_background_warmup, daemon=True).start()
            logger.info("ASR warm-up scheduled in background")
    except Exception as e:
        logger.warning("ASR warm-up scheduling failed: %s", e)

@app.get("/health", response_class=HTMLResponse)
def health():
    return "<pre>OK</pre>"

@app.get("/", response_class=HTMLResponse)
def index():
    """Выдать фронт index.html на корневом маршруте."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return HTMLResponse("<pre>Index not found</pre>", status_code=404)
