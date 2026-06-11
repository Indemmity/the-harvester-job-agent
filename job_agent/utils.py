from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def clean_text(value: object | None) -> str:
    """Return a trimmed, single-spaced string representation."""
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        text = str(value)
    return " ".join(text.split()).strip()


def repair_mojibake(value: object | None) -> str:
    """Best-effort repair for common UTF-8/Latin-1 mojibake in source text."""
    text = clean_text(value)
    if not text:
        return ""
    if not any(marker in text for marker in ("Ã", "Â", "â")):
        return text

    candidates = [text]
    for encoding in ("latin-1", "cp1252"):
        try:
            repaired = text.encode(encoding).decode("utf-8")
        except (UnicodeError, UnicodeEncodeError):
            continue
        candidates.append(clean_text(repaired))

    def score(candidate: str) -> int:
        return sum(candidate.count(marker) for marker in ("Ã", "Â", "â"))

    return min(candidates, key=score)


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    """Normalize text values and keep the first occurrence of each item."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = clean_text(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_parent_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
