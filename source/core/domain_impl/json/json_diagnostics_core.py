"""Consolidated JSON domain pillar: json_diagnostics_core.

Contains merged logic from split JSON domain services.
"""


# --- Merged from json_nearby_line_service.py ---
"""Shared nearby-line scanning helper for JSON diagnostics."""
from typing import Any


def find_nearby_line(
    lineno: Any,
    lookback: Any,
    get_line_text_fn: Any,
    predicate_fn: Any,
    expected_errors: Any,
    strip_text: Any=False,
    predicate_kwargs_provider: Any=None,
) -> Any:
    """Find first matching line among current line + previous non-empty lines."""
    if not lineno:
        return None, None
    candidates = []
    try:
        current = get_line_text_fn(lineno)
        if strip_text:
            current = current.strip()
        candidates.append((lineno, current))
    except expected_errors:
        pass

    line = max(lineno - 1, 1)
    scanned = 0
    while line >= 1 and scanned < lookback:
        try:
            txt = get_line_text_fn(line)
            check = txt.strip() if strip_text else txt
        except expected_errors:
            break
        if check:
            candidates.append((line, txt if not strip_text else check))
            scanned += 1
        line -= 1

    for ln, txt in candidates:
        kwargs = {}
        if callable(predicate_kwargs_provider):
            kwargs = dict(predicate_kwargs_provider(ln, txt) or {})
        if predicate_fn(txt, **kwargs):
            return ln, txt
    return None, None


# --- Merged from json_colon_comma_service.py ---
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


# --- Merged from json_closer_symbol_service.py ---
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


# --- Merged from json_open_symbol_service.py ---
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


# --- Merged from json_property_key_rule_service.py ---
"""JSON property-key quote and escape diagnostic rule helpers."""

import re
from typing import Any


def missing_key_quote_before_colon_span(line_text: Any) -> Any:
    """Return span/issue payload for malformed property key quote patterns."""
    if not line_text:
        return None
    raw = line_text.rstrip()
    match = re.match(
        r'^(?P<indent>\s*)"(?P<base>[A-Za-z_][A-Za-z0-9_]*)(?P<bad>[^\w"]+):(?P<rest>.*)$',
        raw,
    )
    if match:
        indent = match.group("indent") or ""
        base = match.group("base") or ""
        bad = match.group("bad") or ""
        start_col = len(indent) + 1 + len(base)
        return {
            "start_col": start_col,
            "end_col": start_col + len(bad),
            "issue": "wrong_symbol_before_colon",
        }

    match = re.match(r'^(?P<indent>\s*)"(?P<key>[^":]+):(?P<rest>.*)$', raw)
    if match:
        rest = match.group("rest") or ""
        rest_trim = rest.lstrip()
        if not rest_trim or rest_trim.startswith(","):
            return None
        indent = match.group("indent") or ""
        key = match.group("key") or ""
        colon_col = len(indent) + 1 + len(key)
        return {
            "start_col": colon_col,
            "end_col": colon_col,
            "issue": "missing_close_quote",
        }

    match = re.match(r'^(?P<indent>\s*)(?P<bad>[^\w"\s])(?P<key>[^":]+)"(?P<rest>\s*:.*)$', raw)
    if match:
        indent = match.group("indent") or ""
        start_col = len(indent)
        return {
            "start_col": start_col,
            "end_col": start_col + 1,
            "issue": "wrong_open_quote_char",
        }

    match = re.match(r'^(?P<indent>\s*)(?P<key>[A-Za-z_][A-Za-z0-9_]*)"(?P<rest>\s*:.*)$', raw)
    if not match:
        return None
    indent = match.group("indent") or ""
    start_col = len(indent)
    return {
        "start_col": start_col,
        "end_col": start_col,
        "issue": "missing_open_quote",
    }


def line_has_missing_key_quote_before_colon(line_text: Any) -> Any:
    """Return True when malformed property-key quote pattern is present."""
    return missing_key_quote_before_colon_span(line_text) is not None


def fix_property_key_symbol_before_colon(line_text: Any) -> Any:
    """Normalize symbol-before-colon key typo into proper quoted key form."""
    if not line_text:
        return line_text
    return re.sub(
        r'^(\s*)"([A-Za-z_][A-Za-z0-9_]*)([^\w"]+)(\s*:)',
        r'\1"\2"\4',
        line_text.rstrip(),
        count=1,
    )


def property_key_invalid_escape_span(line_text: Any) -> Any:
    """Return span for invalid backslash before property key colon."""
    if not line_text:
        return None
    raw = line_text.rstrip()
    match = re.match(r'^(?P<indent>\s*)"(?P<key>[^"]*)\\(?P<rest>\s*:.*)$', raw)
    if not match:
        return None
    indent = match.group("indent") or ""
    key = match.group("key") or ""
    start_col = len(indent) + 1 + len(key)
    return start_col, start_col + 1


def line_has_property_key_invalid_escape(line_text: Any) -> Any:
    """Return True when property key includes invalid close-quote escape."""
    return property_key_invalid_escape_span(line_text) is not None


def fix_property_key_invalid_escape(line_text: Any) -> Any:
    """Replace first invalid key-close escape with proper quote before colon."""
    if not line_text:
        return line_text
    return re.sub(r'^(\s*"[^"]*)\\(\s*:)', r'\1"\2', line_text.rstrip(), count=1)


# --- Merged from json_quoted_item_tail_service.py ---
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


# --- Merged from json_scalar_tail_service.py ---
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


# --- Merged from json_top_level_close_service.py ---
"""JSON top-level close symbol tail diagnostic rule helpers."""

import re
from typing import Any


def line_has_illegal_comma_after_top_level_close(line_text: Any, lineno: Any, next_non_empty_line_number: Any) -> Any:
    """Return True for EOF lines like `},` or `],` where comma is illegal."""
    if not line_text or not lineno:
        return False
    if not re.match(r'^\s*[\}\]]\s*,+\s*$', line_text):
        return False
    next_line = next_non_empty_line_number(lineno)
    return next_line is None


def top_level_close_symbol_run_span(line_text: Any) -> Any:
    """Return span for trailing symbols after top-level close token."""
    if not line_text:
        return None
    raw = line_text.rstrip()
    match = re.match(r'^(?P<indent>\s*)(?P<close>[\}\]])(?P<trail>.*)$', raw)
    if not match:
        return None
    tail = match.group("trail") or ""
    idx = 0
    while idx < len(tail) and tail[idx].isspace():
        idx += 1
    if idx >= len(tail):
        return None
    start_col = len(match.group("indent") or "") + 1 + idx
    end_col = len(raw)
    if end_col <= start_col:
        end_col = start_col + 1
    return start_col, end_col


def line_has_top_level_close_symbol_run(line_text: Any, lineno: Any, next_non_empty_line_number: Any) -> Any:
    """Return True when close-symbol tail run appears at EOF context."""
    if not line_text or not lineno:
        return False
    if top_level_close_symbol_run_span(line_text) is None:
        return False
    next_line = next_non_empty_line_number(lineno)
    return next_line is None


def fix_top_level_close_symbol_run(line_text: Any) -> Any:
    """Trim all trailing symbols after first top-level close token."""
    if not line_text:
        return line_text
    return re.sub(r'(\s*[\}\]])\s*.*$', r'\1', line_text.rstrip())


def comma_run_after_top_level_close_span(line_text: Any) -> Any:
    """Return span for comma run after top-level close token."""
    if not line_text:
        return None
    raw = line_text.rstrip()
    match = re.match(r'^(?P<indent>\s*)(?P<close>[\}\]])(?P<trail>\s*,+\s*)$', raw)
    if not match:
        return None
    indent_len = len(match.group("indent") or "")
    start_col = raw.find(",", indent_len + 1)
    if start_col < 0:
        return None
    end_col = len(raw)
    if end_col <= start_col:
        end_col = start_col + 1
    return start_col, end_col


def fix_illegal_comma_after_top_level_close(line_text: Any) -> Any:
    """Drop trailing comma run after top-level close token."""
    if not line_text:
        return line_text
    return re.sub(r'(\s*[\}\]])\s*,+\s*$', r'\1', line_text.rstrip())


# --- Merged from json_error_diag_service.py ---
"""JSON diagnostic note mapping and log writer service."""


import logging
import os
import tempfile
from datetime import datetime
from typing import Any
from core.exceptions import EXPECTED_ERRORS
_LOG = logging.getLogger(__name__)

_LOGGER = logging.getLogger(__name__)
_EXPECTED_DIAG_ERRORS = (
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    AttributeError,
    KeyError,
    IndexError,
    ImportError,
)


def _log_expected_diag_error(stage: str, exc: Exception) -> None:
    _LOGGER.debug(
        "json_error_diag.expected_error",
        extra={"stage": stage, "error_type": type(exc).__name__},
        exc_info=exc,
    )


def diag_system_from_note(note: object, is_symbol_error_note: Any = None) -> str:
    """Map a diagnostic note string to a stable log system bucket."""
    note_text = str(note or "").strip().lower()
    match note_text:
        case _ if note_text.startswith("locked_"):
            return "highlight_restore"
        case _ if note_text.startswith("overlay_"):
            return "overlay_parse"
        case _ if note_text.startswith("highlight_failed"):
            return "highlight_internal"
        case _ if note_text.startswith("cursor_restore"):
            return "cursor_restore"
        case _ if (
            note_text.startswith("spacing_")
            or note_text.startswith("missing_phone")
            or note_text.startswith("invalid_email")
        ):
            return "input_validation"
        case _ if note_text.startswith("symbol_"):
            return "symbol_recovery"
    # Older symbol diagnostics used `invalid_*`; keep them grouped with symbol recovery.
    if note_text.startswith("invalid_") and callable(is_symbol_error_note):
        try:
            if is_symbol_error_note(note_text):
                return "symbol_recovery"
        except _EXPECTED_DIAG_ERRORS as exc:
            _log_expected_diag_error("diag_system_from_note", exc)
    return "json_highlight"


def log_json_error(owner: Any, exc: Exception, target_line: object, note: str = "") -> None:
    """Append a normalized diagnostics entry to the runtime diagnostics log."""
    try:
        log_path = owner._diag_log_path()
        try:
            log_dir = os.path.dirname(str(log_path or ""))
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
        except _EXPECTED_DIAG_ERRORS as mkdir_exc:
            _log_expected_diag_error("ensure_log_dir", mkdir_exc)
        log_path_abs = os.path.abspath(log_path)
        for legacy_name in owner.LEGACY_DIAG_LOG_FILENAMES:
            legacy_path = os.path.join(tempfile.gettempdir(), str(legacy_name))
            if os.path.abspath(legacy_path) == log_path_abs:
                continue
            try:
                if os.path.isfile(legacy_path):
                    os.remove(legacy_path)
            except EXPECTED_ERRORS as exc:
                _LOG.debug('expected_error', exc_info=exc)
                pass
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = getattr(exc, "msg", str(exc))
        lineno = getattr(exc, "lineno", None)
        colno = getattr(exc, "colno", None)
        try:
            target_line = int(target_line)
        except (TypeError, ValueError, AttributeError):
            target_line = int(lineno or 1)
        target_line = max(1, target_line)
        diag_system = diag_system_from_note(
            note,
            is_symbol_error_note=getattr(owner, "_is_symbol_error_note", None),
        )
        diag_mode = str(getattr(owner, "_error_visual_mode", "") or "").strip()
        try:
            item_id = owner.tree.focus()
            selected_path = owner.item_to_path.get(item_id, None)
        except _EXPECTED_DIAG_ERRORS as tree_exc:
            _log_expected_diag_error("resolve_selected_path", tree_exc)
            selected_path = None
        path_text = repr(selected_path)
        context = []
        start = max(target_line - 2, 1)
        end = target_line + 2
        for ln in range(start, end + 1):
            try:
                text = owner.text.get(f"{ln}.0", f"{ln}.0 lineend")
            except _EXPECTED_DIAG_ERRORS as text_exc:
                _log_expected_diag_error("collect_context_line", text_exc)
                text = ""
            context.append(f"{ln}: {text}")
        entry = (
            "\n---\n"
            f"time={now} action={str(getattr(owner, '_diag_action', 'apply_edit:0'))}\n"
            f"msg={msg} lineno={lineno} col={colno} target={target_line} note={note}\n"
            f"system={diag_system} mode={diag_mode or '-'}\n"
            f"path={path_text}\n"
            + "\n".join(context).rstrip()
            + "\n"
        )
        try:
            owner._trim_text_file_for_append(
                log_path,
                owner.DIAG_LOG_MAX_BYTES,
                owner.DIAG_LOG_KEEP_BYTES,
            )
        except _EXPECTED_DIAG_ERRORS as trim_exc:
            _log_expected_diag_error("trim_dated_log", trim_exc)
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(entry)
        # Mirror write: keep one stable non-dated diagnostics file for local
        # visibility while retaining dated day-file logs for retention tooling.
        try:
            canonical_name = str(getattr(owner, "DIAG_LOG_FILENAME", "") or "").strip()
            if canonical_name:
                canonical_path = os.path.join(os.path.dirname(log_path), canonical_name)
                if os.path.abspath(canonical_path) != log_path_abs:
                    try:
                        owner._trim_text_file_for_append(
                            canonical_path,
                            owner.DIAG_LOG_MAX_BYTES,
                            owner.DIAG_LOG_KEEP_BYTES,
                        )
                    except _EXPECTED_DIAG_ERRORS as trim_exc:
                        _log_expected_diag_error("trim_canonical_log", trim_exc)
                    with open(canonical_path, "a", encoding="utf-8") as handle:
                        handle.write(entry)
        except _EXPECTED_DIAG_ERRORS as canonical_exc:
            _log_expected_diag_error("write_canonical_log", canonical_exc)
    except _EXPECTED_DIAG_ERRORS as write_exc:
        _log_expected_diag_error("write_diagnostics_log", write_exc)
        return


# --- Merged from json_parse_feedback_service.py ---
"""Shared parse-error feedback helpers for JSON apply/live flows."""


import logging
from typing import Any
from core.exceptions import EXPECTED_ERRORS
_LOG = logging.getLogger(__name__)

_LOGGER = logging.getLogger(__name__)
_EXPECTED_PARSE_FEEDBACK_ERRORS = (
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    AttributeError,
    KeyError,
    IndexError,
    ImportError,
)


def _log_expected_dispatch_error(stage: str, exc: Exception) -> None:
    _LOGGER.debug(
        "json_parse_feedback.dispatch_expected_error",
        extra={"stage": stage, "error_type": type(exc).__name__},
        exc_info=exc,
    )


def handle_live_parse_error(owner: Any, exc: Exception, path: list[str]) -> None:
    """Render and log live-feedback parse errors with overlay/highlight updates."""
    owner._begin_diag_action("live_json_feedback")
    try:
        emergency_logger = getattr(owner, "_log_json_error_emergency", None)
        if callable(emergency_logger):
            emergency_logger(
                exc,
                getattr(exc, "lineno", None) or 1,
                note="overlay_parse_live_emergency",
            )
    except _EXPECTED_PARSE_FEEDBACK_ERRORS as dispatch_exc:
        _log_expected_dispatch_error("live_emergency_logger", dispatch_exc)
    try:
        owner._log_json_error(exc, getattr(exc, "lineno", None) or 1, note="overlay_parse_live_enter")
    except _EXPECTED_PARSE_FEEDBACK_ERRORS as dispatch_exc:
        _log_expected_dispatch_error("live_primary_logger", dispatch_exc)
    owner._error_visual_mode = "guide"
    owner._show_error_overlay("Invalid Entry", owner._format_json_error(exc))
    owner._apply_json_view_lock_state(path)
    owner._highlight_json_error(exc)


def handle_apply_parse_error(owner: Any, exc: Exception, path: list[str]) -> None:
    """Render and log apply-flow parse errors with fallback diagnostic note."""
    try:
        emergency_logger = getattr(owner, "_log_json_error_emergency", None)
        if callable(emergency_logger):
            emergency_logger(
                exc,
                getattr(exc, "lineno", None) or 1,
                note="overlay_parse_apply_emergency",
            )
    except _EXPECTED_PARSE_FEEDBACK_ERRORS as dispatch_exc:
        _log_expected_dispatch_error("apply_emergency_logger", dispatch_exc)
    message = owner._format_json_error(exc)
    owner._error_visual_mode = "guide"
    owner._show_error_overlay("Invalid Entry", message)
    owner._apply_json_view_lock_state(path)
    owner._last_error_highlight_note = ""
    owner._highlight_json_error(exc)
    highlight_note = str(getattr(owner, "_last_error_highlight_note", "") or "").strip()
    if not highlight_note or highlight_note == "highlight" or highlight_note.startswith("highlight_failed"):
        try:
            owner._log_json_error(exc, getattr(exc, "lineno", None) or 1, note="overlay_parse")
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            pass


# --- Merged from json_validation_feedback_service.py ---
"""Shared JSON validation-feedback helpers for apply/live edit flows."""
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def show_spacing_issue(owner: Any, spacing_issue: Any) -> Any:
    """Render spacing validation feedback and highlight span."""
    if not spacing_issue:
        return False
    line, start_col, end_col, before_line, after_line = spacing_issue
    message = owner._format_suggestion(
        'Invalid Entry: add a space after ":".',
        before_line,
        after_line,
    )
    owner._error_visual_mode = "guide"
    owner._show_error_overlay("Invalid Entry", message)
    try:
        start_index = f"{line}.{max(start_col, 0)}"
        end_index = f"{line}.{max(end_col, start_col + 1)}"
        dummy = type(
            "E",
            (),
            {"msg": "Missing space after ':'", "lineno": line, "colno": start_col + 1},
        )
        owner._apply_json_error_highlight(
            dummy, line, start_index, end_index, note="spacing_missing_space_after_colon"
        )
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        owner._highlight_custom_range(line, start_col, end_col)
    return True


def show_email_issue(owner: Any, email_validation: Any, log_issue: Any=False) -> Any:
    """Render invalid-email feedback, optional diagnostics logging."""
    if not email_validation:
        return False
    field_path, bad_value, email_issue = email_validation
    field_label = owner._format_path_for_display(field_path)
    before_line = f'"{field_label}": "{bad_value}"'
    after_line = f'"{field_label}": "{email_issue["suggested"]}"'
    message = owner._format_suggestion(email_issue["message"], before_line, after_line)
    owner._error_visual_mode = "guide"
    owner._show_error_overlay("Invalid Entry", message)
    preferred_key = field_path[-1] if field_path and isinstance(field_path[-1], str) else None
    span = owner._find_value_span_in_editor(bad_value, preferred_key=preferred_key)
    if span:
        line, start_col, end_col = span
        owner._highlight_custom_range(line, start_col, end_col)
    else:
        owner._highlight_custom_range(1, 0, max(1, len(before_line)))
    if bool(log_issue):
        try:
            log_line = span[0] if span else 1
            log_col = (span[1] + 1) if span else 1
            dummy = type("E", (), {"msg": email_issue["log_msg"], "lineno": log_line, "colno": log_col})
            owner._log_json_error(dummy, log_line, note=email_issue["note"])
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            pass
    return True


def show_phone_issue(owner: Any, phone_issue: Any, log_issue: Any=False) -> Any:
    """Render phone-format feedback, optional diagnostics logging."""
    if not phone_issue:
        return False
    line, start_col, end_col, before_line, after_line = phone_issue
    message = owner._format_suggestion(
        'Invalid Entry: add "-" to the phone number.',
        before_line,
        after_line,
    )
    owner._error_visual_mode = "guide"
    owner._show_error_overlay("Invalid Entry", message)
    owner._highlight_custom_range(line, start_col, end_col)
    if bool(log_issue):
        try:
            dummy = type("E", (), {"msg": "Missing '-' in phone", "lineno": line, "colno": start_col + 1})
            owner._log_json_error(dummy, line, note="missing_phone_dash")
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            pass
    return True


# --- Merged from json_repair_service.py ---
"""JSON repair rules used by apply/live feedback flows."""


import difflib
import re

from typing import Any

from core import json_diagnostics as json_diag_core
from core.exceptions import EXPECTED_ERRORS
from core.domain_impl.json import json_diagnostics_core as json_closer_symbol_service
from core.domain_impl.json import json_diagnostics_core as json_colon_comma_service
from core.domain_impl.json import json_diagnostics_core as json_nearby_line_service
from core.domain_impl.json import json_diagnostics_core as json_open_symbol_service
from core.domain_impl.json import json_diagnostics_core as json_property_key_rule_service
from core.domain_impl.json import json_diagnostics_core as json_quoted_item_tail_service
from core.domain_impl.json import json_diagnostics_core as json_scalar_tail_service
from core.domain_impl.json import json_diagnostics_core as json_top_level_close_service


def _strip_invalid_trailing_chars(value_str: str) -> str:
    if not value_str:
        return value_str
    valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.@\t \n\r")
    while value_str and value_str[-1] not in valid_chars:
        value_str = value_str[:-1]
    return value_str.rstrip()


def _json_token_followed_by_colon(owner: Any, end_index, lookahead_chars=24):
        text = getattr(owner, "text", None)
        if text is None:
            return False
        try:
            tail = owner.text.get(end_index, f"{end_index}+{max(1, int(lookahead_chars))}c")
        except EXPECTED_ERRORS:
            return False
        if not tail:
            return False
        for ch in tail:
            if ch in (" ", "\t", "\r", "\n"):
                continue
            return ch == ":"
        return False


def _missing_colon_example(owner: Any, line_text):
        if ":" in line_text:
            return line_text
        has_trailing_comma = line_text.rstrip().endswith(",")
        stripped = line_text.strip().strip(",")
        if not stripped:
            return "\"key\": \"value\""
        m = re.match(r'^\s*"([^"]+)"\s+(.+?)\s*$', stripped)
        if m:
            key = m.group(1)
            value = m.group(2).strip()
            result = f"\"{key}\": {value}"
            if has_trailing_comma and not result.rstrip().endswith(","):
                result += ","
            return result
        if "\"" in stripped:
            try:
                first = stripped.split("\"", 2)
                if len(first) >= 2:
                    quote_index = stripped.find('"', 1)
                    rest = stripped[quote_index + 1 :].strip()
                    rest = rest.lstrip()
                    if rest.startswith("\""):
                        result = f"{stripped[:quote_index + 1]}: {rest}"
                        if line_text.rstrip().endswith(",") and not result.rstrip().endswith(","):
                            result = result.rstrip() + ","
                        return result
            except EXPECTED_ERRORS:
                pass
        if not stripped.startswith("\""):
            stripped = f"\"{stripped.strip()}\""
        result = f"{stripped}: \"value\""
        if has_trailing_comma and not result.rstrip().endswith(","):
            result += ","
        return result


def _missing_colon_key_value_span(owner: Any, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        if ":" in raw:
            return None
        m = re.match(r'^(?P<indent>\s*)"(?P<key>[^"]+)"(?P<gap>\s+)(?P<value>.+?)\s*,?\s*$', raw)
        if not m:
            return None
        value = m.group("value") or ""
        if not owner._is_json_value_token_start(value):
            return None
        first_q = raw.find('"')
        if first_q < 0:
            return None
        second_q = raw.find('"', first_q + 1)
        if second_q < 0:
            return None
        insert_col = second_q + 1
        return insert_col, insert_col


def _find_nearby_missing_colon_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_missing_colon_key_value(txt):
                return ln, txt
        return None, None


def _is_key_colon_comma_line(owner: Any, line_text):
        if not line_text:
            return False
        return bool(re.match(r'^\s*"[^"]+"\s*:\s*,\s*$', line_text))


def _key_colon_comma_to_list_open(owner: Any, line_text):
        if not owner._is_key_colon_comma_line(line_text):
            return line_text
        m = re.match(r'^(\s*"[^"]+"\s*:\s*),\s*$', line_text)
        if not m:
            return line_text
        return m.group(1) + "["


def _line_extra_quote_in_string_value(owner: Any, line_text):
        if not line_text:
            return False
        return bool(re.match(r'^\s*"[^"]+"\s*:\s*"[^"]*""\s*,?\s*$', line_text))


def _fix_extra_quote_to_comma(owner: Any, line_text):
        if not owner._line_extra_quote_in_string_value(line_text):
            return line_text
        idx = line_text.rfind('""')
        if idx == -1:
            return line_text
        return line_text[:idx] + '",' + line_text[idx + 2 :]


def _line_has_trailing_stray_quote_after_comma(owner: Any, line_text):
        if not line_text:
            return False
        return bool(re.match(r'^\s*"[^"]+"\s*:\s*"[^"]*"\s*,\s*"\s*$', line_text))


def _fix_trailing_stray_quote_after_comma(owner: Any, line_text):
        if not owner._line_has_trailing_stray_quote_after_comma(line_text):
            return line_text
        return re.sub(r',\s*"\s*$', ",", line_text)


def _find_nearby_trailing_stray_quote_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except EXPECTED_ERRORS:
                break
            if txt:
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_trailing_stray_quote_after_comma(txt):
                return ln, txt
        return None, None


def _line_has_duplicate_trailing_comma(owner: Any, line_text):
        if not line_text:
            return False
        return bool(re.match(r'^\s*"[^"]+"\s*:\s*.+,\s*,\s*$', line_text))


def _fix_duplicate_trailing_comma(owner: Any, line_text):
        if not owner._line_has_duplicate_trailing_comma(line_text):
            return line_text
        return re.sub(r',\s*,\s*$', ",", line_text)


def _find_nearby_duplicate_trailing_comma_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except EXPECTED_ERRORS:
                break
            if txt:
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_duplicate_trailing_comma(txt):
                return ln, txt
        return None, None


def _line_requires_trailing_comma(owner: Any, lineno):
        if not lineno:
            return False
        next_line = owner._next_non_empty_line_number(lineno)
        if not next_line:
            return False
        next_text = owner._line_text(next_line).lstrip()
        return not next_text.startswith(("}", "]"))


def _duplicate_comma_run_span(owner: Any, line_text, lineno=None):
        if not line_text:
            return None
        raw = line_text.rstrip()
        m = re.match(r'^(?P<prefix>.*?),(?P<extra>\s*,+\s*)$', raw)
        if not m:
            return None
        prefix = m.group("prefix") or ""
        extra = m.group("extra") or ""
        if not extra or "," not in extra:
            return None
        prefix_stripped = prefix.strip()
        if not prefix_stripped or prefix_stripped.endswith(":"):
            return None

        keep_one_comma = owner._line_requires_trailing_comma(lineno)
        if keep_one_comma:
            leading_ws = len(extra) - len(extra.lstrip())
            start_col = len(prefix) + 1 + leading_ws
        else:
            start_col = len(prefix)
        end_col = len(raw.rstrip())
        if end_col <= start_col:
            end_col = start_col + 1
        return start_col, end_col


def _fix_duplicate_comma_run(owner: Any, line_text, lineno=None):
        if not line_text:
            return line_text
        raw = line_text.rstrip()
        m = re.match(r'^(?P<prefix>.*?),(?P<extra>\s*,+\s*)$', raw)
        if not m:
            return raw
        prefix = m.group("prefix") or ""
        if owner._line_requires_trailing_comma(lineno):
            return prefix + ","
        return prefix


def _find_nearby_duplicate_comma_run_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_duplicate_comma_run(txt, lineno=ln):
                return ln, txt
        return None, None


def _find_nearby_comma_before_colon_line(owner: Any, lineno, lookback=2):
        return json_nearby_line_service.find_nearby_line(
            lineno=lineno,
            lookback=lookback,
            get_line_text_fn=lambda ln: owner.text.get(f"{ln}.0", f"{ln}.0 lineend"),
            predicate_fn=lambda txt, **_kwargs: owner._line_has_comma_before_colon(txt),
            expected_errors=EXPECTED_ERRORS,
            strip_text=False,
        )


def _find_nearby_comma_after_colon_line(owner: Any, lineno, lookback=2):
        return json_nearby_line_service.find_nearby_line(
            lineno=lineno,
            lookback=lookback,
            get_line_text_fn=lambda ln: owner.text.get(f"{ln}.0", f"{ln}.0 lineend"),
            predicate_fn=lambda txt, **_kwargs: owner._line_has_comma_after_colon(txt),
            expected_errors=EXPECTED_ERRORS,
            strip_text=False,
        )


def _analyze_invalid_prefix_after_colon(owner: Any, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        m = re.match(r'^(?P<head>\s*"[^"]+"\s*:\s*)(?P<tail>.*)$', raw)
        if not m:
            return None
        head = m.group("head") or ""
        tail = m.group("tail") or ""
        if not tail.strip():
            return None
        first_non_ws = None
        for idx, ch in enumerate(tail):
            if not ch.isspace():
                first_non_ws = idx
                break
        if first_non_ws is None:
            return None
        if tail[first_non_ws] == ",":
            return None
        first_ch = tail[first_non_ws]
        if first_ch.isalnum() or first_ch in ('"', "-"):
            return None

        def head_with_space():
            return re.sub(r':\s*$', ': ', head)

        def token_end_if_clean(s, idx):
            ch = s[idx]
            if ch == '"':
                mstr = re.match(r'"(?:\\.|[^"\\])*"', s[idx:])
                if not mstr:
                    return None
                end = idx + len(mstr.group(0))
            elif ch == "-" or ch.isdigit():
                mnum = re.match(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?', s[idx:])
                if not mnum:
                    return None
                end = idx + len(mnum.group(0))
            elif s.startswith("true", idx) and (idx + 4 >= len(s) or not re.match(r"[A-Za-z0-9_]", s[idx + 4])):
                end = idx + 4
            elif s.startswith("false", idx) and (idx + 5 >= len(s) or not re.match(r"[A-Za-z0-9_]", s[idx + 5])):
                end = idx + 5
            elif s.startswith("null", idx) and (idx + 4 >= len(s) or not re.match(r"[A-Za-z0-9_]", s[idx + 4])):
                end = idx + 4
            elif ch in ("{", "["):
                close = "}" if ch == "{" else "]"
                j = idx + 1
                while j < len(s) and s[j].isspace():
                    j += 1
                if j >= len(s):
                    return len(s)
                if j < len(s) and s[j] == close:
                    end = j + 1
                else:
                    return None
            else:
                return None

            j = end
            while j < len(s) and s[j].isspace():
                j += 1
            if j < len(s) and s[j] == ",":
                j += 1
                while j < len(s) and s[j].isspace():
                    j += 1
            if j == len(s):
                return end
            return None

        if token_end_if_clean(tail, first_non_ws) is not None:
            return None

        def next_value_start_on_boundary(s, start_idx):
            i = start_idx
            while i < len(s):
                while i < len(s) and not s[i].isspace():
                    i += 1
                while i < len(s) and s[i].isspace():
                    i += 1
                if i < len(s) and token_end_if_clean(s, i) is not None:
                    return i
            return None

        next_valid = next_value_start_on_boundary(tail, first_non_ws)
        start_col = len(head) + first_non_ws
        if next_valid is not None:
            end_col = len(head) + next_valid
            after = f"{head_with_space()}{tail[next_valid:].lstrip()}".rstrip()
        else:
            end_col = len(raw)
            after = head.rstrip()
        if end_col <= start_col:
            end_col = start_col + 1
        return {"start_col": start_col, "end_col": end_col, "after": after}


def _fix_invalid_prefix_after_colon(owner: Any, line_text):
        analysis = owner._analyze_invalid_prefix_after_colon(line_text)
        if not analysis:
            return line_text
        return analysis["after"]


def _find_nearby_invalid_prefix_after_colon_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_invalid_prefix_after_colon(txt):
                return ln, txt
        return None, None


def _find_nearby_comma_before_closer_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_comma_before_closer(txt):
                return ln, txt
        return None, None


def _expected_missing_close_symbol(owner: Any, lineno):
        try:
            if owner._is_missing_object_close():
                return "}"
            if owner._is_missing_list_close():
                return "]"
        except EXPECTED_ERRORS:
            pass
        next_line = owner._next_non_empty_line_number(lineno or 1) if lineno else None
        next_text = owner._line_text(next_line).strip() if next_line else ""
        if next_text.startswith("["):
            return "]"
        return "}"


def _fix_comma_line_invalid_tail(owner: Any, line_text, lineno=None):
        return json_colon_comma_service.fix_comma_line_invalid_tail(
            line_text=line_text,
            expected_close_symbol=owner._expected_missing_close_symbol(lineno),
        )


def _find_nearby_comma_line_invalid_tail_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_comma_line_invalid_tail(txt):
                return ln, txt
        return None, None


def _find_nearby_missing_key_quote_before_colon_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_missing_key_quote_before_colon(txt):
                return ln, txt
        return None, None


def _missing_key_quote_before_colon_diag(owner: Any, line_no, colno=1):
        missing_key_quote_no, missing_key_quote_text = owner._find_nearby_missing_key_quote_before_colon_line(
            line_no
        )
        if not (missing_key_quote_text and missing_key_quote_no):
            return None
        raw = owner._line_text(missing_key_quote_no)
        span = owner._missing_key_quote_before_colon_span(raw)
        if span:
            start_col = int(span.get("start_col", max((colno or 1) - 1, 0)))
            end_col = int(span.get("end_col", start_col))
            issue = str(span.get("issue", "")).strip().lower()
        else:
            start_col = max((colno or 1) - 1, 0)
            end_col = start_col
            issue = ""
        header = "Invalid Entry: add quotes around the highlighted name."
        note = "missing_key_quote_before_colon"
        after = owner._quote_property_name(missing_key_quote_text).strip()
        if issue == "wrong_symbol_before_colon":
            header = "Invalid Entry: remove the invalid symbol before ':'."
            note = "symbol_wrong_property_key_symbol"
            after = owner._fix_property_key_symbol_before_colon(missing_key_quote_text).strip()
        if issue == "wrong_open_quote_char":
            header = "Invalid Entry: replace the wrong quote with a double quote."
            note = "symbol_wrong_property_quote_char"
        return {
            "header": header,
            "before": missing_key_quote_text.strip(),
            "after": after,
            "line": missing_key_quote_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": note,
        }


def _quoted_item_invalid_tail_span(owner: Any, line_text):
        return json_quoted_item_tail_service.quoted_item_invalid_tail_span(
            line_text=line_text,
            line_has_missing_key_quote_before_colon=owner._line_has_missing_key_quote_before_colon,
        )


def _line_has_invalid_tail_after_quoted_item(owner: Any, line_text):
        return json_quoted_item_tail_service.line_has_invalid_tail_after_quoted_item(
            line_text=line_text,
            line_has_missing_key_quote_before_colon=owner._line_has_missing_key_quote_before_colon,
        )


def _find_nearby_invalid_tail_after_quoted_item_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_invalid_tail_after_quoted_item(txt):
                return ln, txt
        return None, None


def _line_has_illegal_trailing_comma_before_close(owner: Any, line_text, lineno):
        if not line_text or not lineno:
            return False
        raw = line_text.rstrip()
        if not raw.endswith(","):
            return False
        # If there are already invalid trailing symbols after a completed
        # value/item, prefer the symbol-run diagnostic so the full bad tail
        # is highlighted (not just the final comma).
        if owner._line_has_invalid_trailing_symbols_after_string_value(raw):
            return False
        if owner._line_has_invalid_tail_after_quoted_item(raw):
            return False
        # Comma runs are handled by duplicate-comma diagnostics so only extra
        # commas are marked red and "After" reduces to a single comma.
        if re.search(r',\s*,+\s*$', raw):
            return False
        next_line = owner._next_non_empty_line_number(lineno)
        if not next_line:
            return False
        next_text = owner._line_text(next_line).lstrip()
        return next_text.startswith(("}", "]"))


def _trailing_comma_before_close_col(owner: Any, line_text):
        if not line_text:
            return None
        idx = line_text.rstrip().rfind(",")
        return idx if idx >= 0 else None


def _fix_illegal_trailing_comma_before_close(owner: Any, line_text):
        if not line_text:
            return line_text
        return re.sub(r',\s*$', "", line_text.rstrip())


def _find_nearby_illegal_trailing_comma_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_illegal_trailing_comma_before_close(txt, ln):
                return ln, txt
        return None, None


def _line_has_illegal_comma_after_top_level_close(owner: Any, line_text, lineno):
        return json_top_level_close_service.line_has_illegal_comma_after_top_level_close(
            line_text=line_text,
            lineno=lineno,
            next_non_empty_line_number=owner._next_non_empty_line_number,
        )


def _line_has_top_level_close_symbol_run(owner: Any, line_text, lineno):
        return json_top_level_close_service.line_has_top_level_close_symbol_run(
            line_text=line_text,
            lineno=lineno,
            next_non_empty_line_number=owner._next_non_empty_line_number,
        )


def _find_nearby_top_level_close_symbol_run_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_top_level_close_symbol_run(txt, ln):
                return ln, txt
        return None, None


def _find_nearby_illegal_comma_after_top_level_close_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_illegal_comma_after_top_level_close(txt, ln):
                return ln, txt
        return None, None


def _first_invalid_trailing_symbol_col(owner: Any, line_text, lineno=None):
        return json_scalar_tail_service.first_invalid_trailing_symbol_col(
            line_text=line_text,
            lineno=lineno,
            line_requires_trailing_comma=owner._line_requires_trailing_comma,
        )


def _find_nearby_invalid_trailing_symbols_line(owner: Any, lineno, lookback=2):
        return json_nearby_line_service.find_nearby_line(
            lineno=lineno,
            lookback=lookback,
            get_line_text_fn=lambda ln: owner.text.get(f"{ln}.0", f"{ln}.0 lineend"),
            predicate_fn=lambda txt, **_kwargs: owner._line_has_invalid_trailing_symbols_after_string_value(txt),
            expected_errors=EXPECTED_ERRORS,
            strip_text=True,
        )


def _find_nearby_invalid_symbol_after_closer_line(owner: Any, lineno, lookback=2):
        return json_nearby_line_service.find_nearby_line(
            lineno=lineno,
            lookback=lookback,
            get_line_text_fn=lambda ln: owner.text.get(f"{ln}.0", f"{ln}.0 lineend"),
            predicate_fn=lambda txt, **_kwargs: owner._line_has_invalid_symbol_after_closer(txt),
            expected_errors=EXPECTED_ERRORS,
            strip_text=True,
        )


def _find_nearby_invalid_symbol_after_open_line(owner: Any, lineno, lookback=2):
        return json_nearby_line_service.find_nearby_line(
            lineno=lineno,
            lookback=lookback,
            get_line_text_fn=lambda ln: owner.text.get(f"{ln}.0", f"{ln}.0 lineend"),
            predicate_fn=lambda txt, **_kwargs: owner._line_has_invalid_symbol_after_open(txt),
            expected_errors=EXPECTED_ERRORS,
            strip_text=True,
        )


def _find_nearby_extra_quote_in_value_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except EXPECTED_ERRORS:
                break
            if txt:
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_extra_quote_in_string_value(txt):
                return ln, txt
        return None, None


def _quote_unquoted_value(owner: Any, line_text):
        if not line_text or ":" not in line_text:
            return line_text
        left, right = line_text.split(":", 1)
        right = right.lstrip()
        if not right:
            return line_text

        # Work only on the first value token after "key:" and preserve any tail.
        comma_idx = right.find(",")
        if comma_idx != -1:
            token = right[:comma_idx].strip()
            tail = right[comma_idx:]
        else:
            token = right.strip()
            tail = ""
        if token == "":
            return line_text
        lower = token.lower()

        # Keep valid JSON literals/numbers unquoted.
        if lower in ("true", "false", "null"):
            return line_text
        if re.fullmatch(r"-?\d+(\.\d+)?([eE][+-]?\d+)?", token):
            return line_text
        if token.startswith("{") or token.startswith("[") or token.startswith('"'):
            return line_text

        # Fix common case: missing opening quote (or mismatched quote) around scalar.
        token = token.strip()
        if token.endswith('"') and token.count('"') == 1:
            token = token[:-1]
        # Remove invalid trailing characters before wrapping in quotes
        token = _strip_invalid_trailing_chars(token.strip())
        fixed = f'{left}: "{token}"{tail}'
        return fixed


def _quote_unquoted_scalar_line(owner: Any, line_text):
        if not line_text:
            return line_text
        if ":" in line_text:
            return owner._quote_unquoted_value(line_text)

        stripped = line_text.strip()
        if not stripped:
            return line_text

        has_trailing_comma = stripped.endswith(",")
        token = stripped[:-1].rstrip() if has_trailing_comma else stripped
        if not token:
            return line_text

        lower = token.lower()
        if lower in ("true", "false", "null"):
            return line_text
        if re.fullmatch(r"-?\d+(\.\d+)?([eE][+-]?\d+)?", token):
            return line_text
        if token.startswith("{") or token.startswith("[") or token.startswith("]") or token.startswith("}"):
            return line_text
        if token.startswith('"') and token.endswith('"') and token.count('"') >= 2:
            return line_text

        if token.endswith('"') and token.count('"') == 1:
            token = token[:-1].strip()
        elif token.startswith('"') and token.count('"') == 1:
            token = token[1:].strip()
        else:
            token = token.strip().strip('"')

        # Remove invalid trailing characters before wrapping in quotes
        token = _strip_invalid_trailing_chars(token)
        fixed = f"\"{token}\""
        if has_trailing_comma:
            fixed += ","
        return fixed


def _missing_value_close_quote_insert_col(owner: Any, line_text):
        # Detect: "key": "value,  (missing closing quote before comma/EOL).
        if not line_text:
            return None
        raw = str(line_text)
        # Keep object-key quote diagnostics for key-like forms:
        #   "name: [
        #   "name=: {
        #   "name: "value"
        if re.match(r'^\s*"[A-Za-z_][A-Za-z0-9_]*[^\w"]*:\s*[\[{"]', raw):
            return None

        def _scan_unclosed_quoted_value(value_text, base_col):
            if not value_text.startswith('"'):
                return None
            escape = False
            for idx, ch in enumerate(value_text[1:], start=1):
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    # Already has a valid closing quote.
                    return None
                if ch == ",":
                    return int(base_col + idx)
            if value_text.count('"') == 1:
                return int(base_col + len(value_text.rstrip()))
            return None

        object_value_match = re.match(r'^\s*"[^"]*"\s*:(?P<rest>.*)$', raw)
        if object_value_match:
            rest = object_value_match.group("rest") or ""
            rest_start = int(object_value_match.start("rest"))
            ws_len = len(rest) - len(rest.lstrip(" \t"))
            value_text = rest.lstrip(" \t")
            return _scan_unclosed_quoted_value(value_text, base_col=int(rest_start + ws_len))

        # Array/scalar line form: "value,   (missing closing quote before comma/EOL).
        ws_len = len(raw) - len(raw.lstrip(" \t"))
        value_text = raw.lstrip(" \t")
        return _scan_unclosed_quoted_value(value_text, base_col=int(ws_len))


def _missing_value_open_quote_insert_col(owner: Any, line_text):
        # Detect missing opening quote for scalar values so cursor can stay
        # at the exact insert point instead of jumping to parser fallback lines.
        raw = str(line_text or "")
        if not raw:
            return None
        # Keep literal typo and wrong-token diagnostics in their existing paths.
        if re.match(r'^\s*[A-Za-z_][A-Za-z0-9_]*\s*$', raw):
            return None
        fixed = owner._quote_unquoted_scalar_line(raw)
        if not fixed or fixed == raw:
            return None
        if ":" in raw:
            colon_idx = raw.find(":")
            rest = raw[colon_idx + 1 :]
            ws_len = len(rest) - len(rest.lstrip(" \t"))
            value_text = rest.lstrip(" \t")
            if value_text.startswith('"'):
                return None
            return int(colon_idx + 1 + ws_len)
        for idx, ch in enumerate(raw):
            if not ch.isspace():
                return int(idx)
        return 0


def _find_nearby_missing_value_close_quote_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if str(txt or "").strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            insert_col = owner._missing_value_close_quote_insert_col(txt)
            if insert_col is not None:
                return int(ln), txt, int(insert_col)
        return None, None, None


def _find_nearby_missing_value_open_quote_line(owner: Any, lineno, lookback=3):
        if not lineno:
            return None, None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if str(txt or "").strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            insert_col = owner._missing_value_open_quote_insert_col(txt)
            if insert_col is not None:
                return int(ln), txt, int(insert_col)
        return None, None, None


def _find_wrong_closing_symbol_line(owner: Any, lineno, lookback=2):
        return json_diag_core.find_wrong_closing_symbol_line(
            owner._line_text,
            lineno,
            lookback=lookback,
        )


def _find_missing_list_close_before_object_end(owner: Any, lineno, lookback=4):
        return json_diag_core.find_missing_list_close_before_object_end(
            owner._line_text,
            owner._closest_non_empty_line_before,
            lineno,
            lookback=lookback,
        )


def _missing_list_open_key_line(owner: Any, lineno):
        if not lineno:
            return None
        line = max(lineno - 1, 1)
        while line >= 1:
            text = owner._line_text(line).strip()
            if text.endswith("\":") and not text.endswith("\": {") and not text.endswith("\": ["):
                next_line_num = owner._next_non_empty_line_number(line)
                if next_line_num:
                    next_text = owner._line_text(next_line_num).strip()
                    if next_text.startswith("{"):
                        return line
            line -= 1
        return None


def _find_missing_container_open_after_key_line(owner: Any, lineno, lookback=6):
        """Find a key line that likely needs an opening container token.

        Returns:
            tuple[int|None, str|None]: (line_number, opener) where opener is
            "{" for object-open suggestions or "[" for list-open suggestions.
        """
        if not lineno:
            return None, None
        line = max(lineno - 1, 1)
        checked = 0
        while line >= 1 and checked < lookback:
            text = owner._line_text(line).strip()
            if text:
                checked += 1
                if text.endswith('":'):
                    next_line_num = owner._next_non_empty_line_number(line)
                    if next_line_num:
                        next_text = owner._line_text(next_line_num).strip()
                        if owner._line_looks_like_object_property(next_text):
                            return line, "{"
                        if next_text.startswith('"') or next_text.startswith("{"):
                            return line, "["
            line -= 1
        return None, None


def _find_missing_list_open_after_key_line(owner: Any, lineno, lookback=6):
        line, opener = owner._find_missing_container_open_after_key_line(
            lineno, lookback=lookback
        )
        if opener == "[":
            return line
        return None


def _missing_close_example(owner: Any, msg):
        if msg in ("Expecting ']'", "Unexpected ']'"):
            return "],"
        return "},"


def _is_missing_object_open_at(owner: Any, lineno):
        if not lineno:
            return False
        line_text = owner._line_text(lineno).lstrip()
        if not line_text or ":" not in line_text:
            return False
        prev_line_num = owner._closest_non_empty_line_before(lineno)
        if not prev_line_num:
            return False
        prev_text = owner._line_text(prev_line_num).strip()
        # Do not treat a normal object-member line after "{" as missing object-open.
        # This heuristic is only for property lines that likely lost their leading "{"
        # in list/object boundaries.
        if prev_text in ("[", ",", "],", "},"):
            return True
        return False


def _line_has_missing_open_key_quote(owner: Any, line_text):
        stripped = (line_text or "").lstrip()
        if not stripped or stripped.startswith("\""):
            return False
        if "\":" not in stripped:
            return False
        first = stripped[0]
        return first.isalpha() or first == "_"


def _missing_close_target_line_from_exc(owner: Any, exc, open_bracket, close_bracket):
        line = getattr(exc, "lineno", None)
        if line:
            return line
        return owner._missing_close_target_line(open_bracket, close_bracket)


def _missing_close_target_line_any(owner: Any, exc):
        if owner._is_missing_object_close():
            line, _idx = owner._missing_close_insertion_point("{", "}", exc)
            if line:
                return line
        if owner._is_missing_list_close():
            line, _idx = owner._missing_close_insertion_point("[", "]", exc)
            if line:
                return line
        return None


def _missing_close_insertion_point(owner: Any, open_bracket, close_bracket, exc=None):
        open_line = owner._last_unmatched_bracket_line(open_bracket, close_bracket)
        try:
            max_line = int(owner.text.index("end-1c").split(".")[0])
        except EXPECTED_ERRORS:
            max_line = 1
        if not open_line:
            fallback_line = owner._last_non_empty_line_number() or 1
            return fallback_line, owner.text.index(f"{fallback_line}.0 lineend")

        open_indent = owner._line_indent_width(open_line)
        closer_tokens = [close_bracket]
        # Missing object-close can surface before array closers and missing
        # list-close can surface before object closers.
        if close_bracket == "}":
            closer_tokens.append("]")
        elif close_bracket == "]":
            closer_tokens.append("}")

        candidate = None
        for ln in range(open_line + 1, max_line + 1):
            text = owner._line_text(ln)
            stripped = text.strip()
            if not stripped:
                continue
            if any(stripped.startswith(tok) for tok in closer_tokens):
                indent = owner._line_indent_width(ln)
                if indent <= open_indent:
                    candidate = ln
                    break

        if candidate is not None:
            insert_line = candidate
            if candidate > 1 and not owner._line_text(candidate - 1).strip():
                insert_line = candidate - 1
            closer_indent = owner._line_indent_width(candidate)
            if not owner._line_text(insert_line).strip():
                existing_end = len(owner._line_text(insert_line))
                col = max(existing_end, closer_indent, 0)
            else:
                col = max(closer_indent, 0)
            return insert_line, f"{insert_line}.{col}"

        # No structural closer found: place insertion at trailing EOF.
        last_non_empty = owner._last_non_empty_line_number() or open_line
        trailing_blank = None
        for ln in range(max_line, last_non_empty, -1):
            if owner._line_text(ln).strip():
                break
            trailing_blank = ln
        if trailing_blank is not None:
            existing_end = len(owner._line_text(trailing_blank))
            col = max(existing_end, open_indent, 0)
            return trailing_blank, f"{trailing_blank}.{col}"
        return last_non_empty, owner.text.index(f"{last_non_empty}.0 lineend")


def _find_comma_only_line_before(owner: Any, start_line):
        line = max(start_line - 1, 1)
        while line >= 1:
            try:
                text = owner.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except EXPECTED_ERRORS:
                return None
            if text == ",":
                return line
            line -= 1
        return None


def _find_missing_comma_between_block_values_line(owner: Any, line):
        if not line:
            return None
        current = owner._line_text(line).strip()
        if not current.startswith(("{", "[")):
            return None
        prev_line = owner._closest_non_empty_line_before(line)
        if not prev_line:
            return None
        prev_text = owner._line_text(prev_line).strip()
        if prev_text.endswith(","):
            return None
        if prev_text in ("}", "]"):
            return prev_line
        return None


def _missing_close_target_line(owner: Any, open_bracket, close_bracket):
        open_line = owner._last_unmatched_bracket_line(open_bracket, close_bracket)
        if not open_line:
            return None
        line = open_line + 1
        last_line = int(owner.text.index("end-1c").split(".")[0])
        while line <= last_line:
            try:
                text = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                return open_line
            if text.strip():
                return line
            line += 1
        return open_line


def _is_missing_object_open(owner: Any, exc):
        lineno = getattr(exc, "lineno", None)
        if not lineno:
            return False
        prev_line = owner._previous_non_empty_line(lineno)
        if not prev_line:
            return False
        prev_line_stripped = prev_line.strip()
        return prev_line_stripped.endswith("\":") and not prev_line_stripped.endswith("\": {")


def _is_missing_list_open(owner: Any, exc):
        lineno = getattr(exc, "lineno", None)
        if not lineno:
            return False
        prev_line = owner._previous_non_empty_line(lineno)
        if not prev_line:
            return False
        prev_line_stripped = prev_line.strip()
        if not prev_line_stripped.endswith("\":"):
            return False
        next_line = owner._next_non_empty_line(lineno)
        if not next_line:
            return False
        next_line_stripped = next_line.strip()
        return next_line_stripped.startswith("\"")


def _is_missing_list_open_at_start(owner: Any, exc, allow_any_position=False):
        lineno = getattr(exc, "lineno", None)
        colno = getattr(exc, "colno", None)
        if not allow_any_position:
            if lineno not in (None, 1) or (colno not in (None, 1)):
                return False
        first_line = owner._next_non_empty_line(1)
        if not first_line:
            return False
        first_text = owner._line_text(first_line).lstrip()
        if first_text.startswith("\ufeff"):
            first_text = first_text.lstrip("\ufeff")
        if not first_text:
            return False
        if first_text.startswith("["):
            return False
        if not (first_text.startswith("{") or first_text.startswith("\"")):
            return False
        if allow_any_position:
            return True
        return True


def _missing_list_open_top_level(owner: Any):
        first_line = owner._next_non_empty_line(1)
        if not first_line:
            return False
        first_text = owner._line_text(first_line).lstrip()
        if first_text.startswith("\ufeff"):
            first_text = first_text.lstrip("\ufeff")
        if not first_text or first_text.startswith("["):
            return False
        return first_text.startswith("{") or first_text.startswith("\"")


def _missing_object_open_from_extra_data(owner: Any):
        # For "Extra data", if the first meaningful line looks like an object member
        # (`"key": ...`) then the missing delimiter is '{', not '['.
        if getattr(owner, "_last_json_error_msg", "") != "Extra data":
            return False
        first_line = owner._next_non_empty_line_number(0)
        if not first_line:
            return False
        first_text = owner._line_text(first_line).lstrip()
        if first_text.startswith("\ufeff"):
            first_text = first_text.lstrip("\ufeff").lstrip()
        if not first_text.startswith('"'):
            return False
        return '":' in first_text


def _missing_list_open_from_extra_data(owner: Any):
        # Only treat as missing list open for the "Extra data" parser error.
        if getattr(owner, "_last_json_error_msg", "") != "Extra data":
            return False
        if owner._missing_object_open_from_extra_data():
            return False
        first_char = owner._first_non_ws_char()
        if not first_char or first_char == "[":
            return False
        return True


def _missing_object_example(owner: Any, lineno):
        prev_line = owner._previous_non_empty_line(lineno)
        if not prev_line:
            return "\"data\": {"
        prev_line_stripped = prev_line.strip()
        if prev_line_stripped.endswith("\":"):
            return prev_line_stripped + " {"
        return "\"data\": {"


def _quote_property_name(owner: Any, line_text):
        if ":" in line_text:
            left, right = line_text.split(":", 1)
            left = left.strip()
            # Normalize wrong/missing key quote characters before wrapping.
            left = left.strip().strip(",").strip()
            if left and not left.startswith('"') and left.endswith('"'):
                first = left[0]
                if (not first.isalnum()) and first != "_":
                    left = left[1:]
            left = left.strip().strip('"').strip("'").strip("`")
            left = f"\"{left}\""
            right = right.strip()
            return f"{left}: {right}"
        return "\"key\": \"value\""


def _fix_missing_at(owner: Any, value, domain_roots=None):
        if "@" in value:
            return value
        domains = [
            "gomail.com",
            "gmail.com",
            "yahoo.com",
            "outlook.com",
            "hotmail.com",
            "icloud.com",
        ]
        for domain in domains:
            idx = value.find(domain)
            if idx != -1:
                return value[:idx] + "@" + value[idx:]
        parts = value.split(".")
        if len(parts) == 2:
            left, tld = parts
            if domain_roots:
                best = None
                for root in domain_roots:
                    if left.endswith(root):
                        if best is None or len(root) > len(best):
                            best = root
                if best:
                    local = left[: -len(best)]
                    if local:
                        return f"{local}@{best}.{tld}"
        if len(parts) == 3:
            part0, part1, tld = parts
            if domain_roots:
                best = None
                for root in domain_roots:
                    if part1.endswith(root):
                        if best is None or len(root) > len(best):
                            best = root
                if best:
                    local_tail = part1[: -len(best)].rstrip(".")
                    local = part0 + (("." + local_tail) if local_tail else "")
                    return f"{local}@{best}.{tld}"
            for domlen in (5, 4, 6, 3):
                if len(part1) - domlen >= 3:
                    local_tail = part1[: -domlen]
                    domain = part1[-domlen:] + "." + tld
                    return f"{part0}.{local_tail}@{domain}"
        if len(parts) >= 3:
            return ".".join(parts[:-2]) + "@" + ".".join(parts[-2:])
        last_dot = value.rfind(".")
        if last_dot > 0:
            return value[:last_dot] + "@" + value[last_dot + 1 :]
        # Non-email strings (for example IBAN-like values) should pass through untouched.
        return value


def _format_phone(owner: Any, value):
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) != 10:
            return None
        return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"


def _find_phone_format_issue(owner: Any):
        try:
            text = owner.text.get("1.0", "end-1c")
        except EXPECTED_ERRORS:
            return None
        for idx, line_text in enumerate(text.splitlines(), start=1):
            match = owner.PHONE_FIELD_PATTERN.search(line_text)
            if not match:
                continue
            value = match.group(1)
            if not value:
                continue
            formatted = owner._format_phone(value)
            if not formatted:
                continue
            if value == formatted:
                continue
            before_line = line_text.strip()
            after_line = line_text[: match.start(1)] + formatted + line_text[match.end(1) :]
            return idx, match.start(1), match.end(1), before_line, after_line.strip()
        return None


def _fix_missing_space_after_colon(owner: Any, line_text):
        if not line_text:
            return line_text
        return re.sub(r'^(\s*"[^"]+"\s*):\s*(\S.*)$', r"\1: \2", line_text.rstrip(), count=1)


def _find_json_spacing_issue(owner: Any):
        """Return first missing-space-after-colon style issue in JSON text."""
        try:
            text = owner.text.get("1.0", "end-1c")
        except EXPECTED_ERRORS:
            return None
        for line_no, line_text in enumerate(text.splitlines(), start=1):
            m = re.match(r'^(?P<head>\s*"[^"]+"\s*):(?P<tail>\S.*)$', line_text)
            if not m:
                continue
            head = m.group("head") or ""
            tail = m.group("tail") or ""
            if not tail:
                continue
            before = line_text.strip()
            after = owner._fix_missing_space_after_colon(line_text).strip()
            start_col = len(head) + 1
            end_col = start_col + 1
            return line_no, start_col, end_col, before, after
        return None


def _find_missing_email_at(owner: Any):
        try:
            text = owner.text.get("1.0", "end-1c")
        except EXPECTED_ERRORS:
            return None
        lines = text.splitlines()
        domain_roots = set()
        for line_text in lines:
            m = owner.EMAIL_FIELD_PATTERN.search(line_text)
            if not m:
                continue
            val = m.group(2)
            if "@" not in val:
                continue
            domain = val.split("@", 1)[1]
            parts = domain.split(".")
            if len(parts) >= 2:
                domain_roots.add(parts[-2])
        for idx, line_text in enumerate(lines, start=1):
            match = owner.EMAIL_FIELD_PATTERN.search(line_text)
            if not match:
                continue
            value = match.group(2)
            if not value or "@" in value:
                continue
            fixed = owner._fix_missing_at(value, domain_roots.union(owner.KNOWN_EMAIL_DOMAIN_ROOTS))
            # Prefer exact known domain match if present in value.
            for domain in sorted(owner.KNOWN_EMAIL_DOMAINS, key=len, reverse=True):
                if domain in value:
                    fixed = value.replace(domain, "@" + domain, 1)
                    break
            before_line = line_text.strip()
            after_line = line_text[: match.start(2)] + fixed + line_text[match.end(2) :]
            return idx, match.start(2), match.end(2), before_line, after_line.strip()
        return None


def _path_targets_email(owner: Any, path):
        if not isinstance(path, list) or not path:
            return False
        lowered = [p.lower() for p in path if isinstance(p, str)]
        if not lowered:
            return False
        key = lowered[-1]
        if key in ("email", "from", "to"):
            return True
        # Nested forms like: ... email.address / email.value
        if key in ("address", "value") and len(lowered) >= 2 and lowered[-2] == "email":
            return True
        return False


def _looks_like_email_candidate(owner: Any, value):
        value = (value or "").strip()
        if not value:
            return False
        if "@" in value:
            return True
        if "." not in value:
            return False
        return re.search(r"[A-Za-z]", value) is not None


def _should_validate_email_path_value(owner: Any, path, value):
        lowered = [p.lower() for p in path if isinstance(p, str)]
        if not lowered:
            return False
        key = lowered[-1]
        if key == "email":
            return True
        if key in ("address", "value") and len(lowered) >= 2 and lowered[-2] == "email":
            return True
        if key in ("from", "to"):
            # "from"/"to" appears in non-email objects (e.g. bank transactions).
            return owner._looks_like_email_candidate(value)
        return False


def _iter_candidate_email_values(owner: Any, node, rel_path=None):
        if rel_path is None:
            rel_path = []
        if isinstance(node, dict):
            for k, v in node.items():
                yield from owner._iter_candidate_email_values(v, rel_path + [k])
            return
        if isinstance(node, list):
            for i, v in enumerate(node):
                yield from owner._iter_candidate_email_values(v, rel_path + [i])
            return
        if (
            isinstance(node, str)
            and owner._path_targets_email(rel_path)
            and owner._should_validate_email_path_value(rel_path, node)
        ):
            yield rel_path, node


def _find_invalid_email_in_value(owner: Any, base_path, value):
        if (
            isinstance(value, str)
            and owner._path_targets_email(base_path)
            and owner._should_validate_email_path_value(base_path, value)
        ):
            issue = owner._validate_email_address(value)
            if issue:
                return base_path, value, issue
        if isinstance(value, (dict, list)):
            for rel_path, email_val in owner._iter_candidate_email_values(value):
                issue = owner._validate_email_address(email_val)
                if issue:
                    return list(base_path) + list(rel_path), email_val, issue
        return None


def _suggest_email_for_malformed(owner: Any, value):
        value = (value or "").strip()
        if "@" not in value or value.count("@") != 1:
            return "<name>@<domain.tld>"
        local, domain = value.split("@", 1)
        parts = domain.split(".")
        if len(parts) < 2:
            return "<name>@<domain.tld>"
        sub_prefix = ".".join(parts[:-2]).strip(".")
        sld = parts[-2]
        tld = parts[-1]
        # Rebuild broken short SLDs by borrowing the missing prefix from local part.
        if len(sld) < 2:
            best_prefix_fix = None
            best_prefix_len = -1
            for root in sorted(owner.KNOWN_EMAIL_DOMAIN_ROOTS, key=len, reverse=True):
                if not root.endswith(sld):
                    continue
                missing_prefix = root[: len(root) - len(sld)] if sld else root
                if not missing_prefix:
                    continue
                if not local.lower().endswith(missing_prefix):
                    continue
                cand_local = local[: len(local) - len(missing_prefix)]
                if not cand_local:
                    continue
                if not re.fullmatch(r"^[A-Za-z0-9._%+\-]+$", cand_local):
                    continue
                cand_domain = f"{root}.{tld}"
                if sub_prefix:
                    cand_domain = f"{sub_prefix}.{cand_domain}"
                if not owner._is_valid_email_domain(cand_domain):
                    continue
                if len(root) > best_prefix_len:
                    best_prefix_len = len(root)
                    best_prefix_fix = f"{cand_local}@{cand_domain}"
            if best_prefix_fix:
                return best_prefix_fix

        merged_token = local + sld
        local_re = re.compile(r"^[A-Za-z0-9._%+\-]+$")
        best = None
        best_score = -10**9
        original_len = len(local)
        for cut in range(1, len(merged_token)):
            cand_local = merged_token[:cut]
            cand_sld = merged_token[cut:]
            if not local_re.fullmatch(cand_local):
                continue
            cand_domain = f"{cand_sld}.{tld}"
            if sub_prefix:
                cand_domain = f"{sub_prefix}.{cand_domain}"
            if not owner._is_valid_email_domain(cand_domain):
                continue
            score = 0.0
            if cand_sld.lower() in owner.KNOWN_EMAIL_DOMAIN_ROOTS:
                score += 500.0
            score += owner._best_domain_root_similarity(cand_sld) * 100.0
            score -= abs(cut - original_len) * 2.0
            if score > best_score:
                best_score = score
                best = f"{cand_local}@{cand_domain}"
        return best if best else "<name>@<domain.tld>"


def _validate_email_address(owner: Any, value):
        value = (value or "").strip()
        if not value:
            return None
        if "@" not in value:
            fixed = owner._fix_missing_at(value, owner.KNOWN_EMAIL_DOMAIN_ROOTS)
            if fixed == value or "@" not in fixed:
                return {
                    "message": "Invalid Entry: malformed email address.",
                    "log_msg": "Malformed email format",
                    "note": "invalid_email_format",
                    "suggested": owner._suggest_email_for_malformed(value),
                }
            return {
                "message": 'Invalid Entry: add "@" to the email address.',
                "log_msg": "Missing '@' in email",
                "note": "missing_email_at",
                "suggested": fixed,
            }

        if value.count("@") != 1:
            return {
                "message": "Invalid Entry: malformed email address.",
                "log_msg": "Malformed email format",
                "note": "invalid_email_format",
                "suggested": owner._suggest_email_for_malformed(value),
            }

        local, domain = value.split("@", 1)
        local_re = re.compile(r"^[A-Za-z0-9._%+\-]+$")
        if not local or not domain or not local_re.fullmatch(local) or not owner._is_valid_email_domain(domain):
            return {
                "message": "Invalid Entry: malformed email address.",
                "log_msg": "Malformed email format",
                "note": "invalid_email_format",
                "suggested": owner._suggest_email_for_malformed(value),
            }

        domain_lower = domain.lower()
        if domain_lower not in owner.KNOWN_EMAIL_DOMAINS:
            suggestion = owner._suggest_known_domain_from_local_and_domain(local, domain_lower)
            if not suggestion:
                # NOTE: Keep this as the final fallback; fuzzy matching is expensive in hot parse loops.
                near_match = difflib.get_close_matches(
                    domain_lower,
                    sorted(owner.KNOWN_EMAIL_DOMAINS),
                    n=1,
                    cutoff=0.72,
                )
                if near_match:
                    suggestion = f"{local}@{near_match[0]}"
            return {
                "message": "Invalid Entry: unknown email domain.",
                "log_msg": "Unknown email domain",
                "note": "unknown_email_domain",
                "suggested": suggestion or "<name>@<domain.tld>",
            }

        return None


def _is_valid_email_domain(owner: Any, domain):
        if not domain or "." not in domain:
            return False
        parts = domain.split(".")
        if len(parts) < 2:
            return False
        # Catch obvious misplaced-@ cases like "x@l.net".
        if len(parts[-2]) < 2:
            return False
        tld = parts[-1]
        if len(tld) < 2 or not tld.isalpha():
            return False
        label_re = re.compile(r"^[A-Za-z0-9-]+$")
        for part in parts:
            if not part:
                return False
            if part.startswith("-") or part.endswith("-"):
                return False
            if not label_re.fullmatch(part):
                return False
        return True


def _find_invalid_email_format_issue(owner: Any):
        try:
            text = owner.text.get("1.0", "end-1c")
        except EXPECTED_ERRORS:
            return None
        for idx, line_text in enumerate(text.splitlines(), start=1):
            match = owner.EMAIL_FIELD_PATTERN.search(line_text)
            if not match:
                continue
            value = (match.group(2) or "").strip()
            if not value or "@" not in value:
                continue
            issue = owner._validate_email_address(value)
            if not issue:
                continue
            before_line = line_text.strip()
            suggested = issue["suggested"]
            after_line = line_text[: match.start(2)] + suggested + line_text[match.end(2) :]
            return (
                idx,
                match.start(2),
                match.end(2),
                before_line,
                after_line.strip(),
                issue["message"],
                issue["log_msg"],
                issue["note"],
            )
        return None


def _fix_missing_quote(owner: Any, line_text):
        if not line_text:
            return "\"key\": \"value\""
        if line_text.count("\"") % 2 == 0:
            return line_text
        object_value_match = re.match(r'^(?P<key>\s*"[^"]*"\s*):(?P<rest>.*)$', str(line_text))
        if object_value_match:
            key_part = object_value_match.group("key") or ""
            rest = object_value_match.group("rest") or ""
            key_part = key_part.strip().strip(",")
            rest = rest.strip().rstrip(",")
            if rest == "\"":
                rest = "\"\""
            elif rest.startswith("\"") and rest.count("\"") == 1:
                # Remove invalid trailing characters before closing the quote
                rest = rest[1:]  # Remove opening quote
                rest = _strip_invalid_trailing_chars(rest)
                rest = "\"" + rest + "\""
            if not key_part.endswith("\""):
                key_part = key_part + "\""
            if not key_part.startswith("\""):
                key_part = "\"" + key_part
            return f"{key_part}: {rest}" + ("," if line_text.strip().endswith(",") else "")
        stripped = line_text.rstrip()
        if stripped.endswith(","):
            base = stripped[:-1]
            # Remove invalid tail symbols before closing the missing quote.
            m = re.match(r'^(?P<head>\s*")(?P<body>.*)$', base)
            if m:
                head = m.group("head") or ""
                body = _strip_invalid_trailing_chars((m.group("body") or "").rstrip())
                return head + body + "\"" + ("," if line_text.strip().endswith(",") else "")
            return _strip_invalid_trailing_chars(base.rstrip()) + "\"" + (
                "," if line_text.strip().endswith(",") else ""
            )
        return stripped + "\""


def _unclosed_quoted_value_invalid_tail_span(owner: Any, line_text):
        # Detect unclosed quoted scalar values with invalid trailing symbols
        # before comma/EOL (for example: "hackhub.net:,).
        raw = str(line_text or "")
        if not raw:
            return None
        # Keep object-key quote diagnostics for key-like forms:
        #   "name: [
        #   "name: {
        #   "name: "value"
        if re.match(r'^\s*"[A-Za-z_][A-Za-z0-9_]*[^\w"]*:\s*[\[{"]', raw):
            return None

        object_value_match = re.match(r'^\s*"[^"]*"\s*:(?P<rest>.*)$', raw)
        if object_value_match:
            rest = object_value_match.group("rest") or ""
            rest_start = int(object_value_match.start("rest"))
            ws_len = len(rest) - len(rest.lstrip(" \t"))
            value_text = rest.lstrip(" \t")
            base_col = int(rest_start + ws_len)
        else:
            ws_len = len(raw) - len(raw.lstrip(" \t"))
            value_text = raw.lstrip(" \t")
            base_col = int(ws_len)

        if not value_text.startswith('"'):
            return None

        escape = False
        comma_idx = None
        for idx, ch in enumerate(value_text[1:], start=1):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                return None
            if ch == ",":
                comma_idx = idx
                break
        stop_idx = int(comma_idx) if comma_idx is not None else int(len(value_text.rstrip()))
        if stop_idx <= 1:
            return None

        body = value_text[1:stop_idx]
        body_rstrip = body.rstrip()
        if not body_rstrip:
            return None
        trimmed = _strip_invalid_trailing_chars(body_rstrip)
        if len(trimmed) >= len(body_rstrip):
            return None
        invalid_start = len(trimmed)
        invalid_end = len(body_rstrip)
        return (
            int(base_col + 1 + invalid_start),
            int(base_col + 1 + invalid_end),
        )


def _find_nearby_unclosed_quoted_value_invalid_tail_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if str(txt or "").strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            span = owner._unclosed_quoted_value_invalid_tail_span(txt)
            if span:
                return int(ln), txt, span
        return None, None, None


def _comma_example_line(owner: Any, lineno):
        if not lineno:
            return "\"item1\",\n\"item2\""
        target_line = max(lineno - 1, 1)
        try:
            line_text = owner.text.get(f"{target_line}.0", f"{target_line}.0 lineend").strip()
        except EXPECTED_ERRORS:
            line_text = ""
        if not line_text:
            return "\"item1\",\n\"item2\""
        if not line_text.endswith(","):
            line_text = line_text.rstrip()
            line_text = line_text + ","
        return line_text


def _symbol_error_focus_index(owner: Any, start_index, end_index):
        try:
            segment = owner.text.get(start_index, end_index)
            if not segment:
                return end_index
            trimmed = len(segment.rstrip())
            if trimmed <= 0:
                return end_index
            return owner.text.index(f"{start_index} +{trimmed}c")
        except EXPECTED_ERRORS:
            return end_index


# --- Merged from json_diagnostics_service.py ---
"""JSON diagnostics helpers delegated from JsonEditor."""


import difflib
import json
import os
import re
from datetime import datetime
from typing import Any

from core import json_diagnostics as json_diag_core
from core import json_error_diagnostics_core
from core import json_error_highlight_core
from core.exceptions import EXPECTED_ERRORS
import core.domain_impl.support.error_overlay_service as error_overlay_service
import core.domain_impl.support.highlight_label_service as highlight_label_service
import core.domain_impl.infra.input_mode_diag_service as input_mode_diag_service
from core.domain_impl.json import json_diagnostics_core as json_closer_symbol_service
from core.domain_impl.json import json_diagnostics_core as json_colon_comma_service
from core.domain_impl.json import json_io_core as json_edit_flow_service
from core.domain_impl.json import json_diagnostics_core as json_error_diag_service
from core.domain_impl.json import json_view_core as json_error_highlight_render_service
from core.domain_impl.json import json_diagnostics_core as json_nearby_line_service
from core.domain_impl.json import json_diagnostics_core as json_open_symbol_service
from core.domain_impl.json import json_diagnostics_core as json_parse_feedback_service
from core.domain_impl.json import json_diagnostics_core as json_property_key_rule_service
from core.domain_impl.json import json_diagnostics_core as json_quoted_item_tail_service
from core.domain_impl.json import json_diagnostics_core as json_scalar_tail_service
from core.domain_impl.json import json_diagnostics_core as json_top_level_close_service
from core.domain_impl.json import json_diagnostics_core as json_validation_feedback_service
import core.domain_impl.ui.tree_view_service as tree_view_service
def _configure_json_lock_tags(owner: Any):
        palette = owner._json_lock_tag_palette()
        try:
            owner.text.tag_config("json_brace_token", foreground="#54d5ff")
            owner.text.tag_config("json_bracket_token", foreground="#ff7ac8")
            owner.text.tag_config("json_bool_true", foreground="#5fa8ff")
            owner.text.tag_config("json_bool_false", foreground="#ff9ea1")
            owner.text.tag_config("json_value_green", foreground="#49c979")
            owner.text.tag_config("json_property_key", foreground=palette["fg"])
            owner.text.tag_config("json_locked_key", foreground=palette["fg"])
            owner.text.tag_config(
                "json_locked_block",
                foreground=palette["fg"],
                background=palette["block_bg"],
            )
            owner.text.tag_config("json_xy_key", foreground="#b6ff3b")
            owner.text.tag_raise("json_brace_token")
            owner.text.tag_raise("json_bracket_token")
            owner.text.tag_raise("json_bool_true")
            owner.text.tag_raise("json_bool_false")
            owner.text.tag_raise("json_value_green")
            owner.text.tag_raise("json_locked_key")
            owner.text.tag_raise("json_property_key")
            owner.text.tag_raise("json_xy_key")
        except EXPECTED_ERRORS:
            return


def _clear_json_lock_highlight(owner: Any):
        try:
            owner.text.tag_remove("json_brace_token", "1.0", "end")
            owner.text.tag_remove("json_bracket_token", "1.0", "end")
            owner.text.tag_remove("json_bool_true", "1.0", "end")
            owner.text.tag_remove("json_bool_false", "1.0", "end")
            owner.text.tag_remove("json_value_green", "1.0", "end")
            owner.text.tag_remove("json_property_key", "1.0", "end")
            owner.text.tag_remove("json_locked_key", "1.0", "end")
            owner.text.tag_remove("json_locked_block", "1.0", "end")
            owner.text.tag_remove("json_xy_key", "1.0", "end")
        except EXPECTED_ERRORS:
            return


def _set_json_text_editable(owner: Any, editable=True):
        text = getattr(owner, "text", None)
        if text is None:
            return
        target_state = "normal" if editable else "disabled"
        try:
            if str(text.cget("state")) != target_state:
                text.configure(state=target_state)
        except EXPECTED_ERRORS:
            return


def _tag_json_locked_key_occurrences(owner: Any, key_name):
        token = f'"{key_name}"'
        malformed_missing_close_quote = f'"{key_name}:'
        malformed_missing_open_quote = f'{key_name}"'
        index = "1.0"
        while True:
            try:
                hit = owner.text.search(token, index, stopindex="end", nocase=True)
            except EXPECTED_ERRORS:
                hit = ""
            if not hit:
                break
            try:
                end = f"{hit}+{len(token)}c"
                if owner._json_token_followed_by_colon(end):
                    owner.text.tag_add("json_locked_key", hit, end)
            except EXPECTED_ERRORS:
                break
            index = end
        # Keep lock-label context alive while users fix half-typed key quotes.
        for malformed_token in (malformed_missing_close_quote, malformed_missing_open_quote):
            index = "1.0"
            while True:
                try:
                    hit = owner.text.search(malformed_token, index, stopindex="end", nocase=True)
                except EXPECTED_ERRORS:
                    hit = ""
                if not hit:
                    break
                try:
                    if malformed_token.endswith(":"):
                        end = f"{hit}+{len(malformed_token) - 1}c"
                    else:
                        end = f"{hit}+{len(malformed_token)}c"
                    if owner._json_token_followed_by_colon(end):
                        owner.text.tag_add("json_locked_key", hit, end)
                except EXPECTED_ERRORS:
                    break
                index = end


def _tag_json_xy_key_occurrences(owner: Any, key_name):
        token = f'"{key_name}"'
        index = "1.0"
        while True:
            try:
                hit = owner.text.search(token, index, stopindex="end", nocase=False)
            except EXPECTED_ERRORS:
                hit = ""
            if not hit:
                break
            try:
                end = f"{hit}+{len(token)}c"
                if owner._json_token_followed_by_colon(end):
                    owner.text.tag_add("json_xy_key", hit, end)
            except EXPECTED_ERRORS:
                break
            index = end


def _should_batch_tag_locked_keys(owner: Any, key_names):
        if not key_names:
            return False
        if len(tuple(key_names)) < 12:
            return False
        try:
            if getattr(owner, "error_overlay", None) is not None:
                return False
        except EXPECTED_ERRORS:
            return False
        try:
            raw = owner.text.get("1.0", "end-1c")
        except EXPECTED_ERRORS:
            return False
        if len(raw or "") < 4000:
            return False
        return True


def _tag_json_key_occurrences_batch(owner: Any, locked_key_names, xy_key_names=(), line_limit=None):
        # NOTE: Keep this batch path. Per-key search loops caused visible stalls on large saves.
        locked_targets = {
            str(name or "").strip().casefold()
            for name in tuple(locked_key_names or ())
            if str(name or "").strip()
        }
        xy_targets = {
            str(name or "").strip()
            for name in tuple(xy_key_names or ())
            if str(name or "").strip()
        }
        if not locked_targets and not xy_targets:
            return
        try:
            raw = owner.text.get("1.0", "end-1c")
        except EXPECTED_ERRORS:
            return
        line_no = 1
        key_pattern = re.compile(r'"([^"\r\n:]+)"\s*:')
        max_lines = int(line_limit or 0)
        for line_text in str(raw or "").splitlines():
            if max_lines and line_no > max_lines:
                break
            for hit in key_pattern.finditer(line_text):
                key_name = str(hit.group(1) or "")
                locked_match = key_name.casefold() in locked_targets
                xy_match = key_name in xy_targets
                if not locked_match and not xy_match:
                    continue
                key_start = int(hit.start(0))
                key_end = int(key_start + len(key_name) + 2)
                try:
                    start = f"{line_no}.{key_start}"
                    end = f"{line_no}.{key_end}"
                    if locked_match:
                        owner.text.tag_add("json_locked_key", start, end)
                    if xy_match:
                        owner.text.tag_add("json_xy_key", start, end)
                except EXPECTED_ERRORS:
                    continue
            line_no += 1


def _tag_json_string_value_literals(owner: Any, line_limit=None):
        try:
            raw = owner.text.get("1.0", "end-1c")
        except EXPECTED_ERRORS:
            return
        line_no = 1
        max_lines = int(line_limit or 0)
        token_pattern = re.compile(r'"([^"\\]|\\.)*"')
        for line_text in str(raw or "").splitlines():
            if max_lines and line_no > max_lines:
                break
            for hit in token_pattern.finditer(line_text):
                start_col = int(hit.start(0))
                end_col = int(hit.end(0))
                next_nonspace = ""
                for ch in line_text[end_col:]:
                    if ch in (" ", "\t", "\r", "\n"):
                        continue
                    next_nonspace = ch
                    break
                is_key = next_nonspace == ":"
                if is_key:
                    continue
                try:
                    owner.text.tag_add("json_value_green", f"{line_no}.{start_col}", f"{line_no}.{end_col}")
                except EXPECTED_ERRORS:
                    continue
            line_no += 1


def _tag_json_brace_tokens(owner: Any, line_limit=None):
        try:
            raw = owner.text.get("1.0", "end-1c")
        except EXPECTED_ERRORS:
            return
        line_no = 1
        max_lines = int(line_limit or 0)
        for line_text in str(raw or "").splitlines():
            if max_lines and line_no > max_lines:
                break
            in_string = False
            escaped = False
            col_no = 0
            for ch in line_text:
                if escaped:
                    escaped = False
                    col_no += 1
                    continue
                if ch == "\\" and in_string:
                    escaped = True
                    col_no += 1
                    continue
                if ch == '"':
                    in_string = not in_string
                    col_no += 1
                    continue
                if not in_string and ch in ("{", "}", "[", "]"):
                    try:
                        token_tag = "json_brace_token" if ch in ("{", "}") else "json_bracket_token"
                        owner.text.tag_add(token_tag, f"{line_no}.{col_no}", f"{line_no}.{col_no + 1}")
                    except EXPECTED_ERRORS:
                        pass
                col_no += 1
            line_no += 1


def _tag_json_boolean_literals(owner: Any, line_limit=None):
        try:
            raw = owner.text.get("1.0", "end-1c")
        except EXPECTED_ERRORS:
            return
        line_no = 1
        max_lines = int(line_limit or 0)
        token_pattern = re.compile(r"\b(true|false)\b")
        for line_text in str(raw or "").splitlines():
            if max_lines and line_no > max_lines:
                break
            in_string = False
            escaped = False
            string_mask = [False] * len(line_text)
            for idx, ch in enumerate(line_text):
                string_mask[idx] = in_string
                if escaped:
                    escaped = False
                    continue
                if ch == "\\" and in_string:
                    escaped = True
                    continue
                if ch == '"':
                    in_string = not in_string
            for hit in token_pattern.finditer(line_text):
                start_col = int(hit.start(0))
                end_col = int(hit.end(0))
                inside_string = any(string_mask[idx] for idx in range(start_col, min(end_col, len(string_mask))))
                if inside_string:
                    continue
                token = str(hit.group(1) or "")
                tag_name = "json_bool_true" if token == "true" else "json_bool_false"
                try:
                    owner.text.tag_add(tag_name, f"{line_no}.{start_col}", f"{line_no}.{end_col}")
                except EXPECTED_ERRORS:
                    continue
            line_no += 1


def _tag_json_property_keys(owner: Any, line_limit=None):
        try:
            raw = owner.text.get("1.0", "end-1c")
        except EXPECTED_ERRORS:
            return
        line_no = 1
        max_lines = int(line_limit or 0)
        key_pattern = re.compile(r'"([^"\\]|\\.)*"\s*:')
        for line_text in str(raw or "").splitlines():
            if max_lines and line_no > max_lines:
                break
            for hit in key_pattern.finditer(line_text):
                token = str(hit.group(0) or "")
                colon_index = token.rfind(":")
                if colon_index <= 0:
                    continue
                end_col = int(hit.start(0) + colon_index)
                start_col = int(hit.start(0))
                while end_col > start_col and line_text[end_col - 1] in (" ", "\t"):
                    end_col -= 1
                try:
                    owner.text.tag_add("json_property_key", f"{line_no}.{start_col}", f"{line_no}.{end_col}")
                except EXPECTED_ERRORS:
                    continue
            line_no += 1


def _json_literal_offsets_after_key(owner: Any, key_end_index, literal_token, lookahead_chars=120, ignore_case=False):
        text = getattr(owner, "text", None)
        token = str(literal_token or "")
        if text is None or not token:
            return None
        try:
            tail = owner.text.get(key_end_index, f"{key_end_index}+{max(1, int(lookahead_chars))}c")
        except EXPECTED_ERRORS:
            return None
        if not tail:
            return None
        i = 0
        while i < len(tail) and tail[i] in (" ", "\t", "\r", "\n"):
            i += 1
        if i >= len(tail) or tail[i] != ":":
            return None
        i += 1
        while i < len(tail) and tail[i] in (" ", "\t", "\r", "\n"):
            i += 1
        if i >= len(tail):
            return None
        candidate = tail[i:i + len(token)]
        if ignore_case:
            if candidate.casefold() != token.casefold():
                return None
        else:
            if candidate != token:
                return None
        end = i + len(token)
        if end < len(tail):
            next_ch = tail[end]
            if next_ch not in (" ", "\t", "\r", "\n", ",", "}", "]"):
                return None
        return i, end


def _tag_json_locked_value_occurrences(owner: Any, field_name, literal_value, ignore_case=False):
        key_token = json.dumps(str(field_name), ensure_ascii=False)
        value_token = json.dumps(literal_value, ensure_ascii=False)
        index = "1.0"
        while True:
            try:
                hit = owner.text.search(key_token, index, stopindex="end", nocase=True)
            except EXPECTED_ERRORS:
                hit = ""
            if not hit:
                break
            try:
                key_end = f"{hit}+{len(key_token)}c"
                offsets = owner._json_literal_offsets_after_key(
                    key_end,
                    value_token,
                    ignore_case=bool(ignore_case),
                )
                if offsets is not None:
                    value_start = f"{key_end}+{int(offsets[0])}c"
                    value_end = f"{key_end}+{int(offsets[1])}c"
                    owner.text.tag_add("json_locked_key", value_start, value_end)
            except EXPECTED_ERRORS:
                break
            index = key_end


def _apply_json_view_lock_state(owner: Any, path):
        owner._clear_json_lock_highlight()
        owner._set_json_text_editable(True)
        owner._apply_json_view_key_highlights(path)
        owner._apply_json_view_value_highlights(path)


def _describe(owner: Any, value):
        if isinstance(value, dict):
            return f"dict ({len(value)} keys)"
        if isinstance(value, list):
            return f"list ({len(value)} items)"
        return f"{type(value).__name__}"


def _extract_key_name_from_diag_line(owner: Any, line_text):
        raw = str(line_text or "").strip()
        if not raw:
            return ""
        m = re.search(r'"([^"\r\n:]+)"\s*:', raw)
        if m:
            return str(m.group(1) or "").strip()
        m = re.search(r'([A-Za-z_][A-Za-z0-9_]*)"\s*:', raw)
        if m:
            return str(m.group(1) or "").strip()
        m = re.search(r'"([A-Za-z_][A-Za-z0-9_]*)\s*:', raw)
        if m:
            return str(m.group(1) or "").strip()
        return ""


def _find_lock_anchor_index(owner: Any, field_name, preferred_index=None):
        token = f'"{str(field_name or "").strip()}"'
        if token == '""':
            token = ""
        anchor_idx = str(preferred_index or "")
        try:
            if anchor_idx:
                anchor_idx = str(owner.text.index(anchor_idx))
        except EXPECTED_ERRORS:
            pass
        if not token:
            return anchor_idx
        try:
            if anchor_idx:
                backward_hit = owner.text.search(
                    token,
                    anchor_idx,
                    stopindex="1.0",
                    nocase=True,
                    backwards=True,
                )
                if backward_hit:
                    return backward_hit
                forward_hit = owner.text.search(token, anchor_idx, stopindex="end", nocase=True)
                if forward_hit:
                    return forward_hit
        except EXPECTED_ERRORS:
            pass
        try:
            hit = owner.text.search(token, "1.0", stopindex="end", nocase=True)
            if hit:
                return hit
        except EXPECTED_ERRORS:
            pass
        return anchor_idx


def _diag_line_mentions_locked_field(owner: Any, line_no, field_name):
        if not line_no or not field_name:
            return False
        try:
            line_text = str(owner._line_text(int(line_no)) or "")
        except EXPECTED_ERRORS:
            return False
        if not line_text.strip():
            return False
        field_lookup = str(field_name).strip().casefold()
        line_lookup = line_text.casefold()
        if field_lookup in line_lookup:
            return True
        compact_field = "".join(ch for ch in field_lookup if ch.isalnum())
        compact_line = "".join(ch for ch in line_lookup if ch.isalnum())
        if compact_field and compact_field in compact_line:
            return True
        return False


def _example_for_error(owner: Any, exc):
        lineno = getattr(exc, "lineno", None)
        line_text = ""
        if lineno:
            try:
                line_text = owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()
            except EXPECTED_ERRORS:
                line_text = ""

        msg = getattr(exc, "msg", None)
        if msg == "Expecting ',' delimiter":
            if owner._is_missing_object_open_at(lineno):
                return "{"
            if owner._is_missing_object_open(exc):
                return owner._missing_object_example(lineno)
            if owner._is_missing_object_close():
                return owner._missing_close_example("Expecting '}'")
            if owner._is_missing_list_close():
                return owner._missing_close_example("Expecting ']'")
            return owner._comma_example_line(lineno)

        if msg == "Expecting property name enclosed in double quotes":
            if line_text:
                return line_text
            return "\"key\": \"value\""

        if msg == "Expecting ':' delimiter":
            if line_text:
                return owner._missing_colon_example(line_text)
            return "\"key\": \"value\""

        if msg and msg.startswith("Invalid control character"):
            if line_text:
                return owner._fix_missing_quote(line_text)
            return "\"key\": \"value\""

        if msg in ("Expecting ']'", "Expecting '}'"):
            return owner._missing_close_example(msg)

        if msg == "Expecting value":
            if owner._is_missing_list_open_at_start(exc):
                return "["
            if owner._is_missing_list_close():
                return owner._missing_close_example("Expecting ']'")
            if owner._is_missing_object_close():
                return owner._missing_close_example("Expecting '}'")
            if owner._is_missing_list_open(exc):
                return "\"items\": ["
            if owner._is_missing_object_open(exc):
                return "\"data\": {"

        if msg == "Extra data":
            if owner._missing_object_open_from_extra_data():
                return "{"
            if owner._missing_list_open_from_extra_data():
                return "["
            next_line = owner._next_non_empty_line(lineno or 1)
            if next_line:
                next_text = owner._line_text(next_line).strip()
                if next_text:
                    return next_text
            if line_text:
                return line_text
            return "\"key\": \"value\""

        if msg in ("Unexpected ']'", "Unexpected '}'"):
            return owner._missing_close_example(msg)

        if msg == "Unterminated string":
            return "\"text\""

        if line_text:
            return line_text
        return "\"key\": \"value\""


def _is_json_value_token_start(owner: Any, value_text):
        stripped = (value_text or "").lstrip()
        if not stripped:
            return False
        ch = stripped[0]
        if ch in ('"', "{", "[") or ch == "-" or ch.isdigit():
            return True
        for lit in ("true", "false", "null"):
            if stripped.startswith(lit):
                end = len(lit)
                if end >= len(stripped) or not re.match(r"[A-Za-z0-9_]", stripped[end]):
                    return True
        return False


def _find_nearby_property_key_invalid_escape_line(owner: Any, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_has_property_key_invalid_escape(txt):
                return ln, txt
        return None, None


def _line_needs_value_quotes(owner: Any, line_text):
        if not line_text:
            return False
        fixed = owner._quote_unquoted_scalar_line(line_text)
        return bool(fixed and fixed != line_text)


def _find_nearby_unquoted_value_line(owner: Any, lineno, lookback=3):
        if not lineno:
            return None, None
        # Check current line first, then a few previous non-empty lines.
        candidates = []
        try:
            candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()))
        except EXPECTED_ERRORS:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = owner.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except EXPECTED_ERRORS:
                break
            if txt:
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if owner._line_needs_value_quotes(txt):
                return ln, txt
        return None, None


def _find_nearby_boolean_literal_typo_line(owner: Any, lineno, lookback=3):
        return json_diag_core.find_nearby_boolean_literal_typo_line(
            owner._line_text,
            lineno,
            lookback=lookback,
        )


def _is_wrong_list_open_for_object(owner: Any, prev_text, next_text):
        if not prev_text:
            return False
        prev = prev_text.strip()
        prev_compact = "".join(prev.split())
        if not (prev.endswith("\": [") or prev.endswith("\":[") or prev_compact.endswith("\":[") ):
            return False
        nxt = next_text.strip()
        # Only treat as object-open mismatch when the next token looks like an
        # object property (`"key": ...`), not a plain list item (`"value"`).
        return bool(re.match(r'^"[^"]+"\s*:', nxt))


def _find_wrong_list_open_line(owner: Any, lineno, lookback=3):
        if not lineno:
            return None
        line = lineno - 1
        checked = 0
        while line >= 1 and checked < lookback:
            text = owner._line_text(line).strip()
            if text:
                next_line_num = owner._next_non_empty_line_number(line)
                next_text = owner._line_text(next_line_num).strip() if next_line_num else ""
                if owner._is_wrong_list_open_for_object(text, next_text):
                    return line
                checked += 1
            line -= 1
        return None


def _find_wrong_object_open_line(owner: Any, lineno, lookback=3):
        if not lineno:
            return None
        line = lineno - 1
        checked = 0
        while line >= 1 and checked < lookback:
            text = owner._line_text(line).strip()
            if text:
                if text in ("[", "[,"):
                    next_line_num = owner._next_non_empty_line_number(line)
                    next_text = owner._line_text(next_line_num).strip() if next_line_num else ""
                    # Only treat "[" as wrong object opener when the following
                    # line looks like an object property (`"key": ...`).
                    if re.match(r'^"[^"]+"\s*:', next_text):
                        return line
                checked += 1
            line -= 1
        return None


def _expected_closer_before_position(owner: Any, target_line, target_col):
        return json_diag_core.expected_closer_before_position(
            owner._line_text,
            target_line,
            target_col,
        )


def _next_non_empty_line_number(owner: Any, start_line):
        try:
            last_line = int(owner.text.index("end-1c").split(".")[0])
        except EXPECTED_ERRORS:
            return None
        line = max(start_line + 1, 1)
        while line <= last_line:
            text = owner._line_text(line)
            if text.strip():
                return line
            line += 1
        return None


def _format_suggestion(owner: Any, header, before, after, header_only=False):
        if header_only:
            return f"Suggestion:\n- Before: {before}\n- After:  {after}"
        return f"{header}\n\nSuggestion:\n- Before: {before}\n- After:  {after}"


def _suggestion_from_example(owner: Any, example, add_after=None, add_colon=False, quote_key=False):
        before = example.strip()
        after = before
        if quote_key:
            after = owner._quote_property_name(before)
        if add_colon and ":" not in after:
            if after and not after.endswith(":"):
                after = after.rstrip(",") + ": \"value\""
        if add_after:
            if add_after in (",", "],", "},", "{", "["):
                if add_after == ",":
                    before = before.rstrip().rstrip(",")
                    after = before + ","
                else:
                    after = add_after
                    if add_after in ("},", "],"):
                        before = add_after.replace(",", "")
                    if add_after in ("{", "["):
                        before = add_after
            else:
                # Append non-structural additions (e.g. closing quote) to the
                # example so suggestions show the full corrected string.
                after = before + add_after
        return (before if before else "\"value\""), (after if after else "\"value\"")


def _line_text(owner: Any, lineno):
        try:
            return owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")
        except EXPECTED_ERRORS:
            return ""


def _unmatched_open_bracket_lines(owner: Any, open_bracket, close_bracket):
        text = owner.text.get("1.0", "end-1c")
        stack = []
        line = 1
        in_string = False
        escape = False
        for ch in text:
            if ch == "\n":
                line += 1
                if in_string and not escape:
                    # Keep string state; multiline strings are invalid JSON but
                    # this preserves safer structural scanning behavior.
                    pass
                escape = False
                continue
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == "\"":
                    in_string = False
                continue
            if ch == "\"":
                in_string = True
                continue
            if ch == open_bracket:
                stack.append(line)
            elif ch == close_bracket and stack:
                stack.pop()
        return stack


def _last_unmatched_bracket_line(owner: Any, open_bracket, close_bracket):
        stack = owner._unmatched_open_bracket_lines(open_bracket, close_bracket)
        if stack:
            return stack[-1]
        return None


def _find_blank_line_before(owner: Any, start_line):
        line = max(start_line - 1, 1)
        while line >= 1:
            try:
                text = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                return None
            if text.strip() == "":
                return line
            line -= 1
        return None


def _closest_non_empty_line_before(owner: Any, start_line):
        line = max(start_line - 1, 1)
        while line >= 1:
            try:
                text = owner.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except EXPECTED_ERRORS:
                return None
            if text:
                return line
            line -= 1
        return None


def _last_non_empty_line_number(owner: Any):
        try:
            line = int(owner.text.index("end-1c").split(".")[0])
        except EXPECTED_ERRORS:
            return None
        while line >= 1:
            try:
                text = owner.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except EXPECTED_ERRORS:
                return None
            if text:
                return line
            line -= 1
        return None


def _first_non_ws_char(owner: Any):
        try:
            text = owner.text.get("1.0", "end-1c")
        except EXPECTED_ERRORS:
            return ""
        for ch in text:
            if ch == "\ufeff":
                continue
            if ch.isspace():
                continue
            return ch
        return ""


def _previous_non_empty_line(owner: Any, lineno):
        line = max(lineno - 1, 1)
        while line >= 1:
            try:
                text = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                return ""
            if text.strip():
                return text
            line -= 1
        return ""


def _next_non_empty_line(owner: Any, lineno):
        line = max(lineno, 1)
        last_line = int(owner.text.index("end-1c").split(".")[0])
        while line <= last_line:
            try:
                text = owner.text.get(f"{line}.0", f"{line}.0 lineend")
            except EXPECTED_ERRORS:
                return ""
            if text.strip():
                return text
            line += 1
        return ""


def _close_before_list(owner: Any, lineno):
        next_text = owner._next_non_empty_line(lineno or 1)
        if not next_text:
            return False
        return next_text.strip().startswith("]")


def _highlight_custom_range(owner: Any, line, start_col, end_col):
        try:
            if end_col <= start_col:
                end_col = start_col + 1
            start_index = f"{line}.{max(start_col, 0)}"
            end_index = f"{line}.{max(end_col, start_col + 1)}"
            owner.text.tag_remove("json_error", "1.0", "end")
            owner.text.tag_remove("json_error_line", "1.0", "end")
            owner._clear_error_pin()
            palette = owner._current_error_palette()
            owner.text.tag_add("json_error", start_index, end_index)
            owner.text.tag_config("json_error", background=palette["fix_bg"], foreground="#ffffff")
            owner.text.tag_add("json_error_line", f"{line}.0", f"{line}.0 lineend")
            owner.text.tag_config("json_error_line", background=palette["line_bg"], foreground="#ffffff")
            owner.text.tag_raise("json_error_line")
            owner.text.tag_raise("json_error")
            owner._error_focus_index = start_index
            insert_index = owner._preferred_error_insert_index(line, start_index)
            owner.text.mark_set("insert", insert_index)
            owner.text.see(insert_index)
            owner._position_error_overlay(line)
        except EXPECTED_ERRORS:
            return


def _find_value_span_in_editor(owner: Any, value, preferred_key=None):
        try:
            text = owner.text.get("1.0", "end-1c")
        except EXPECTED_ERRORS:
            return None
        if not text or not value:
            return None

        def to_line_col(abs_index):
            line = text.count("\n", 0, abs_index) + 1
            last_nl = text.rfind("\n", 0, abs_index)
            col = abs_index if last_nl == -1 else abs_index - last_nl - 1
            return line, col

        escaped_value = re.escape(value)
        patterns = []
        if isinstance(preferred_key, str) and preferred_key:
            escaped_key = re.escape(preferred_key)
            patterns.append(rf'"{escaped_key}"\s*:\s*"(?P<val>{escaped_value})"')
        patterns.append(rf'"(?P<val>{escaped_value})"')

        for pattern in patterns:
            m = re.search(pattern, text)
            if not m:
                continue
            start = m.start("val")
            end = m.end("val")
            line, start_col = to_line_col(start)
            _, end_col = to_line_col(end)
            return line, start_col, end_col
        return None


def _best_domain_root_similarity(owner: Any, root):
        if not root:
            return 0.0
        return max(
            (difflib.SequenceMatcher(None, root.lower(), known).ratio() for known in owner.KNOWN_EMAIL_DOMAIN_ROOTS),
            default=0.0,
        )


def _suggest_known_domain_from_local_and_domain(owner: Any, local, domain):
        domain = (domain or "").lower()
        if "." not in domain:
            return None
        parts = domain.split(".")
        if len(parts) < 2:
            return None
        sld = parts[-2]
        tld = parts[-1]
        local_re = re.compile(r"^[A-Za-z0-9._%+\-]+$")
        best = None
        for known in sorted(owner.KNOWN_EMAIL_DOMAINS, key=len, reverse=True):
            kparts = known.split(".")
            if len(kparts) < 2:
                continue
            ksld = kparts[-2]
            ktld = kparts[-1]
            if ktld != tld:
                continue
            if sld and not ksld.endswith(sld):
                continue
            missing_prefix = ksld[: len(ksld) - len(sld)] if sld else ksld
            if not missing_prefix:
                continue
            if not local.lower().endswith(missing_prefix):
                continue
            cand_local = local[: len(local) - len(missing_prefix)]
            if not cand_local or not local_re.fullmatch(cand_local):
                continue
            candidate = f"{cand_local}@{known}"
            best = candidate
            break
        return best


def _apply_json_error_highlight(owner: Any, exc, line, start_index, end_index, note=""):
        owner.text.tag_remove("json_error", "1.0", "end")
        owner.text.tag_remove("json_error_line", "1.0", "end")
        owner._clear_error_pin()
        palette = owner._current_error_palette()
        owner._last_error_highlight_note = str(note or "")
        comma_focus_notes = {
            "missing_object_close_before_comma",
            "missing_list_close_before_comma",
            "missing_comma_between_blocks",
        }
        force_start_focus = str(note or "") in comma_focus_notes
        before_comma_notes = {
            "missing_object_close_before_comma",
            "missing_list_close_before_comma",
        }
        missing_key_quote_notes = {"highlight", "missing_key_quote_before_colon"}
        missing_key_quote_focus = False
        try:
            missing_key_quote_focus = (
                str(note or "") in missing_key_quote_notes
                and owner._line_has_missing_open_key_quote(owner._line_text(line))
            )
        except EXPECTED_ERRORS:
            missing_key_quote_focus = False
        insertion_only = start_index == end_index
        owner._last_error_insertion_only = bool(insertion_only)
        insertion_at_point_notes = {
            "missing_list_close_before_object_end",
            "missing_object_close_eof",
            "missing_value_close_quote",
            "missing_value_open_quote",
        }
        insertion_marker_at_point = str(note or "") in insertion_at_point_notes
        if not insertion_only and missing_key_quote_focus:
            # Missing opening key quote should be an insertion cue, not a token span.
            end_index = start_index
            insertion_only = True
            owner._last_error_insertion_only = True
        focus_index = start_index if (insertion_only or force_start_focus) else end_index
        if not insertion_only and owner._is_symbol_error_note(note):
            focus_index = owner._symbol_error_focus_index(start_index, end_index)
        if str(note or "") in before_comma_notes:
            try:
                raw = owner._line_text(line)
                comma_col = raw.find(",")
                if comma_col >= 0:
                    focus_index = f"{line}.{comma_col}"
            except EXPECTED_ERRORS:
                pass
        if insertion_only and str(note or "") == "missing_list_close_before_object_end":
            # Keep list-close insertion guidance anchored on the blank insert row,
            # but place caret at this row's edit edge so editing does not jump to another line.
            try:
                focus_line_s, focus_col_s = str(start_index).split(".")
                focus_line_no = int(focus_line_s)
                focus_col_no = int(focus_col_s)
                focus_line_text = str(owner._line_text(focus_line_no) or "")
                if focus_col_no == 0 and not focus_line_text.strip():
                    focus_index = owner.text.index(f"{focus_line_no}.0 lineend")
            except EXPECTED_ERRORS:
                pass
        owner._error_focus_index = focus_index
        if insertion_only:
            # Ensure insertion target is visible before placing marker/pin.
            try:
                owner.text.see(start_index)
                owner.text.update_idletasks()
            except EXPECTED_ERRORS:
                pass
            # For comma-focus insertion hints, keep only cursor+overlay guidance
            # and avoid token/line fill so the comma itself is not highlighted.
            render_insertion_marker = not force_start_focus
            if render_insertion_marker:
                # Fallback marker so insertion points still get a visible error marker
                # highlight even if pin placement fails on a given platform/font.
                try:
                    line_s, col_s = start_index.split(".")
                    lno = int(line_s)
                    col = int(col_s)
                    line_text = owner._line_text(lno)
                    if insertion_marker_at_point:
                        # Avoid highlighting the implicit newline at line-end,
                        # which can make the next line look incorrectly marked.
                        line_end_idx = owner.text.index(f"{lno}.0 lineend")
                        if owner.text.compare(start_index, ">=", line_end_idx):
                            if col > 0:
                                fallback_start = f"{lno}.{col - 1}"
                                fallback_end = f"{lno}.{col}"
                            else:
                                fallback_start = start_index
                                fallback_end = owner.text.index(f"{start_index} +1c")
                        else:
                            fallback_start = start_index
                            fallback_end = owner.text.index(f"{start_index} +1c")
                    elif col == 0 and not line_text.strip():
                        prev_line = owner._closest_non_empty_line_before(lno)
                        if prev_line:
                            prev_end = owner.text.index(f"{prev_line}.0 lineend")
                            prev_col = int(str(prev_end).split(".")[1])
                            if prev_col > 0:
                                fallback_start = owner.text.index(f"{prev_end} -1c")
                                fallback_end = prev_end
                            else:
                                fallback_start = prev_end
                                fallback_end = owner.text.index(f"{prev_end} +1c")
                        else:
                            fallback_start = start_index
                            fallback_end = owner.text.index(f"{start_index} +1c")
                    elif col > 0:
                        fallback_start = f"{lno}.{col - 1}"
                        fallback_end = f"{lno}.{col}"
                    else:
                        fallback_start = start_index
                        fallback_end = owner.text.index(f"{start_index} +1c")
                    owner.text.tag_add("json_error", fallback_start, fallback_end)
                except EXPECTED_ERRORS:
                    pass
            else:
                # Keep a subtle marker immediately before the insertion point so
                # users still get visual guidance without highlighting the comma.
                try:
                    line_s, col_s = start_index.split(".")
                    lno = int(line_s)
                    col = int(col_s)
                    if col > 0:
                        subtle_start = f"{lno}.{col - 1}"
                        subtle_end = f"{lno}.{col}"
                        try:
                            prev_char = owner.text.get(subtle_start, subtle_end)
                            if prev_char == "," and col > 1:
                                subtle_start = f"{lno}.{col - 2}"
                                subtle_end = f"{lno}.{col - 1}"
                        except EXPECTED_ERRORS:
                            pass
                    else:
                        subtle_start = start_index
                        subtle_end = owner.text.index(f"{start_index} +1c")
                    owner.text.tag_add("json_error", subtle_start, subtle_end)
                except EXPECTED_ERRORS:
                    pass
        else:
            owner.text.tag_add("json_error", start_index, end_index)
        marker_bg, marker_fg = owner._error_marker_colors(note, palette, insertion_only=insertion_only)
        owner.text.tag_config("json_error", background=marker_bg, foreground=marker_fg)
        show_line_context = (not insertion_only) and (not force_start_focus) and (not missing_key_quote_focus)
        if show_line_context:
            owner.text.tag_add("json_error_line", f"{line}.0", f"{line}.0 lineend")
            owner.text.tag_config("json_error_line", background=palette["line_bg"], foreground="#ffffff")
            owner.text.tag_raise("json_error_line")
        owner.text.tag_raise("json_error")
        # Keep drag-selection visible above error tags.
        try:
            owner.text.tag_raise("sel")
        except EXPECTED_ERRORS:
            pass
        # For insertion errors, keep focus at the insertion target so the
        # marker/overlay does not jump away during live validation.
        if insertion_only or force_start_focus:
            insert_index = focus_index
        else:
            insert_index = owner._preferred_error_insert_index(line, focus_index)
        owner.text.mark_set("insert", insert_index)
        owner.text.see(insert_index)
        if note:
            owner._log_json_error(exc, line, note=note)
        else:
            owner._log_json_error(exc, line, note="highlight")
        owner._position_error_overlay(line)


def _highlight_json_error(owner: Any, exc):
        return json_error_highlight_core.highlight_json_error(
            owner,
            exc,
            apply_highlight_fn=json_error_highlight_render_service.apply_json_error_highlight,
            log_error_fn=json_error_highlight_render_service.log_json_error,
        )


def _diag_system_from_note(owner: Any, note):
        # Diagnostic mapping checklist:
        # - locked_* -> highlight_restore
        # - overlay_* -> overlay_parse
        # - highlight_failed* -> highlight_internal
        # - cursor_restore* -> cursor_restore
        # - spacing_*, missing_phone*, invalid_email* -> input_validation
        # - symbol_* and symbol-type invalid_* -> symbol_recovery
        # - everything else -> json_highlight
        return json_error_diag_service.diag_system_from_note(
            note,
            is_symbol_error_note=getattr(owner, "_is_symbol_error_note", None),
        )


def _log_json_error_emergency(owner: Any, exc, target_line, note=""):
        # Emergency diagnostics fallback: write a minimal parse entry directly
        # when normal service logging is bypassed or fails unexpectedly.
        try:
            log_path = owner._diag_log_path()
            log_dir = os.path.dirname(str(log_path or ""))
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                line = int(target_line)
            except (TypeError, ValueError, AttributeError):
                line = int(getattr(exc, "lineno", 1) or 1)
            line = max(1, line)
            msg = str(getattr(exc, "msg", str(exc)) or "").strip()
            entry = (
                "\n---\n"
                f"time={stamp} action={str(getattr(owner, '_diag_action', 'apply_edit:0'))}\n"
                f"msg={msg} lineno={getattr(exc, 'lineno', None)} col={getattr(exc, 'colno', None)} "
                f"target={line} note={str(note or '').strip()}\n"
                "system=overlay_parse mode=guide\n"
                f"path={owner._selected_tree_path_text()}\n"
            )
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(entry)
        except EXPECTED_ERRORS:
            return


def _log_input_mode_apply_trace(owner: Any, stage, path, specs_count, changed=None):
        input_mode_diag_service.log_input_mode_apply_trace(
            owner,
            stage,
            path,
            specs_count,
            changed=changed,
        )


def _begin_diag_action(owner: Any, action_name):
        owner._diag_event_seq += 1
        owner._diag_action = f"{action_name}:{owner._diag_event_seq}"
        return owner._diag_action


def _clear_json_error_highlight(owner: Any):
        try:
            owner.text.tag_remove("json_error", "1.0", "end")
            owner.text.tag_remove("json_error_line", "1.0", "end")
            owner._clear_error_pin()
            owner._error_focus_index = None
            owner._last_error_highlight_note = ""
            owner._last_error_insertion_only = False
        except EXPECTED_ERRORS:
            return


def _on_text_keypress(owner: Any, event):
        try:
            keysym = getattr(event, "keysym", "") or ""
            char = getattr(event, "char", "") or ""
            nav_keys = {
                "Up", "Down", "Prior", "Next",
                "Page_Up", "Page_Down",
            }
            if owner.error_overlay is not None and keysym in nav_keys:
                owner._enforce_error_focus()
                return "break"
            owner._last_edit_was_deletion = keysym in ("BackSpace", "Delete")
            should_clear = bool(char) or keysym in ("BackSpace", "Delete", "Return", "KP_Enter", "space")
            if should_clear and (owner.error_overlay is not None):
                owner._destroy_error_overlay()
                owner._clear_json_error_highlight()
                owner._auto_apply_pending = True
        except EXPECTED_ERRORS:
            return


def _on_text_nav_attempt(owner: Any, event):
        try:
            if owner.error_overlay is None:
                return
            target = owner.text.index(f"@{event.x},{event.y}")
            if owner._is_index_on_error_line(target):
                return
            owner._enforce_error_focus()
            return "break"
        except EXPECTED_ERRORS:
            return "break"


def _is_index_on_error_line(owner: Any, index):
        if not owner._error_focus_index or not index:
            return False
        try:
            err_line = int(str(owner._error_focus_index).split(".")[0])
            idx_line = int(str(index).split(".")[0])
            return err_line == idx_line
        except EXPECTED_ERRORS:
            return False


def _line_number_from_index(owner: Any, index):
        if not index:
            return None
        try:
            return int(str(index).split(".")[0])
        except EXPECTED_ERRORS:
            return None


def _preferred_error_insert_index(owner: Any, line, fallback_index):
        # During live feedback, keep the caret where the user is actively typing
        # on the same line instead of snapping back to the first error column.
        try:
            if not (owner._auto_apply_pending and owner.error_overlay is not None):
                return fallback_index
            current_insert = owner.text.index("insert")
            if owner._line_number_from_index(current_insert) != int(line):
                return fallback_index
            return current_insert
        except EXPECTED_ERRORS:
            return fallback_index

__all__ = [name for name in globals() if not name.startswith("__")]
