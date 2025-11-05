import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
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

@app.get("/health", response_class=HTMLResponse)
def health():
    return "<pre>OK</pre>"
