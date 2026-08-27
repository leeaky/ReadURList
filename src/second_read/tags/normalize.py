from __future__ import annotations

import re
from typing import Sequence

_DASHES = dict.fromkeys(
    map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\ufe63\uff0d"),
    "-",
)
_WS = re.compile(r"\s+")


def _fold(raw: str) -> str:
    text = (raw or "").translate(_DASHES)
    return _WS.sub(" ", text).strip()


def canonicalize_label(raw: str, existing: Sequence[str]) -> str:
    folded = _fold(raw if isinstance(raw, str) else "")
    if not folded:
        return ""
    key = folded.lower()
    for item in existing:
        candidate = _fold(item)
        if candidate.lower() == key:
            return item.strip() if isinstance(item, str) else folded
    return folded


def should_consolidate(*, ready_count: int, unique_subjects: int) -> bool:
    if ready_count < 8:
        return False
    return unique_subjects / ready_count > 0.5
