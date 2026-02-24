"""JSON scalar-tail trailing symbol diagnostic rule helpers."""

import re
from typing import Any


def split_completed_scalar_value_tail(line_text: Any) -> Any:
    """Return `(head, tail, prefix_len)` for `\"key\": <scalar><tail>` lines."""
    if not line_text:
        return None
    match = re.match(r'^(?P<prefix>\s*"[^"]+"\s*:\s*)(?P<rest>.*)$', line_text)
    if not match:
        return None
    prefix = match.group("prefix") or ""
    rest = match.group("rest") or ""
    idx = 0
    while idx < len(rest) and rest[idx].isspace():
        idx += 1
    if idx >= len(rest):
        return None

    value_end = None
    ch = rest[idx]
    match ch:
        case '"':
            j = idx + 1
            escaped = False
            while j < len(rest):
                c = rest[j]
                if escaped:
                    escaped = False
                else:
                    match c:
                        case "\\":
                            escaped = True
                        case '"':
                            value_end = j + 1
                            break
                j += 1
            if value_end is None:
                return None
        case _ if ch in "-0123456789":
            num_m = re.match(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?", rest[idx:])
            if not num_m:
                return None
            value_end = idx + len(num_m.group(0))
        case _:
            literal_end = None
            for lit in ("true", "false", "null"):
                if rest.startswith(lit, idx):
                    end_idx = idx + len(lit)
                    if end_idx >= len(rest) or not re.match(r"[A-Za-z0-9_]", rest[end_idx]):
                        literal_end = end_idx
                        break
            if literal_end is None:
                return None
            value_end = literal_end

    prefix_len = len(prefix) + value_end
    head = line_text[:prefix_len]
    tail = line_text[prefix_len:]
    return head, tail, prefix_len


def line_has_invalid_trailing_symbols_after_string_value(line_text: Any) -> Any:
    """Return True when scalar-tail content is neither empty nor single comma."""
    parsed = split_completed_scalar_value_tail(line_text)
    if not parsed:
        return False
    _head, tail, _prefix_len = parsed
    return tail.strip() not in ("", ",")


def first_invalid_trailing_symbol_col(line_text: Any, lineno: Any, line_requires_trailing_comma: Any) -> Any:
    """Return first invalid trailing symbol column offset after scalar value."""
    parsed = split_completed_scalar_value_tail(line_text)
    if not parsed:
        return None
    _head, tail, prefix_len = parsed
    idx = 0
    while idx < len(tail) and tail[idx].isspace():
        idx += 1
    if idx < len(tail) and tail[idx] == ",":
        comma_idx = idx
        idx += 1
        while idx < len(tail) and tail[idx].isspace():
            idx += 1
        if idx < len(tail):
            comma_is_valid = bool(lineno) and bool(line_requires_trailing_comma(lineno))
            if comma_is_valid:
                return prefix_len + idx
            return prefix_len + comma_idx
        return None
    if idx < len(tail):
        return prefix_len + idx
    return None


def fix_invalid_trailing_symbols_after_string_value(line_text: Any, next_non_empty_line_text: Any) -> Any:
    """Drop invalid tail and preserve comma only when next line is not a closer."""
    parsed = split_completed_scalar_value_tail(line_text)
    if not parsed:
        return line_text
    head, _tail, _prefix_len = parsed
    next_text = str(next_non_empty_line_text or "").strip()
    needs_comma = not next_text.startswith(("}", "]"))
    return head + ("," if needs_comma else "")
