"""JSON edit flow helper logic for editor mode checks."""

import json
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def can_auto_apply_current_edit(owner: Any) -> Any:
    """Return True when current text content is valid for auto-apply flow."""
    item_id = owner.tree.focus()
    if not item_id:
        return False
    path = owner.item_to_path.get(item_id, [])
    if isinstance(path, tuple) and path and path[0] == "__group__":
        return False
    raw = owner.text.get("1.0", "end").strip()
    try:
        new_value = json.loads(raw)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return False
    if owner._find_invalid_email_in_value(path, new_value):
        return False
    if owner._find_phone_format_issue():
        return False
    if owner._find_json_spacing_issue():
        return False
    if not owner._is_json_edit_allowed(path, new_value, show_feedback=False):
        return False
    if not owner._is_edit_allowed(path, new_value):
        return False
    return True
