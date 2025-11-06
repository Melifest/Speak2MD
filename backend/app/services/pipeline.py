"""Сервис пайплайна: 
Здесь реализация аудио → текст → обработка → LLM → Markdown.
Ответственный Сергеев А.П.
"""

import os, json, logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from multiprocessing import Process
from pathlib import Path
import wave
from contextlib import closing
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

def _transcribe_whisper_to_file(
    wav_path: str,
    model_name: str,
    language: str,
    download_root: Optional[str],
    out_path: str,
) -> None:
    """В отдельном процессе: запуск Faster-Whisper и запись результата в файл.
    Логи из дочернего процесса опускаем, чтобы не блокировать основной поток.
    """
    text = ""
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=download_root)
        segments, _ = model.transcribe(
            wav_path,
            language=language,
            vad_filter=False,
        )
        text = " ".join([seg.text.strip() for seg in segments])
    except Exception:
        # Ошибки подавляем, в основном процессе обработаем пустой результат как фолбэк
        text = ""
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass

def _run_whisper_with_hard_timeout(
    job_id: str,
    wav_path: Path,
    model_name: str,
    timeout_sec: int,
    download_root: Optional[str],
    language: str,
) -> str:
    """Запуск Faster-Whisper в отдельном процессе с принудительным таймаутом.
    Если за timeout_sec не завершился — процесс завершается и возвращается пустая строка.
    """
    tmp_out = storage.job_dir(job_id) / "whisper_out.txt"
    try:
        if tmp_out.exists():
            tmp_out.unlink()
    except Exception:
        pass

    p = Process(
        target=_transcribe_whisper_to_file,
        args=(str(wav_path), model_name, language, download_root, str(tmp_out)),
    )
    p.daemon = True
    p.start()
    p.join(timeout_sec)

    if p.is_alive():
        logger.warning("ASR Faster-Whisper exceeded %ss timeout; terminating", timeout_sec)
        try:
            p.terminate()
        except Exception:
            pass
        p.join()
        return ""

    try:
        with open(tmp_out, "r", encoding="utf-8") as f:
            return (f.read() or "").strip()
    except Exception:
        return ""
    finally:
        try:
            tmp_out.unlink()
        except Exception:
            pass

def _estimate_wav_duration_sec(wav_path: Path) -> float | None:
    """Оценить длительность WAV-файла в секундах.
    Почему такое делаем - файлы могут быть разные, при аудио больше 30 мин все падало.
    """
    try:
        with closing(wave.open(str(wav_path), "rb")) as w:
            frames = w.getnframes()
            rate = w.getframerate() or 0
            if rate > 0:
                return frames / float(rate)
            return None
    except Exception:
        return None

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
        # Сначала PaddleSpeech, затем fallback на Faster-Whisper + добавим логи (дебаг)
        raw_text: str = ""
        use_paddlespeech = os.getenv("ENABLE_PADDLESPEECH", "false").lower() in {"1", "true", "yes", "on"}
        #базовый минимум таймаут (if звук короткий)
        base_asr_timeout = int(os.getenv("ASR_TIMEOUT_SEC", "60"))
        # масштабирование таймаута от длительности, по умолчанию ×3 от длины WAV
        duration_sec = _estimate_wav_duration_sec(wav_path)
        factor = float(os.getenv("ASR_TIMEOUT_FACTOR", "3.0"))
        if duration_sec is not None and duration_sec > 0:
            scaled = int(duration_sec * max(factor, 1.0))
            asr_timeout = max(base_asr_timeout, scaled)
        else:
            asr_timeout = base_asr_timeout
        download_root = os.getenv("WHISPER_CACHE_DIR") or os.getenv("DATA_DIR")
        model_name = os.getenv("WHISPER_MODEL", "tiny")
        # Если модель ещё не прогрета, покажем статус и выполним краткий прогрев
        try:
            sentinel = storage.DATA_DIR/".whisper_ready"
            if not sentinel.exists():
                update_task_progress(job_id, 65, "processing", "Скачиваем модель…")
                from faster_whisper import WhisperModel
                WhisperModel(model_name, device="cpu", compute_type="int8", download_root=download_root)
                try:
                    sentinel.write_text(model_name, encoding="utf-8")
                except Exception:
                    pass
        except Exception as e_warm:
            logger.warning("ASR model warm-up during job failed/skipped: %s", e_warm)

        def _run_paddlespeech() -> str:
            from paddlespeech.cli.asr.infer import ASRExecutor
            asr = ASRExecutor()
            return asr(audio_file=str(wav_path)) or ""

        def _run_whisper(model_name: str) -> str:
            from faster_whisper import WhisperModel
            model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=download_root)
            segments, info = model.transcribe(
                str(wav_path),
                language=os.getenv("LANGUAGE", "ru"),
                vad_filter=False,
            )
            return " ".join([seg.text.strip() for seg in segments])
        if use_paddlespeech:
            ex = ThreadPoolExecutor(max_workers=1)
            try:
                update_task_progress(job_id, 70, "processing", "ASR running (PaddleSpeech)")
                future = ex.submit(_run_paddlespeech)
                raw_text = future.result(timeout=asr_timeout)
            except FuturesTimeout:
                logger.warning("ASR PaddleSpeech timeout after %ss; falling back to Faster-Whisper", asr_timeout)
                try:
                    future.cancel()
                except Exception:
                    pass
                ex.shutdown(wait=False, cancel_futures=True)
                raw_text = ""
            except Exception as e_ps:
                logger.warning("ASR PaddleSpeech failed, trying Faster-Whisper fallback: %s", e_ps)
            finally:
                try:
                    ex.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    pass
        else:
            logger.info("PaddleSpeech disabled by config; using Faster-Whisper directly")

        if not raw_text:
            update_task_progress(job_id, 70, "processing", f"ASR running (Faster-Whisper {model_name})")
            raw_text = _run_whisper_with_hard_timeout(
                job_id,
                wav_path,
                model_name,
                asr_timeout,
                download_root,
                os.getenv("LANGUAGE", "ru"),
            )
            if not raw_text:
                logger.warning("ASR Faster-Whisper timeout or failure, using stub text")
                raw_text = "Распознавание не удалось (timeout), используем заглушку"
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