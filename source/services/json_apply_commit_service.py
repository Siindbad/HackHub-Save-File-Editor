"""Commit helpers for successful JSON edits."""
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def commit_json_edit(owner: Any, item_id: Any, path: Any, new_value: Any) -> Any:
    """Commit edit and refresh node visuals."""
    owner._set_value(path, new_value)
    owner._populate_children(item_id)
    owner._apply_json_view_lock_state(path)
    pending_restore = str(getattr(owner, "_pending_insert_restore_index", "") or "")
    owner._pending_insert_restore_index = ""
    if pending_restore:
        try:
            if getattr(owner, "root", None) is not None:
                owner.root.after_idle(lambda idx=pending_restore: owner._restore_insert_index(idx, log_failure=True))
            else:
                owner._restore_insert_index(pending_restore, log_failure=True)
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            pass
    owner._auto_apply_pending = False
    owner._auto_apply_in_progress = False
    owner.set_status("Edited")
