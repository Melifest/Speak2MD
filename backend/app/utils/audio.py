from pathlib import Path

"""Утилиты аудио -0 пока каркас без реальной обработки.
Реальную работу с аудио/ffmpeg добавить в рамках проекта.
"""

def ffprobe_duration_seconds(path: Path) -> int | None:
    """Заглушка: определить длительность аудио файла.
    реализовано на месте, позже перенести сюда
    Возвращает None. Реализация должна использовать доступные нам инструменты.
    """
    raise NotImplementedError("audio.ffprobe_duration_seconds is not implemented in skeleton")


def convert_to_wav(input_path: Path, output_path: Path, sample_rate: int = 16000):
    """Заглушка: конвертация аудио в WAV.
    реализовано на месте, позже перенести сюда
    Реализация должна использовать ffmpeg или аналог. Пока  заглушка.
    """
    raise NotImplementedError("audio.convert_to_wav is not implemented in skeleton")
