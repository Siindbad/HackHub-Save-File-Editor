"""JSON raw-mode edit guard helpers for safe token-level mutation control."""

from __future__ import annotations

import json
import re
from typing import Any


GLOBAL_LOCKED_VALUE_KEYS: frozenset[str] = frozenset({"width", "height"})


_NUMBER_TOKEN = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+\-]?\d+)?")


def _parse_index(index_text: str) -> tuple[int, int]:
    raw = str(index_text or "1.0").strip()
    if not raw:
        return 1, 0
    parts = raw.split(".", 1)
    try:
        line_no = max(1, int(parts[0]))
    except ValueError:
        line_no = 1
    try:
        col_no = max(0, int(parts[1])) if len(parts) > 1 else 0
    except ValueError:
        col_no = 0
    return line_no, col_no


def _offset_from_index(raw: str, index_text: str) -> int:
    line_no, col_no = _parse_index(index_text)
    line_start = 0
    current_line = 1
    text = str(raw or "")
    while current_line < line_no and line_start < len(text):
        next_break = text.find("\n", line_start)
        if next_break < 0:
            line_start = len(text)
            break
        line_start = next_break + 1
        current_line += 1
    return min(len(text), line_start + col_no)


def _decode_string_token(token: str) -> str:
    try:
        decoded = json.loads(str(token))
        return str(decoded or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        inner = str(token or "")
        if len(inner) >= 2 and inner[0] == '"' and inner[-1] == '"':
            inner = inner[1:-1]
        return inner


def _next_nonspace_char(raw: str, start: int) -> str:
    idx = int(start)
    text = str(raw or "")
    while idx < len(text):
        if text[idx] not in (" ", "\t", "\r", "\n"):
            return text[idx]
        idx += 1
    return ""


def _is_word_boundary(text: str, pos: int) -> bool:
    if pos < 0 or pos >= len(text):
        return True
    ch = text[pos]
    return not (ch.isalpha() or ch.isdigit() or ch == "_")


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not spans:
        return []
    ordered = sorted(spans, key=lambda item: (int(item[0]), int(item[1])))
    merged: list[tuple[int, int]] = []
    cur_start, cur_end = ordered[0]
    for start, end in ordered[1:]:
        if int(start) <= int(cur_end):
            cur_end = max(int(cur_end), int(end))
            continue
        merged.append((int(cur_start), int(cur_end)))
        cur_start, cur_end = int(start), int(end)
    merged.append((int(cur_start), int(cur_end)))
    return merged


def build_editable_spans(raw: str, protected_value_keys: frozenset[str] | None = None) -> list[tuple[int, int]]:
    """Return editable raw-text spans for JSON mode.

    Editable spans:
    - String value content only (quote delimiters are excluded)
    - Boolean tokens (`true`, `false`)
    - Numeric tokens

    Locked spans:
    - Property keys
    - Structural punctuation (including commas/quotes/braces/brackets/colons)
    - Values for protected keys (global lock list, default: width/height)
    """
    text = str(raw or "")
    if not text:
        return []
    protected = {
        str(name or "").strip().casefold()
        for name in (protected_value_keys or GLOBAL_LOCKED_VALUE_KEYS)
        if str(name or "").strip()
    }
    spans: list[tuple[int, int]] = []
    idx = 0
    pending_key: str | None = None
    while idx < len(text):
        ch = text[idx]
        if ch == '"':
            end = idx + 1
            escaped = False
            while end < len(text):
                cur = text[end]
                if escaped:
                    escaped = False
                    end += 1
                    continue
                if cur == "\\":
                    escaped = True
                    end += 1
                    continue
                if cur == '"':
                    break
                end += 1
            if end >= len(text):
                break
            token = text[idx : end + 1]
            is_key = _next_nonspace_char(text, end + 1) == ":"
            if is_key:
                pending_key = _decode_string_token(token).casefold()
            else:
                if pending_key not in protected and end > (idx + 1):
                    spans.append((idx + 1, end))
                pending_key = None
            idx = end + 1
            continue
        if text.startswith("true", idx) and _is_word_boundary(text, idx - 1) and _is_word_boundary(text, idx + 4):
            if pending_key not in protected:
                spans.append((idx, idx + 4))
            pending_key = None
            idx += 4
            continue
        if text.startswith("false", idx) and _is_word_boundary(text, idx - 1) and _is_word_boundary(text, idx + 5):
            if pending_key not in protected:
                spans.append((idx, idx + 5))
            pending_key = None
            idx += 5
            continue
        number_match = _NUMBER_TOKEN.match(text, idx)
        if number_match is not None:
            end = int(number_match.end())
            if pending_key not in protected:
                spans.append((idx, end))
            pending_key = None
            idx = end
            continue
        if ch in (",", "}", "]"):
            pending_key = None
        idx += 1
    return _merge_spans(spans)


def _is_range_editable(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    if start >= end:
        return True
    for span_start, span_end in spans:
        if int(span_start) <= int(start) and int(end) <= int(span_end):
            return True
    return False


def _is_insert_position_editable(spans: list[tuple[int, int]], pos: int) -> bool:
    for span_start, span_end in spans:
        if int(span_start) <= int(pos) <= int(span_end):
            return True
    return False


def _selection_offsets(owner: Any, raw: str, expected_errors: tuple[type[BaseException], ...]) -> tuple[int, int] | None:
    try:
        sel_first = owner.text.index("sel.first")
        sel_last = owner.text.index("sel.last")
    except expected_errors:
        return None
    start = _offset_from_index(raw, str(sel_first))
    end = _offset_from_index(raw, str(sel_last))
    if end < start:
        start, end = end, start
    return start, end


def _insert_offset(owner: Any, raw: str, expected_errors: tuple[type[BaseException], ...]) -> int:
    try:
        insert_idx = owner.text.index("insert")
    except expected_errors:
        insert_idx = "1.0"
    return _offset_from_index(raw, str(insert_idx))


def _read_raw(owner: Any, expected_errors: tuple[type[BaseException], ...]) -> str:
    try:
        return str(owner.text.get("1.0", "end-1c") or "")
    except expected_errors:
        return ""


def is_keypress_edit_allowed(
    owner: Any,
    event: Any,
    *,
    expected_errors: tuple[type[BaseException], ...],
) -> bool:
    """Return whether a JSON text KeyPress mutation should be allowed."""
    keysym = str(getattr(event, "keysym", "") or "")
    char = str(getattr(event, "char", "") or "")
    state = int(getattr(event, "state", 0) or 0)
    ctrl_active = bool(state & 0x4)

    non_edit_keys = {
        "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
        "Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next",
        "Page_Up", "Page_Down", "Tab", "Escape",
    }
    if keysym in non_edit_keys:
        return True

    lower_key = keysym.lower()
    if ctrl_active and lower_key in {"a", "c", "f", "g", "z", "y"}:
        return True

    is_backspace = keysym == "BackSpace"
    is_delete = keysym == "Delete"
    is_cut = ctrl_active and lower_key == "x"
    is_paste = ctrl_active and lower_key == "v"
    is_enter = keysym in {"Return", "KP_Enter"}
    is_typed = bool(char) and not ctrl_active
    if not (is_backspace or is_delete or is_cut or is_paste or is_enter or is_typed):
        return True

    raw = _read_raw(owner, expected_errors)
    spans = build_editable_spans(raw)
    selection = _selection_offsets(owner, raw, expected_errors)
    caret = _insert_offset(owner, raw, expected_errors)

    if selection is not None:
        if not _is_range_editable(spans, selection[0], selection[1]):
            return False

    if is_backspace and selection is None:
        if caret <= 0:
            return True
        return _is_range_editable(spans, caret - 1, caret)
    if is_delete and selection is None:
        if caret >= len(raw):
            return True
        return _is_range_editable(spans, caret, caret + 1)

    # Insert/replace and cut operations require editable insertion location.
    return _is_insert_position_editable(spans, caret)


def is_paste_allowed(
    owner: Any,
    *,
    expected_errors: tuple[type[BaseException], ...],
) -> bool:
    """Return whether a context-menu paste operation is allowed in JSON mode."""
    raw = _read_raw(owner, expected_errors)
    spans = build_editable_spans(raw)
    selection = _selection_offsets(owner, raw, expected_errors)
    if selection is not None and not _is_range_editable(spans, selection[0], selection[1]):
        return False
    caret = _insert_offset(owner, raw, expected_errors)
    return _is_insert_position_editable(spans, caret)

