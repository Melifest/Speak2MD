"""Сервис пайплайна: 
Здесь реализация аудио → текст → обработка → LLM → Markdown.
Ответственный Сергеев А.П.
"""

import os, json, logging
from pathlib import Path
from typing import Optional
from . import storage
from .audio_converter import convert_to_wav_16k_mono
from ..shared_storage import update_task_progress
from ..models import Job, JobStatus
logger = logging.getLogger("speak2md")

def _write_text_artifacts(job_id: str, text: str) -> tuple[Path, Path]:
    base_dir = storage.job_dir(job_id)
    md_path = base_dir/"result.md"
    json_path = base_dir/"transcript.json"
    md_content = f"# Расшифровка\n\n{text}\n"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"text": text}, f, ensure_ascii=False, indent=2)
    return md_path, json_path

def _write_markdown_artifacts(job_id: str, markdown: str, raw_text: Optional[str] = None) -> tuple[Path, Path]:
    base_dir = storage.job_dir(job_id)
    md_path = base_dir/"result.md"
    json_path = base_dir/"transcript.json"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    payload = {"markdown": markdown}
    if raw_text is not None:
        payload["text"] = raw_text
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return md_path, json_path

def _run_mock_pipeline(job_id: str, wav_path: Path) -> tuple[Path, Path]:
    # простой локальный мок, герерит текст и артефакты
    update_task_progress(job_id, 40, "processing", "Speech recognition (mock)")
    text = "Это мок-результат локальной обработки аудио."
    update_task_progress(job_id, 80, "processing", "Structuring content (mock)")
    md_path, json_path = _write_text_artifacts(job_id, text)
    return md_path, json_path

def _run_real_pipeline(job_id: str, wav_path: Path) -> tuple[Path, Path]:
    # реальный локальный пайплайн: Silero VAD + PaddleSpeech ASR + LLM постпроцессинг
    # при ошибке откатится на мок
    try:
        # Временно отключаем VAD (избегаем нестабильностей numpy/torch на Windows)
        update_task_progress(job_id, 30, "processing", "Skipping VAD")
        speech_timestamps = []

        update_task_progress(job_id, 60, "processing", "ASR loading")
        # Сначала пробуем PaddleSpeech, затем fallback на Faster-Whisper (CTranslate2)
        raw_text: str = ""
        try:
            from paddlespeech.cli.asr.infer import ASRExecutor
            asr = ASRExecutor()
            update_task_progress(job_id, 70, "processing", "ASR running (PaddleSpeech)")
            # для mvp пока распознаём целиком, без нарезки по vad сегментам
            raw_text = asr(audio_file=str(wav_path)) or ""
        except Exception as e_ps:
            logger.warning("ASR PaddleSpeech failed, trying Faster-Whisper fallback: %s", e_ps)
            try:
                from faster_whisper import WhisperModel
                model_name = os.getenv("WHISPER_MODEL", "base")
                update_task_progress(job_id, 70, "processing", f"ASR running (Faster-Whisper {model_name})")
                # CPU-only, avoid numpy/torch instability on Windows
                model = WhisperModel(model_name, device="cpu", compute_type="int8")
                segments, info = model.transcribe(
                    str(wav_path),
                    language=os.getenv("LANGUAGE", "ru"),
                    vad_filter=False,
                )
                raw_text = " ".join([seg.text.strip() for seg in segments])
            except Exception as e_w:
                logger.warning("ASR Faster-Whisper failed, using stub text: %s", e_w)
                raw_text = "Распознавание не удалось, используем заглушку"
        # Постпроцессинг через LLM (LM Studio на http://127.0.0.1:1234)
        try:
            from .llm_client import generate_markdown
            update_task_progress(job_id, 80, "processing", "LLM post-processing")
            markdown = generate_markdown(job_id, raw_text, language=os.getenv("LANGUAGE", "ru"))
            md_path, json_path = _write_markdown_artifacts(job_id, markdown, raw_text)
        except Exception as e:
            logger.warning("LLM post-processing failed, applying simple Markdown fallback: %s", e)
            # Простой структуризатор: заголовок и абзацы по предложениям
            title = (raw_text.strip().split(". ")[0] or "Расшифровка").strip()
            title = (title[:60] + "…") if len(title) > 60 else title
            paragraphs = [p.strip() for p in raw_text.split(". ") if p.strip()]
            body = "\n\n".join(paragraphs) if paragraphs else raw_text
            markdown = f"# {title}\n\n{body}"
            md_path, json_path = _write_markdown_artifacts(job_id, markdown, raw_text)
        return md_path, json_path
    except Exception as e:
        logger.exception("Real pipeline failed, switching to mock: %s", e)
        return _run_mock_pipeline(job_id, wav_path)


def run_job(db, job: Job) -> None:
    # конвертируем входной файл в WAV 16k mono
    # запускаем мок/реальный пайплайн
    # обновляем прогресс и запись в БД
    # сохраняем артефакты и выставляем статус ready
    try:
        job.status = JobStatus.processing
        job.progress = 0
        db.add(job)
        db.commit()

        update_task_progress(job.id, 5, "processing", "Preparing audio")
        base_dir: Path = storage.job_dir(job.id)
        original = next(base_dir.glob("original.*"), None)
        if not original:
            raise RuntimeError("Original file not found")

        wav_path = base_dir / "audio16k.wav"
        ffmpeg_timeout = int(os.getenv("FFMPEG_TIMEOUT_SEC", "600"))
        convert_to_wav_16k_mono(original, wav_path, timeout_sec=ffmpeg_timeout)
        update_task_progress(job.id, 20, "processing", "Audio converted")

        use_mock = os.getenv("MOCK_PIPELINE", "false").lower() in {"1", "true", "yes"}
        if use_mock:
            md_path, json_path = _run_mock_pipeline(job.id, wav_path)
        else:
            md_path, json_path = _run_real_pipeline(job.id, wav_path)

        job.result_md_path = str(md_path)
        job.result_json_path = str(json_path)
        job.progress = 100
        job.status = JobStatus.ready
        db.add(job)
        db.commit()

        update_task_progress(job.id, 100, "ready", "Task completed")
        logger.info("Job %s completed: %s", job.id, md_path)
    except Exception as e:
        logger.exception("Job %s failed: %s", job.id, e)
        job.status = JobStatus.error
        job.error_message = str(e)
        job.progress = 0
        db.add(job)
        db.commit()
        update_task_progress(job.id, 0, "error", f"Job failed: {e}")