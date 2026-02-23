from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)

def normalize_root_tree_key(value: Any) -> Any:
    return str(value).strip().casefold()


def tree_display_label_for_key(key: Any, tree_style_variant: Any, safe_display_labels: Any) -> Any:
    text = str(key)
    if str(tree_style_variant or "").upper() != "B":
        return text
    labels = safe_display_labels if isinstance(safe_display_labels, dict) else {}
    return labels.get(text, text)


def selected_tree_path_text(item_id: Any, item_to_path: Any) -> Any:
    path = None
    try:
        path = item_to_path.get(item_id, None)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        path = None
    if path is None:
        return "unknown"
    try:
        return repr(path)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return "unknown"


def format_path_for_display(path: Any) -> Any:
    parts = []
    for token in path:
        if isinstance(token, int):
            parts.append(f"[{token}]")
        else:
            if parts:
                parts.append(".")
            parts.append(str(token))
    return "".join(parts) if parts else "<value>"


def tree_item_can_toggle_from_value(path: Any, value: Any) -> Any:
    if isinstance(path, tuple) and path and path[0] == "__group__":
        return False
    return isinstance(value, (dict, list)) and len(value) > 0
