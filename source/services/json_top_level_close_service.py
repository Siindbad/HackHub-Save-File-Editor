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
