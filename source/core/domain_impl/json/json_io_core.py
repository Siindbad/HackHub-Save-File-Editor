"""Consolidated JSON domain pillar: json_io_core.

Contains merged logic from split JSON domain services.
"""


# --- Merged from document_io_service.py ---
"""Document I/O helpers for JSON and .hhsav data paths."""

import gzip
import json
import os
import tempfile
from typing import Any
from core.exceptions import AppRuntimeError


def load_document(path: Any) -> Any:
    """Load JSON-compatible document data from .json or .hhsav path."""
    use_path = str(path or "")
    if use_path.lower().endswith(".hhsav"):
        with gzip.open(use_path, "rb") as handle:
            raw = handle.read().decode("utf-8")
        return json.loads(raw)
    with open(use_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def build_pretty_json_payload(data: Any) -> Any:
    """Build UTF-8 text payload for normal Save operations."""
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def build_compact_json_bytes(data: Any) -> Any:
    """Build compact UTF-8 JSON bytes for .hhsav gzip export."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def export_hhsav_bytes(payload: Any, destination_path: Any, commit_file_fn: Any) -> Any:
    """Write compact JSON bytes into deterministic gzip container and commit."""
    use_destination = str(destination_path or "")
    if not use_destination:
        raise ValueError("Export destination path is required.")
    if not callable(commit_file_fn):
        raise ValueError("commit_file_fn is required.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        gzip_path = os.path.join(tmp_dir, "save.hhsav")
        with open(gzip_path, "wb") as raw_handle:
            with gzip.GzipFile(
                filename="",
                mode="wb",
                fileobj=raw_handle,
                compresslevel=9,
                mtime=0,
            ) as gz_handle:
                gz_handle.write(payload)
        if not os.path.isfile(gzip_path) or os.path.getsize(gzip_path) <= 0:
            raise AppRuntimeError("Exported .hhsav is empty.")
        commit_file_fn(gzip_path, use_destination)


# --- Merged from json_path_service.py ---
"""JSON path get/set helpers."""
from typing import Any


def get_value(root_value: Any, path: Any) -> Any:
    """Resolve nested value from root by path keys/indexes."""
    value = root_value
    for key in path:
        value = value[key]
    return value


def set_value(root_value: Any, path: Any, new_value: Any) -> Any:
    """Set nested value by path and return updated root value."""
    if not path:
        return new_value
    parent = root_value
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = new_value
    return root_value


# --- Merged from json_apply_commit_service.py ---
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


# --- Merged from json_edit_flow_service.py ---
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


# --- Merged from validation_service.py ---
"""Input validation helpers for clipboard paste and Apply Edit flows."""


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

__all__ = [name for name in globals() if not name.startswith("__")]
