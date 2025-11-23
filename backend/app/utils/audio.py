import shutil
import subprocess
from pathlib import Path

def wav_duration_seconds(path: Path) -> float | None:
    try:
        import wave
        from contextlib import closing
        with closing(wave.open(str(path), "rb")) as w:
            frames = w.getnframes()
            rate = w.getframerate() or 0
            if rate > 0:
                return frames / float(rate)
            return None
    except Exception:
        return None

def convert_to_wav(input_path: Path, output_path: Path, sample_rate: int = 16000, timeout_sec: int = 60) -> Path:
    ffmpeg_cmd = None
    usr_bin_ffmpeg = Path("/usr/bin/ffmpeg")
    if usr_bin_ffmpeg.exists():
        ffmpeg_cmd = str(usr_bin_ffmpeg)
    else:
        ffmpeg_cmd = shutil.which("ffmpeg")
    if not ffmpeg_cmd:
        try:
            import imageio_ffmpeg
            ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            raise RuntimeError("FFmpeg not found")
    cmd = [
        ffmpeg_cmd,
        "-hide_banner",
        "-nostdin",
        "-y",
        "-i", str(input_path),
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-acodec", "pcm_s16le",
        str(output_path),
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"FFmpeg timeout after {timeout_sec}s")
    except Exception:
        raise RuntimeError("FFmpeg execution failed")
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg returned {proc.returncode}")
    return output_path
