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
