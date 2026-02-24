"""Crash-report state and payload helpers."""

import hashlib
import json
import os
from datetime import datetime
from typing import Any


def _normalized_limit(default_limit, max_chars):
    if max_chars is None:
        return int(default_limit)
    return max(0, int(max_chars))


def build_crash_log_path(runtime_dir: Any, crash_log_filename: Any) -> Any:
    """Build crash log path under runtime data directory."""
    return os.path.join(runtime_dir, crash_log_filename)


def build_crash_state_path(runtime_dir: Any, crash_state_filename: Any) -> Any:
    """Build crash state path under runtime data directory."""
    return os.path.join(runtime_dir, crash_state_filename)


def read_crash_log_tail(path: Any, default_limit: Any, max_chars: Any, read_text_file_tail: Any) -> Any:
    """Read trailing crash log text using the configured default cap."""
    limit = _normalized_limit(default_limit, max_chars)
    return read_text_file_tail(path, limit)


def read_latest_crash_block(
    read_crash_log_tail_func: Any,
    default_limit: Any,
    max_chars: Any,
    read_latest_block: Any,
    marker: Any="\n---\n",
) -> Any:
    """Read and trim the most recent crash entry block from the log tail."""
    text = read_crash_log_tail_func(max_chars=0)
    limit = _normalized_limit(default_limit, max_chars)
    return read_latest_block(text, max_chars=limit, marker=marker)


def read_crash_prompt_state(path: Any, expected_errors: Any) -> Any:
    """Load persisted crash prompt state dictionary when available."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            parsed = json.load(fh)
        if isinstance(parsed, dict):
            return parsed
    except expected_errors:
        pass
    return {}


def write_crash_prompt_state(path: Any, crash_hash: Any, write_text_file_atomic: Any, expected_errors: Any) -> Any:
    """Persist crash prompt state hash and update timestamp."""
    payload = json.dumps(
        {
            "last_seen_hash": str(crash_hash or ""),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        ensure_ascii=False,
        indent=2,
    )
    try:
        write_text_file_atomic(path, payload, encoding="utf-8")
    except expected_errors:
        return


def pending_crash_report_payload(
    log_path: Any,
    read_latest_crash_block_func: Any,
    read_crash_prompt_state_func: Any,
    expected_errors: Any,
) -> Any:
    """Build pending crash report payload unless already acknowledged."""
    if not os.path.isfile(log_path):
        return None
    try:
        if os.path.getsize(log_path) <= 0:
            return None
    except expected_errors:
        return None
    crash_tail = read_latest_crash_block_func()
    if not crash_tail.strip():
        return None
    crash_hash = hashlib.sha256(crash_tail.encode("utf-8", errors="replace")).hexdigest().lower()
    state = read_crash_prompt_state_func()
    if str(state.get("last_seen_hash", "")).strip().lower() == crash_hash:
        return None
    return {"hash": crash_hash, "tail": crash_tail}
