def render_markdown(transcript_text: str, meta: dict) -> str:
    title = str(meta.get("title") or meta.get("filename") or "Расшифровка").strip()
    text = str(transcript_text or "").strip()
    if not text:
        return f"# {title}\n\n"
    parts = [p.strip() for p in text.replace("\r", " ").split(". ") if p.strip()]
    body = "\n\n".join(parts) if parts else text
    return f"# {title}\n\n{body}"
