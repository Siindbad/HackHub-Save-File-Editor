"""JSON closer-tail symbol diagnostic rule helpers."""

import re
from typing import Any


def line_has_invalid_symbol_after_closer(line_text: Any) -> Any:
    """Return True when closer line has non-comma trailing symbols."""
    if not line_text:
        return False
    match = re.match(r'^\s*([\}\]])(?P<trail>.*)$', line_text)
    if not match:
        return False
    tail = (match.group("trail") or "").strip()
    return tail not in ("", ",")


def first_invalid_symbol_after_closer_col(line_text: Any) -> Any:
    """Return first invalid symbol column after close token."""
    match = re.match(r'^\s*([\}\]])(?P<trail>.*)$', line_text)
    if not match:
        return None
    prefix_len = len(line_text) - len(match.group("trail"))
    tail = match.group("trail") or ""
    idx = 0
    while idx < len(tail) and tail[idx].isspace():
        idx += 1
    if idx < len(tail) and tail[idx] == ",":
        idx += 1
        while idx < len(tail) and tail[idx].isspace():
            idx += 1
    if idx < len(tail):
        return prefix_len + idx
    return None


def fix_invalid_symbol_after_closer(line_text: Any) -> Any:
    """Normalize closer-tail line to `<closer>,` form."""
    match = re.match(r'^(\s*[\}\]])(?P<trail>.*)$', line_text)
    if not match:
        return line_text
    head = match.group(1)
    return head + ","
