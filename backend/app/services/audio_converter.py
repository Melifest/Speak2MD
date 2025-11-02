import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("speak2md")

def convert_to_wav_16k_mono(input_path: Path, output_path: Path, timeout_sec: int = 60) -> Path:
    ''' Конвертирует любой поддерживаемый входной файл в WAV 16kHz mono.
    Использует системный ffmpeg. Логи ошибок пишутся в общий логгер.
    return - путь к вывходному файлу
    '''
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-y",
        "-i", str(input_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-acodec", "pcm_s16le",
        str(output_path),
    ]

    logger.info("FFmpeg convert start: %s -> %s", input_path, output_path)
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        logger.error("FFmpeg timeout after %ss for %s: %s", timeout_sec, input_path, e)
        raise RuntimeError(f"FFmpeg timeout after {timeout_sec}s")
    except Exception as e:
        logger.exception("FFmpeg failed to start for %s", input_path)
        raise RuntimeError("FFmpeg execution failed")

    if proc.returncode != 0:
        logger.error(
            "FFmpeg error (code %s) converting %s:\nSTDOUT:\n%s\nSTDERR:\n%s",
            proc.returncode,
            input_path,
            proc.stdout,
            proc.stderr,
        )
        raise RuntimeError(f"FFmpeg returned {proc.returncode}")

    logger.info("FFmpeg convert done: %s", output_path)
    return output_path