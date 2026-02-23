"""Bug-report submit cooldown helper logic."""

import math
from typing import Any


def submit_cooldown_remaining(last_submit_monotonic: Any, cooldown_seconds: Any, now_monotonic: Any) -> Any:
    """Return non-negative seconds remaining before next submit is allowed."""
    cooldown = int(cooldown_seconds or 0)
    if cooldown <= 0:
        return 0
    last_submit = float(last_submit_monotonic or 0.0)
    if last_submit <= 0:
        return 0
    now_val = float(now_monotonic)
    remaining = (last_submit + float(cooldown)) - now_val
    if remaining <= 0:
        return 0
    return int(math.ceil(remaining))


def mark_submit_now(now_monotonic: Any) -> Any:
    """Return normalized submit timestamp for owner state storage."""
    return float(now_monotonic)
