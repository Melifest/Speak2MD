import os

class Settings:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DATA_DIR = os.getenv("DATA_DIR", "./data")
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@db:5432/postgres")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "local-model")
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "20000"))
    LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "240"))
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
    WHISPER_CACHE_DIR = os.getenv("WHISPER_CACHE_DIR")
    ASR_TIMEOUT_SEC = int(os.getenv("ASR_TIMEOUT_SEC", "60"))
    ASR_TIMEOUT_FACTOR = float(os.getenv("ASR_TIMEOUT_FACTOR", "3.0"))
    FFMPEG_TIMEOUT_SEC = int(os.getenv("FFMPEG_TIMEOUT_SEC", "600"))
    LANGUAGE = os.getenv("LANGUAGE", "ru")
    MOCK_PIPELINE = os.getenv("MOCK_PIPELINE", "false")
    POLL_INTERVAL_SEC = float(os.getenv("POLL_INTERVAL_SEC", "2.0"))

    # JWT / Auth настройки
    JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-prod")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRES_SECONDS = int(os.getenv("ACCESS_TOKEN_EXPIRES_SECONDS", "3600"))
    REFRESH_TOKEN_EXPIRES_SECONDS = int(os.getenv("REFRESH_TOKEN_EXPIRES_SECONDS", "2592000"))  # 30 дней
    JWT_ISSUER = os.getenv("JWT_ISSUER", "speak2md")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "speak2md-users")

settings = Settings()
