"""INPUT-mode diagnostics logging helpers."""

import os
from datetime import datetime
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def log_input_mode_edit_issue(owner: Any, path: Any, exc: Any) -> Any:
    """Capture invalid INPUT field/path writes for support triage."""
    try:
        log_path = owner._diag_log_path()
        owner._trim_text_file_for_append(log_path, owner.DIAG_LOG_MAX_BYTES, owner.DIAG_LOG_KEEP_BYTES)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            "\n---\n"
            f"time={stamp}\n"
            "context=input_apply_failure\n"
            f"action={str(getattr(owner, '_diag_action', 'apply_edit:0'))}\n"
            f"path={repr(list(path or []))}\n"
            f"error={type(exc).__name__}: {str(exc).strip()}\n"
        )
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(entry)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return


def log_input_mode_apply_result(owner: Any, path: Any, changed: Any) -> Any:
    """Log whether INPUT apply actually changed the target value."""
    try:
        log_path = owner._diag_log_path()
        owner._trim_text_file_for_append(log_path, owner.DIAG_LOG_MAX_BYTES, owner.DIAG_LOG_KEEP_BYTES)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            "\n---\n"
            f"time={stamp}\n"
            "context=input_apply_result\n"
            f"action={str(getattr(owner, '_diag_action', 'apply_edit:0'))}\n"
            f"path={repr(list(path or []))}\n"
            f"changed={'true' if bool(changed) else 'false'}\n"
        )
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(entry)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return


def log_input_mode_apply_trace(owner: Any, stage: Any, path: Any, specs_count: Any, changed: Any=None) -> Any:
    """Optionally log INPUT apply branch trace when env toggle is enabled."""
    raw = str(os.environ.get("HACKHUB_INPUT_APPLY_TRACE", "0")).strip().lower()
    if raw not in ("1", "true", "yes", "on"):
        return
    try:
        log_path = owner._diag_log_path()
        owner._trim_text_file_for_append(log_path, owner.DIAG_LOG_MAX_BYTES, owner.DIAG_LOG_KEEP_BYTES)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line_changed = ""
        if changed is not None:
            line_changed = f"changed={'true' if bool(changed) else 'false'}\n"
        entry = (
            "\n---\n"
            f"time={stamp}\n"
            "context=input_apply_trace\n"
            f"action={str(getattr(owner, '_diag_action', 'apply_edit:0'))}\n"
            f"stage={str(stage or '').strip()}\n"
            f"path={repr(list(path or []))}\n"
            f"specs={int(specs_count or 0)}\n"
            f"{line_changed}"
        )
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(entry)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return
