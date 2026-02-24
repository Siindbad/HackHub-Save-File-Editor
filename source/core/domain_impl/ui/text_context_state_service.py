"""Text-context menu state helper functions."""
from typing import Any


def has_text_selection(text_widget: Any, expected_errors: Any) -> Any:
    """Return True when editor selection tag has ranges."""
    try:
        return bool(text_widget.tag_ranges("sel"))
    except expected_errors:
        return False


def clipboard_has_text(root: Any, expected_errors: Any) -> Any:
    """Return True when clipboard has non-empty text."""
    try:
        value = root.clipboard_get()
    except expected_errors:
        return False
    return bool(value)


def text_can_undo(text_widget: Any, expected_errors: Any) -> Any:
    """Return True when Tk edit stack can undo."""
    try:
        return bool(int(text_widget.tk.call(text_widget._w, "edit", "canundo")))
    except expected_errors:
        return False


def text_can_redo(text_widget: Any, expected_errors: Any) -> Any:
    """Return True when Tk edit stack can redo."""
    try:
        return bool(int(text_widget.tk.call(text_widget._w, "edit", "canredo")))
    except expected_errors:
        return False
