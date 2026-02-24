"""Latest-release metadata parsing helpers."""

import json
from typing import Any
from core.exceptions import AppRuntimeError


def parse_latest_release_info(raw_bytes: Any) -> Any:
    """Parse and validate latest-release API response payload."""
    try:
        parsed = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as exc:
        raise AppRuntimeError("No release info available.") from exc
    if not isinstance(parsed, dict):
        raise AppRuntimeError("No release info available.")
    return parsed
