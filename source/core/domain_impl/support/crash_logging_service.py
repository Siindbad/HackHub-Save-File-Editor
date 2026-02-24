"""Crash logging and user-notice helpers."""

from datetime import datetime
import os
import platform
import threading
import traceback
from typing import Any


_MAX_FIELD_NAME_LEN = 48
_MAX_FIELD_VALUE_LEN = 256
_MAX_EXCEPTION_CHAIN_DEPTH = 3


def _safe_field_name(name: Any) -> str:
    raw = str(name or "").strip().lower()
    if not raw:
        return "unknown"
    kept = []
    for ch in raw:
        if ch.isalnum() or ch in ("_", "-", "."):
            kept.append(ch)
    token = "".join(kept).strip("._-")
    if not token:
        token = "unknown"
    return token[:_MAX_FIELD_NAME_LEN]


def _safe_field_value(value: Any) -> str:
    # Keep crash meta one-line and short to avoid leaking raw user payloads.
    cleaned = str(value or "").replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()
    if len(cleaned) > _MAX_FIELD_VALUE_LEN:
        return f"{cleaned[:_MAX_FIELD_VALUE_LEN]}..."
    return cleaned


def _safe_field(name: Any, value: Any) -> str:
    key = _safe_field_name(name)
    cleaned = _safe_field_value(value)
    return f"{key}={cleaned}\n"


def _exception_chain_summary(exc_value: Any, max_depth: int=_MAX_EXCEPTION_CHAIN_DEPTH) -> str:
    chain = []
    current = exc_value
    seen_ids = set()
    depth = 0
    while current is not None and depth < max(1, int(max_depth)):
        ident = id(current)
        if ident in seen_ids:
            break
        seen_ids.add(ident)
        etype = type(current).__name__
        msg = _safe_field_value(current)
        chain.append(f"{etype}:{msg}" if msg else etype)
        next_exc = getattr(current, "__cause__", None)
        if next_exc is None:
            next_exc = getattr(current, "__context__", None)
        current = next_exc
        depth += 1
    return " <= ".join(chain)


def append_crash_log(
    path: Any,
    trim_text_file_for_append: Any,
    max_bytes: Any,
    keep_bytes: Any,
    app_version: Any,
    context: Any,
    exc_type: Any,
    exc_value: Any,
    exc_tb: Any,
    expected_errors: Any,
    extra_fields: Any=None,
) -> Any:
    """Append structured crash context and traceback details to crash log."""
    try:
        trim_text_file_for_append(path, max_bytes, keep_bytes)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = (
            f"\n---\n"
            f"time={stamp}\n"
            f"context={context}\n"
            f"version={app_version}\n"
        )
        fields = {
            "pid": os.getpid(),
            "thread_name": threading.current_thread().name,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "exception_type": getattr(exc_type, "__name__", type(exc_value).__name__),
            "exception_message": str(exc_value or ""),
            "exception_chain": _exception_chain_summary(exc_value),
        }
        if isinstance(extra_fields, dict):
            for key, value in extra_fields.items():
                fields[str(key)] = value
        meta = "".join(_safe_field(name, value) for name, value in fields.items())
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(header)
            fh.write(meta)
            fh.write(detail.rstrip())
            fh.write("\n")
    except expected_errors:
        return


def show_crash_notice_once(crash_notice_shown: Any, crash_path: Any, ui_call: Any, showerror_func: Any) -> Any:
    """Show one-time crash-log notice and return updated shown flag."""
    if crash_notice_shown:
        return True
    msg = (
        "An unexpected error occurred.\n"
        "A crash log was written to:\n"
        f"{crash_path}"
    )
    ui_call(showerror_func, "Unexpected Error", msg, wait=False)
    return True
