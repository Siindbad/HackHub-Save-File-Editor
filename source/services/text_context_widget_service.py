"""Text-context widget relationship helpers."""
from typing import Any


def is_popup_child(widget: Any, popup: Any) -> Any:
    """Return True when widget path is popup or descendant of popup path."""
    if widget is None or popup is None:
        return False
    widget_path = str(widget)
    popup_path = str(popup)
    return widget_path == popup_path or widget_path.startswith(popup_path + ".")
