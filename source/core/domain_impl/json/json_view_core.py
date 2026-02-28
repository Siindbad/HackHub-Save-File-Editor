"""Consolidated JSON domain pillar: json_view_core.

Contains merged logic from split JSON domain services.
"""


# --- Merged from json_error_highlight_render_service.py ---
"""JSON highlight renderer service."""
from typing import Any


# Rendering helpers keep Tk-tag application out of decision code.
def apply_json_error_highlight(owner: Any, exc: Any, line: Any, start_index: Any, end_index: Any, note: Any=None) -> Any:
    return owner._apply_json_error_highlight(exc, line, start_index, end_index, note=note)


def log_json_error(owner: Any, exc: Any, target_line: Any, note: Any="") -> Any:
    return owner._log_json_error(exc, target_line, note=note)


# --- Merged from json_view_render_service.py ---
"""JSON view rendering helpers for editor text widget flows."""

import json
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def show_value(owner: Any, value: Any, path: Any=None) -> Any:
    """Render selected JSON value and schedule deferred highlight passes."""
    owner._json_render_seq = int(getattr(owner, "_json_render_seq", 0) or 0) + 1
    render_seq = int(owner._json_render_seq)
    try:
        owner.text.configure(state="normal")
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        pass
    owner.text.delete("1.0", "end")
    try:
        rendered = json.dumps(value, indent=2, ensure_ascii=False)
    except TypeError:
        rendered = str(value)
    owner.text.insert("1.0", rendered)
    # Keep visible key highlights instant; defer heavier value-rule pass.
    owner._clear_json_lock_highlight()
    owner._set_json_text_editable(True)
    owner._apply_json_view_key_highlights(path, line_limit=initial_highlight_line_limit(owner))
    schedule_json_view_lock_state(owner, path, render_seq=render_seq)
    try:
        # Keep undo/redo scoped to the current node content.
        owner.text.edit_reset()
        owner.text.edit_modified(False)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        pass


def initial_highlight_line_limit(owner: Any) -> Any:
    """Estimate visible line window for fast-first highlight pass."""
    try:
        text_h = max(1, int(owner.text.winfo_height()))
        top_idx = str(owner.text.index("@0,0"))
        bottom_idx = str(owner.text.index(f"@0,{text_h}"))
        top_line = int(top_idx.split(".", 1)[0])
        bottom_line = int(bottom_idx.split(".", 1)[0])
        return max(80, int(bottom_line - top_line + 30))
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return 160


def cancel_pending_json_view_lock_state(owner: Any) -> Any:
    """Cancel any pending after-id for deferred JSON value highlight pass."""
    after_id = getattr(owner, "_json_lock_apply_after_id", None)
    owner._json_lock_apply_after_id = None
    if not after_id:
        return
    try:
        owner.root.after_cancel(after_id)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return


def schedule_json_view_lock_state(owner: Any, path: Any, render_seq: Any=None) -> Any:
    """Defer full lock/value highlight pass until idle to keep first paint responsive."""
    cancel_pending_json_view_lock_state(owner)
    snapshot_path = list(path or [])
    expected_seq = int(render_seq if render_seq is not None else getattr(owner, "_json_render_seq", 0) or 0)

    def _apply_pending():
        owner._json_lock_apply_after_id = None
        if int(getattr(owner, "_json_render_seq", 0) or 0) != expected_seq:
            return
        owner._apply_json_view_key_highlights(snapshot_path)
        owner._apply_json_view_value_highlights(snapshot_path)

    try:
        owner._json_lock_apply_after_id = owner.root.after_idle(_apply_pending)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        owner._json_lock_apply_after_id = None
        owner._apply_json_view_key_highlights(snapshot_path)
        owner._apply_json_view_value_highlights(snapshot_path)


# --- Merged from json_view_service.py ---
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)

NO_FILE_LOADED_MESSAGE = "No File Loaded. Open A .HHSAV File Before Continuing."


def show_json_no_file_message(text_widget: Any) -> Any:
    try:
        text_widget.delete("1.0", "end")
        text_widget.insert("1.0", NO_FILE_LOADED_MESSAGE)
        text_widget.edit_modified(False)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return

__all__ = [name for name in globals() if not name.startswith("__")]
