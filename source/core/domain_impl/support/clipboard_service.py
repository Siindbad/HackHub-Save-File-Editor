"""Clipboard helpers for Tk-root text copy flows."""
from typing import Any


def copy_text_to_clipboard(payload: Any, root: Any, expected_errors: Any) -> Any:
    """Copy non-empty text payload into root clipboard; return success bool."""
    text = str(payload or "").strip()
    if not text:
        return False
    if root is None:
        return False
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update_idletasks()
        return True
    except expected_errors:
        return False


def validate_clipboard_paste_payload(payload: Any, validate_text_fn: Any) -> tuple[bool, str, str]:
    """Validate clipboard text before inserting into editor text widget."""
    text = str(payload or "")
    if not text:
        return False, "", "Clipboard is empty."
    if callable(validate_text_fn):
        is_valid, reason = validate_text_fn(text)
        if not bool(is_valid):
            return False, "", str(reason or "Clipboard text is not allowed.")
    return True, text, ""
