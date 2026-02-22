"""JSON diagnostic note mapping and log writer service."""

import os
import tempfile
from datetime import datetime


def diag_system_from_note(note, is_symbol_error_note=None):
    """Map a diagnostic note string to a stable log system bucket."""
    note_text = str(note or "").strip().lower()
    if note_text.startswith("locked_"):
        return "highlight_restore"
    if note_text.startswith("overlay_"):
        return "overlay_parse"
    if note_text.startswith("highlight_failed"):
        return "highlight_internal"
    if note_text.startswith("cursor_restore"):
        return "cursor_restore"
    if (
        note_text.startswith("spacing_")
        or note_text.startswith("missing_phone")
        or note_text.startswith("invalid_email")
    ):
        return "input_validation"
    if note_text.startswith("symbol_"):
        return "symbol_recovery"
    # Older symbol diagnostics used `invalid_*`; keep them grouped with symbol recovery.
    if note_text.startswith("invalid_") and callable(is_symbol_error_note):
        try:
            if is_symbol_error_note(note_text):
                return "symbol_recovery"
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            pass
    return "json_highlight"


def log_json_error(owner, exc, target_line, note=""):
    """Append a normalized diagnostics entry to the runtime diagnostics log."""
    try:
        log_path = owner._diag_log_path()
        try:
            log_dir = os.path.dirname(str(log_path or ""))
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
        except Exception:
            pass
        log_path_abs = os.path.abspath(log_path)
        for legacy_name in owner.LEGACY_DIAG_LOG_FILENAMES:
            legacy_path = os.path.join(tempfile.gettempdir(), str(legacy_name))
            if os.path.abspath(legacy_path) == log_path_abs:
                continue
            try:
                if os.path.isfile(legacy_path):
                    os.remove(legacy_path)
            except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                pass
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = getattr(exc, "msg", str(exc))
        lineno = getattr(exc, "lineno", None)
        colno = getattr(exc, "colno", None)
        try:
            target_line = int(target_line)
        except Exception:
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
        except Exception:
            selected_path = None
        path_text = repr(selected_path)
        context = []
        start = max(target_line - 2, 1)
        end = target_line + 2
        for ln in range(start, end + 1):
            try:
                text = owner.text.get(f"{ln}.0", f"{ln}.0 lineend")
            except Exception:
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
        except Exception:
            pass
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
                    except Exception:
                        pass
                    with open(canonical_path, "a", encoding="utf-8") as handle:
                        handle.write(entry)
        except Exception:
            pass
    except Exception:
        return
