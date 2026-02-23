"""JSON find-navigation helpers for cross-root tree traversal behavior."""
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def collapse_previous_find_root_if_category_changed(owner: Any, next_item_id: Any) -> Any:
    """Collapse previous root when Find Next jumps to a different top-level category."""
    tree_widget = getattr(owner, "tree", None)
    if tree_widget is None:
        return
    if not next_item_id:
        return
    try:
        if not tree_widget.winfo_exists():
            return
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return

    def _root_item(item_id):
        current = item_id
        if not current:
            return ""
        while True:
            try:
                parent = tree_widget.parent(current)
            except EXPECTED_ERRORS as exc:
                _LOG.debug('expected_error', exc_info=exc)
                return current
            if not parent:
                return current
            current = parent

    try:
        next_root = _root_item(next_item_id)
        previous_root = str(getattr(owner, "_find_last_root_item", "") or "")
        if previous_root and next_root and previous_root != next_root:
            tree_widget.item(previous_root, open=False)
        owner._find_last_root_item = next_root
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return
