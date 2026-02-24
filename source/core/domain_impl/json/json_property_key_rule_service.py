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
