import os
import logging
from typing import Optional
import requests

logger = logging.getLogger("speak2md")


def _base_url() -> str:
    # Возвращает базовый url сервера; по дефолу стоит LM Studio
    return os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1").rstrip("/")


def _model_name() -> str:
    # Возвращает название модели 
    return os.getenv("LLM_MODEL", "local-model")


def _api_key() -> Optional[str]:
    # API ключ (на всякий случай)
    return os.getenv("LLM_API_KEY")


def _timeout_seconds() -> float:
    # Таймаут HTTP-запроса к LLM (секунды)
    # По умолчанию до 240
    try:
        return float(os.getenv("LLM_TIMEOUT", "240"))
    except Exception:
        return 240.0


def generate_markdown(job_id: str, raw_text: str, language: str = "ru") -> str:
    # Запрос к LLM по нашей задаче
    url = f"{_base_url()}/chat/completions"
    headers = {
        "Content-Type": "application/json",
    }
    api_key = _api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Системный промпт
    system_prompt = (
        """[system]
    Режим: CleanRewrite для ru ASR → текст.

    Задача: принять сырой русский ASR-текст (оговорки, повторы, шумы, сбитая пунктуация) и выдать ОЧИЩЕННУЮ версию — связный литературный текст с минимальной структурой. Смысл не менять, факты не добавлять. Итоговый объём — ≥80% от исходного по символам (с пробелами). Если выходит <70%, разверни сокращённые места ИЗ исходника (перефразируй без новых фактов).

    Выход: только чистый, красивый конспект (Markdown допустим для заголовков/формул), без служебных метаданных и без JSON.

    Правила:
    - Сохраняй ≥80% содержания; порядок тем в целом — как в исходнике, фразы можно переставлять ради связности или объединять.
    - Удаляй речевой мусор: «ээ», «мм», повторы, самопоправления, междометия, пометки типа [шум]/[смех], пустые вводные («сейчас мы…»), если не несут смысла.
    - Восстанавливай пунктуацию, регистр, опечатки, согласование; используй «ёлочки», корректные тире, исправляй ошибки.
    - Термины, числа, единицы, формулы и примеры — сохраняй; десятичный разделитель — как в исходнике. Математику можно давать в инлайне `F = ma` или в блоке ```math … ```.
    - Таймкоды и имена говорящих убирай, если они не критичны для понимания.
    - Соблюдай основные русские типографские нормы (неразрывные пробелы — по возможности).
    - Никаких галлюцинаций: при неоднозначности сглаживай формулировки, не выдумывая данные.
    - Реклама: убирай ее если находишь в тексте (не относись к этому правилу слишком строго, если очевидно, что это реклама - убери ее).
    - Цельность: делай цельный, не разрозненный текст, по возможности струкурированными абзацами.

    Структура:
    - Один H1-заголовок (# …) с названием темы (выведи из контекста).
    - 2–3 H2-подзаголовков (## …), если темы явно просматриваются; иначе — связные абзацы без H2.
    - Абзацы: НЕ РАЗБИВАЙ КАЖДОЕ ПРЕДЛОЖЕНИЕ НОВОЙ СТРОКОЙ.

    Проверки перед выводом:
    1) Объём ≥80% от исходника.
    2) Нет списков/таблиц/оглавлений.
    3) Нет речевого мусора; пунктуация/регистр нормализованы.
    4) Формулы/числа/единицы сохранены; факты не искажены.

    Формат ввода: asr_text (строка с сырым распознанным текстом).
    Формат вывода: только очищенный текст (Markdown допустим для заголовков/формул), без префиксов, JSON, приветствий.
    """
    )

    user_prompt = (
        f"Язык: {language}.\n"
        "Сырой текст (ASR, без форматирования):\n\n"
        f"{raw_text}\n\n"
        "Задача: преобразуй в хорошо структурированный Markdown-текст. НЕ ПИШИ НИЧЕГО КРОМЕ ПРЕОБРАЗОВАННОГО ТЕКСТА"
    )

    payload = {
        "model": _model_name(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "20000")),
        "stream": False,
    }

    logger.info(
        "LLM request for job %s → %s (model=%s, max_tokens=%s, timeout=%ss)",
        job_id,
        url,
        payload.get("model"),
        payload.get("max_tokens"),
        _timeout_seconds(),
    )
    resp = requests.post(url, json=payload, headers=headers, timeout=_timeout_seconds())
    resp.raise_for_status()
    data = resp.json()

    # Основной путь: контент в message.content
    try:
        message = data.get("choices", [{}])[0].get("message", {})
        content = message.get("content")
    except Exception as e:
        logger.error("LLM response parsing failed for job %s: %s", job_id, e)
        raise

    # Фолбэк для reasoning-моделей: иногда финальный ответ попадает в reasoning_content
    if not isinstance(content, str) or not content.strip():
        reasoning_content = message.get("reasoning_content")
        if isinstance(reasoning_content, str) and reasoning_content.strip():
            logger.warning(
                "LLM returned empty content; using reasoning_content as fallback for job %s",
                job_id,
            )
            content = reasoning_content
        else:
            raise RuntimeError("LLM returned empty content")

    return content.strip()