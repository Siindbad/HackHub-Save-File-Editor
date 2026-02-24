"""Input validation helpers for clipboard paste and Apply Edit flows."""

from __future__ import annotations

from typing import Any

from core import constants as app_constants


def _contains_disallowed_controls(text: str) -> bool:
    allowed = set(app_constants.EDITOR_ALLOWED_CONTROL_CHARS)
    for char in text:
        if ord(char) < 32 and char not in allowed:
            return True
    return False


def _contains_utf16_surrogate(text: str) -> bool:
    for char in text:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            return True
    return False


def _contains_hidden_unicode(text: str) -> bool:
    hidden = set(app_constants.EDITOR_HIDDEN_UNICODE_CHARS)
    return any(char in hidden for char in text)


def validate_editor_text_payload(payload: Any) -> tuple[bool, str]:
    """Validate text payload before it is inserted/parsed by editor flows."""
    text = str(payload or "")
    if not text:
        return True, ""
    limit = int(app_constants.EDITOR_INPUT_MAX_CHARS)
    if len(text) >= limit:
        return False, f"Input exceeds safety limit ({limit:,} characters)."
    if _contains_utf16_surrogate(text):
        return False, "Input contains non-UTF text code points."
    if _contains_disallowed_controls(text):
        return False, "Input contains unsupported binary control bytes."
    if _contains_hidden_unicode(text):
        return False, "Input contains hidden Unicode characters."
    return True, ""
