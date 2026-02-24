"""Update diagnostics logging helpers."""

from datetime import datetime
from typing import Any


def log_update_failure(owner: Any, exc: Any, auto: Any=False, pretty_error: Any="") -> Any:
    """Append normalized update-failure diagnostics entry to runtime log file."""
    try:
        path = owner._diag_log_path()
        owner._trim_text_file_for_append(path, owner.DIAG_LOG_MAX_BYTES, owner.DIAG_LOG_KEEP_BYTES)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chain = []
        for err in owner._walk_exception_chain(exc, max_depth=5):
            chain.append(f"{type(err).__name__}: {str(err).strip()}")
        details = " | ".join(part for part in chain if part) or str(exc or "").strip()
        mode = "auto" if bool(auto) else "manual"
        entry = (
            "\n---\n"
            f"time={stamp}\n"
            f"context=update_failure\n"
            f"mode={mode}\n"
            f"summary={str(pretty_error or '').strip()}\n"
            f"detail={details}\n"
        )
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(entry)
    except (OSError, ValueError, TypeError):
        return
