"""JSON open-symbol trailing rule helpers."""

import re
from typing import Any


def invalid_symbol_after_open_span(line_text: Any) -> Any:
    """Return `(opener, start_col, end_col, symbol_text)` for invalid open-tail symbols."""
    if not line_text:
        return None
    match = re.match(r'^(?P<indent>\s*)(?P<open>[\{\[])(?P<trail>.*)$', line_text)
    if not match:
        return None
    opener = match.group("open")
    tail = match.group("trail") or ""
    idx = 0
    while idx < len(tail) and tail[idx].isspace():
        idx += 1
    if idx >= len(tail):
        return None
    ch = tail[idx]

    if opener == "{":
        if ch in ('"', "}"):
            return None
    else:
        if ch in ("]", "{", "[", '"', "-") or ch.isdigit() or ch.lower() in ("t", "f", "n"):
            return None

    if ch.isalnum() or ch in ('"', "'", "_"):
        return None

    run_end = idx + 1
    while run_end < len(tail):
        nxt = tail[run_end]
        if nxt.isspace() or nxt.isalnum() or nxt in ('"', "'", "_"):
            break
        run_end += 1

    col_start = len(match.group("indent")) + 1 + idx
    col_end = len(match.group("indent")) + 1 + run_end
    symbol_text = tail[idx:run_end]
    return opener, col_start, col_end, symbol_text


def line_has_invalid_symbol_after_open(line_text: Any) -> Any:
    """Return True when open-tail contains invalid symbol run."""
    return invalid_symbol_after_open_span(line_text) is not None


def fix_invalid_symbol_after_open(line_text: Any) -> Any:
    """Remove invalid symbol run after open token."""
    span = invalid_symbol_after_open_span(line_text)
    if not span:
        return line_text
    _opener, start_col, end_col, _symbol_text = span
    return line_text[:start_col] + line_text[end_col:]
