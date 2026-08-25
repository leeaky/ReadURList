from __future__ import annotations

from datetime import date


def should_send_digest(*, existing_run_on: date | None, today: date) -> bool:
    """True when no digest has been recorded for `today`."""
    return existing_run_on != today
