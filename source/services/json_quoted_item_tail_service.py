"""JSON quoted-item trailing symbol diagnostic rule helpers."""

import re
from typing import Any


def quoted_item_invalid_tail_span(line_text: Any, line_has_missing_key_quote_before_colon: Any) -> Any:
    """Return invalid-tail span for quoted array-item style lines."""
    if not line_text:
        return None
    raw = line_text.rstrip()
    if line_has_missing_key_quote_before_colon(raw):
        return None
    match = re.match(r'^(?P<head>\s*"[^"]*")(?P<tail>.*)$', raw)
    if not match:
        return None
    head = match.group("head") or ""
    tail = match.group("tail") or ""
    if tail.lstrip().startswith(":"):
        return None
    idx = 0
    while idx < len(tail) and tail[idx].isspace():
        idx += 1
    if idx >= len(tail):
        return None
    if tail[idx] == ",":
        idx += 1
        while idx < len(tail) and tail[idx].isspace():
            idx += 1
        if idx >= len(tail):
            return None
    start_col = len(head) + idx
    end_col = len(raw)
    if end_col <= start_col:
        end_col = start_col + 1
    return start_col, end_col


def line_has_invalid_tail_after_quoted_item(line_text: Any, line_has_missing_key_quote_before_colon: Any) -> Any:
    """Return True when quoted item has invalid trailing symbols."""
    return quoted_item_invalid_tail_span(line_text, line_has_missing_key_quote_before_colon) is not None


def fix_invalid_tail_after_quoted_item(line_text: Any, next_non_empty_line_text: Any) -> Any:
    """Trim invalid tail and keep comma only when following line is not a closer."""
    if not line_text:
        return line_text
    match = re.match(r'^(?P<head>\s*"[^"]*")(?P<tail>.*)$', line_text.rstrip())
    if not match:
        return line_text
    head = match.group("head")
    next_text = str(next_non_empty_line_text or "").strip()
    needs_comma = not next_text.startswith(("]", "}"))
    return head + ("," if needs_comma else "")
