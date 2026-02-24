"""Diagnostics log path and retention helpers."""

import os
import re
from datetime import datetime, timedelta
from typing import Any


def build_dated_diag_log_path(runtime_dir: Any, diag_log_filename: Any) -> Any:
    """Build today's diagnostics log path using YYYY-MM-DD suffix."""
    base, ext = os.path.splitext(str(diag_log_filename))
    dated_name = f"{base}-{datetime.now().strftime('%Y-%m-%d')}{ext}"
    return os.path.join(runtime_dir, dated_name)


def purge_diag_logs_for_new_session(
    runtime_dir: Any,
    diag_log_filename: Any,
    legacy_diag_log_filenames: Any,
    keep_days: Any,
    temp_dir: Any,
    expected_errors: Any,
) -> Any:
    """Remove stale dated diag logs and legacy filenames from runtime/temp paths."""
    keep_days = max(1, int(keep_days or 2))
    base, ext = os.path.splitext(str(diag_log_filename))
    prefix = f"{base}-"
    legacy_names = set(legacy_diag_log_filenames)
    keep_stamps = {
        (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d")
        for offset in range(keep_days)
    }

    try:
        entries = list(os.scandir(runtime_dir))
    except expected_errors:
        entries = []
    for entry in entries:
        if not entry.is_file():
            continue
        name = str(entry.name)
        should_delete = False
        if name == str(diag_log_filename) or name in legacy_names:
            should_delete = True
        elif name.startswith(prefix) and (not ext or name.endswith(ext)):
            stamp = name[len(prefix) : len(name) - len(ext)] if ext else name[len(prefix) :]
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp) and stamp not in keep_stamps:
                should_delete = True
        if not should_delete:
            continue
        try:
            os.remove(entry.path)
        except expected_errors:
            continue

    names = [diag_log_filename] + list(legacy_diag_log_filenames)
    for base_dir in (runtime_dir, temp_dir):
        for name in names:
            path = os.path.join(base_dir, str(name))
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except expected_errors:
                continue
