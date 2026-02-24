"""JSON highlight renderer service."""
from typing import Any


# Rendering helpers keep Tk-tag application out of decision code.
def apply_json_error_highlight(owner: Any, exc: Any, line: Any, start_index: Any, end_index: Any, note: Any=None) -> Any:
    return owner._apply_json_error_highlight(exc, line, start_index, end_index, note=note)


def log_json_error(owner: Any, exc: Any, target_line: Any, note: Any="") -> Any:
    return owner._log_json_error(exc, target_line, note=note)
