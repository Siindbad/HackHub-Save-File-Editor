"""UI-thread dispatch helpers for Tk callback execution."""

import threading
from typing import Any


def ui_call(owner: Any, callback: Any, *args: Any, wait: Any=False, default: Any=None, timeout: Any=15.0, expected_errors: Any=(), **kwargs: Any) -> Any:
    """Run callback on UI thread with optional synchronous wait from worker threads."""
    root = getattr(owner, "root", None)
    if root is None:
        return default
    if threading.current_thread() is threading.main_thread():
        try:
            return callback(*args, **kwargs)
        except tuple(expected_errors):
            return default

    if not wait:
        def invoke_async() -> Any:
            try:
                callback(*args, **kwargs)
            except tuple(expected_errors):
                return None

        try:
            root.after(0, invoke_async)
        except tuple(expected_errors):
            return default
        return default

    result = {"value": default}
    done = threading.Event()

    def invoke_sync() -> Any:
        try:
            result["value"] = callback(*args, **kwargs)
        except tuple(expected_errors):
            result["value"] = default
        finally:
            done.set()

    try:
        root.after(0, invoke_sync)
    except tuple(expected_errors):
        return default
    done.wait(max(0.0, float(timeout)))
    return result["value"]
