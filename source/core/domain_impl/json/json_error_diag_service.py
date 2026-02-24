"""JSON diagnostic note mapping and log writer service."""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from typing import Any
from core.exceptions import EXPECTED_ERRORS
_LOG = logging.getLogger(__name__)

_LOGGER = logging.getLogger(__name__)
_EXPECTED_DIAG_ERRORS = (
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    AttributeError,
    KeyError,
    IndexError,
    ImportError,
)


def _log_expected_diag_error(stage: str, exc: Exception) -> None:
    _LOGGER.debug(
        "json_error_diag.expected_error",
        extra={"stage": stage, "error_type": type(exc).__name__},
        exc_info=exc,
    )


def diag_system_from_note(note: object, is_symbol_error_note: Any = None) -> str:
    """Map a diagnostic note string to a stable log system bucket."""
    note_text = str(note or "").strip().lower()
    match note_text:
        case _ if note_text.startswith("locked_"):
            return "highlight_restore"
        case _ if note_text.startswith("overlay_"):
            return "overlay_parse"
        case _ if note_text.startswith("highlight_failed"):
            return "highlight_internal"
        case _ if note_text.startswith("cursor_restore"):
            return "cursor_restore"
        case _ if (
            note_text.startswith("spacing_")
            or note_text.startswith("missing_phone")
            or note_text.startswith("invalid_email")
        ):
            return "input_validation"
        case _ if note_text.startswith("symbol_"):
            return "symbol_recovery"
    # Older symbol diagnostics used `invalid_*`; keep them grouped with symbol recovery.
    if note_text.startswith("invalid_") and callable(is_symbol_error_note):
        try:
            if is_symbol_error_note(note_text):
                return "symbol_recovery"
        except _EXPECTED_DIAG_ERRORS as exc:
            _log_expected_diag_error("diag_system_from_note", exc)
    return "json_highlight"


def log_json_error(owner: Any, exc: Exception, target_line: object, note: str = "") -> None:
    """Append a normalized diagnostics entry to the runtime diagnostics log."""
    try:
        log_path = owner._diag_log_path()
        try:
            log_dir = os.path.dirname(str(log_path or ""))
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
        except _EXPECTED_DIAG_ERRORS as mkdir_exc:
            _log_expected_diag_error("ensure_log_dir", mkdir_exc)
        log_path_abs = os.path.abspath(log_path)
        for legacy_name in owner.LEGACY_DIAG_LOG_FILENAMES:
            legacy_path = os.path.join(tempfile.gettempdir(), str(legacy_name))
            if os.path.abspath(legacy_path) == log_path_abs:
                continue
            try:
                if os.path.isfile(legacy_path):
                    os.remove(legacy_path)
            except EXPECTED_ERRORS as exc:
                _LOG.debug('expected_error', exc_info=exc)
                pass
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = getattr(exc, "msg", str(exc))
        lineno = getattr(exc, "lineno", None)
        colno = getattr(exc, "colno", None)
        try:
            target_line = int(target_line)
        except (TypeError, ValueError, AttributeError):
            target_line = int(lineno or 1)
        target_line = max(1, target_line)
        diag_system = diag_system_from_note(
            note,
            is_symbol_error_note=getattr(owner, "_is_symbol_error_note", None),
        )
        diag_mode = str(getattr(owner, "_error_visual_mode", "") or "").strip()
        try:
            item_id = owner.tree.focus()
            selected_path = owner.item_to_path.get(item_id, None)
        except _EXPECTED_DIAG_ERRORS as tree_exc:
            _log_expected_diag_error("resolve_selected_path", tree_exc)
            selected_path = None
        path_text = repr(selected_path)
        context = []
        start = max(target_line - 2, 1)
        end = target_line + 2
        for ln in range(start, end + 1):
            try:
                text = owner.text.get(f"{ln}.0", f"{ln}.0 lineend")
            except _EXPECTED_DIAG_ERRORS as text_exc:
                _log_expected_diag_error("collect_context_line", text_exc)
                text = ""
            context.append(f"{ln}: {text}")
        entry = (
            "\n---\n"
            f"time={now} action={str(getattr(owner, '_diag_action', 'apply_edit:0'))}\n"
            f"msg={msg} lineno={lineno} col={colno} target={target_line} note={note}\n"
            f"system={diag_system} mode={diag_mode or '-'}\n"
            f"path={path_text}\n"
            + "\n".join(context).rstrip()
            + "\n"
        )
        try:
            owner._trim_text_file_for_append(
                log_path,
                owner.DIAG_LOG_MAX_BYTES,
                owner.DIAG_LOG_KEEP_BYTES,
            )
        except _EXPECTED_DIAG_ERRORS as trim_exc:
            _log_expected_diag_error("trim_dated_log", trim_exc)
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(entry)
        # Mirror write: keep one stable non-dated diagnostics file for local
        # visibility while retaining dated day-file logs for retention tooling.
        try:
            canonical_name = str(getattr(owner, "DIAG_LOG_FILENAME", "") or "").strip()
            if canonical_name:
                canonical_path = os.path.join(os.path.dirname(log_path), canonical_name)
                if os.path.abspath(canonical_path) != log_path_abs:
                    try:
                        owner._trim_text_file_for_append(
                            canonical_path,
                            owner.DIAG_LOG_MAX_BYTES,
                            owner.DIAG_LOG_KEEP_BYTES,
                        )
                    except _EXPECTED_DIAG_ERRORS as trim_exc:
                        _log_expected_diag_error("trim_canonical_log", trim_exc)
                    with open(canonical_path, "a", encoding="utf-8") as handle:
                        handle.write(entry)
        except _EXPECTED_DIAG_ERRORS as canonical_exc:
            _log_expected_diag_error("write_canonical_log", canonical_exc)
    except _EXPECTED_DIAG_ERRORS as write_exc:
        _log_expected_diag_error("write_diagnostics_log", write_exc)
        return
