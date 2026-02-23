"""JSON colon/comma diagnostic rule helpers."""

import re
from typing import Any


def comma_before_colon_span(line_text: Any) -> Any:
    """Return comma-run span before colon in `"key",: value` patterns."""
    if not line_text:
        return None
    raw = line_text.rstrip()
    match = re.match(r'^(?P<head>\s*"[^"]+"\s*)(?P<run>,(?:\s*,)*)(?P<rest>\s*:\s*.+)$', raw)
    if not match:
        return None
    start_col = len(match.group("head") or "")
    run = (match.group("run") or "").rstrip()
    end_col = start_col + max(1, len(run))
    return start_col, end_col


def line_has_comma_before_colon(line_text: Any) -> Any:
    """Return True when a comma-run appears between key and colon."""
    return comma_before_colon_span(line_text) is not None


def fix_comma_before_colon(line_text: Any) -> Any:
    """Drop comma-run so key is followed directly by colon segment."""
    if not line_text:
        return line_text
    raw = line_text.rstrip()
    match = re.match(r'^(?P<head>\s*"[^"]+"\s*)(?P<run>,(?:\s*,)*)(?P<rest>\s*:\s*.+)$', raw)
    if not match:
        return raw
    head = match.group("head") or ""
    rest = match.group("rest") or ""
    return head + rest


def _has_clean_tail(value_text, end_idx):
    idx = end_idx
    while idx < len(value_text) and value_text[idx].isspace():
        idx += 1
    if idx >= len(value_text):
        return True
    if value_text[idx] in (",", "}", "]"):
        idx += 1
        while idx < len(value_text) and value_text[idx].isspace():
            idx += 1
        return idx >= len(value_text)
    return False


def _is_value_start(value_text, start_idx):
    token = value_text[start_idx]
    if token in ("{", "["):
        return True
    if token == '"':
        match = re.match(r'"(?:\\.|[^"\\])*"', value_text[start_idx:])
        if not match:
            return False
        return _has_clean_tail(value_text, start_idx + len(match.group(0)))
    if token == "-" or token.isdigit():
        match = re.match(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?', value_text[start_idx:])
        if not match:
            return False
        return _has_clean_tail(value_text, start_idx + len(match.group(0)))
    if value_text.startswith("true", start_idx) and (
        start_idx + 4 >= len(value_text) or not re.match(r"[A-Za-z0-9_]", value_text[start_idx + 4])
    ):
        return _has_clean_tail(value_text, start_idx + 4)
    if value_text.startswith("false", start_idx) and (
        start_idx + 5 >= len(value_text) or not re.match(r"[A-Za-z0-9_]", value_text[start_idx + 5])
    ):
        return _has_clean_tail(value_text, start_idx + 5)
    if value_text.startswith("null", start_idx) and (
        start_idx + 4 >= len(value_text) or not re.match(r"[A-Za-z0-9_]", value_text[start_idx + 4])
    ):
        return _has_clean_tail(value_text, start_idx + 4)
    return False


def _next_value_start_on_boundary(value_text, start_idx):
    idx = start_idx
    while idx < len(value_text):
        while idx < len(value_text) and not value_text[idx].isspace():
            idx += 1
        while idx < len(value_text) and value_text[idx].isspace():
            idx += 1
        if idx < len(value_text) and _is_value_start(value_text, idx):
            return idx
    return None


def comma_after_colon_span(line_text: Any) -> Any:
    """Return comma-run span after colon in `"key":, value` patterns."""
    if not line_text:
        return None
    raw = line_text.rstrip()
    match = re.match(r'^(?P<head>\s*"[^"]+"\s*:\s*)(?P<run>,(?:\s*,)*)(?P<tail>\s*.+)$', raw)
    if not match:
        return None
    tail = match.group("tail") or ""
    if not tail.strip():
        return None
    start_col = len(match.group("head") or "")
    run = (match.group("run") or "").rstrip()
    run_len = max(1, len(run))
    first_non_ws = None
    for idx, char in enumerate(tail):
        if not char.isspace():
            first_non_ws = idx
            break
    if first_non_ws is None:
        return None
    invalid_prefix_len = 0
    if not _is_value_start(tail, first_non_ws):
        next_valid = _next_value_start_on_boundary(tail, first_non_ws)
        if next_valid is not None:
            invalid_prefix_len = next_valid
        else:
            invalid_prefix_len = len(tail.rstrip())
    end_col = start_col + run_len + max(0, invalid_prefix_len)
    return start_col, end_col


def line_has_comma_after_colon(line_text: Any) -> Any:
    """Return True when a comma-run appears immediately after colon."""
    return comma_after_colon_span(line_text) is not None


def fix_comma_after_colon(line_text: Any) -> Any:
    """Drop comma-run and keep first valid value token when available."""
    if not line_text:
        return line_text
    match = re.match(r'^(?P<head>\s*"[^"]+"\s*:\s*)(?P<run>,(?:\s*,)*)(?P<tail>\s*.+)$', line_text.rstrip())
    if not match:
        return line_text.rstrip()
    head = match.group("head") or ""
    tail = match.group("tail") or ""
    first_non_ws = None
    for idx, char in enumerate(tail):
        if not char.isspace():
            first_non_ws = idx
            break
    if first_non_ws is None:
        return head.rstrip()
    keep_from = first_non_ws
    if not _is_value_start(tail, first_non_ws):
        next_valid = _next_value_start_on_boundary(tail, first_non_ws)
        if next_valid is not None:
            keep_from = next_valid
    kept_tail = tail[keep_from:].lstrip()
    sep = "" if not kept_tail else ("" if head.endswith((" ", "\t")) else " ")
    return f"{head}{sep}{kept_tail}"


def comma_before_closer_span(line_text: Any) -> Any:
    """Return comma-run span before `}` or `]` in closer-only lines."""
    if not line_text:
        return None
    raw = line_text.rstrip()
    match = re.match(
        r'^(?P<indent>\s*)(?P<run>,(?:\s*,)*)\s*(?P<close>[\}\]])(?P<trail>\s*)$',
        raw,
    )
    if not match:
        return None
    start_col = len(match.group("indent") or "")
    end_col = len(raw)
    if end_col <= start_col:
        end_col = start_col + 1
    return start_col, end_col


def line_has_comma_before_closer(line_text: Any) -> Any:
    """Return True when closer line starts with one or more commas."""
    return comma_before_closer_span(line_text) is not None


def fix_comma_before_closer(line_text: Any) -> Any:
    """Normalize comma-before-closer line to `<indent><closer>,`."""
    if not line_text:
        return line_text
    raw = line_text.rstrip()
    match = re.match(
        r'^(?P<indent>\s*)(?P<run>,(?:\s*,)*)\s*(?P<close>[\}\]])(?P<trail>\s*)$',
        raw,
    )
    if not match:
        return raw
    indent = match.group("indent") or ""
    close = match.group("close") or "}"
    return f"{indent}{close},"


def comma_line_invalid_tail_span(line_text: Any) -> Any:
    """Return span for comma-only line that has invalid tail symbols."""
    if not line_text:
        return None
    raw = line_text.rstrip()
    match = re.match(r'^(?P<indent>\s*),(?P<tail>.*)$', raw)
    if not match:
        return None
    tail = match.group("tail") or ""
    idx = 0
    while idx < len(tail) and tail[idx].isspace():
        idx += 1
    if idx >= len(tail):
        return None
    if tail[idx] in ("}", "]"):
        return None
    start_col = len(match.group("indent") or "")
    end_col = len(raw)
    if end_col <= start_col:
        end_col = start_col + 1
    return start_col, end_col


def line_has_comma_line_invalid_tail(line_text: Any) -> Any:
    """Return True when comma-leading line has invalid non-closer tail."""
    return comma_line_invalid_tail_span(line_text) is not None


def fix_comma_line_invalid_tail(line_text: Any, expected_close_symbol: Any) -> Any:
    """Convert invalid comma-leading line into `<indent><close>,` format."""
    if not line_text:
        return line_text
    raw = line_text.rstrip()
    match = re.match(r'^(?P<indent>\s*),(?P<tail>.*)$', raw)
    if not match:
        return raw
    indent = match.group("indent") or ""
    close = str(expected_close_symbol or "}").strip() or "}"
    return f"{indent}{close},"
