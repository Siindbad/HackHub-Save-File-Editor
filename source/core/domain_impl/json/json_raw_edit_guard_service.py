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


def _offset_from_widget_count(owner: Any, index_text: str, expected_errors: tuple[type[BaseException], ...]) -> int | None:
    """Use Tk text `count` when available to avoid full line scans for index offsets."""
    try:
        counter = getattr(owner.text, "count", None)
        if not callable(counter):
            return None
        counts = counter("1.0", str(index_text), "chars")
        if isinstance(counts, (tuple, list)) and counts:
            return max(0, int(counts[0]))
    except expected_errors:
        return None
    except (TypeError, ValueError, AttributeError):
        return None
    return None


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


def _prev_nonspace_char(raw: str, start: int) -> str:
    idx = int(start)
    text = str(raw or "")
    while idx >= 0:
        if text[idx] not in (" ", "\t", "\r", "\n"):
            return text[idx]
        idx -= 1
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


def _decode_key_name(token: str) -> str:
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        inner = token[1:-1]
        if "\\" not in inner:
            return inner.casefold()
    return _decode_string_token(token).casefold()


def _quoted_key_before_colon(line_text: str, colon_idx: int) -> str | None:
    head = str(line_text or "")[: max(0, int(colon_idx) + 1)]
    match = re.match(r'.*"(?P<key>(?:\\.|[^"\\])*)"\s*:\s*$', head)
    if not match:
        return None
    token = '"' + str(match.group("key") or "") + '"'
    return _decode_key_name(token)


def _line_local_value_window(line_text: str, colon_idx: int) -> tuple[int, int, bool] | None:
    text = str(line_text or "")
    value_start = int(colon_idx) + 1
    while value_start < len(text) and text[value_start] in (" ", "\t", "\r"):
        value_start += 1
    if value_start >= len(text):
        return None
    idx = value_start
    in_string = False
    escaped = False
    while idx < len(text):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            idx += 1
            continue
        if ch == '"':
            in_string = True
            idx += 1
            continue
        if ch in (",", "}", "]"):
            break
        idx += 1
    value_end = idx
    is_string = value_start < value_end and text[value_start] == '"' and value_end > value_start + 1 and text[value_end - 1] == '"'
    return value_start, value_end, is_string


def _line_local_position_editable(
    raw: str,
    pos: int,
    *,
    insert_mode: bool,
    protected_value_keys: frozenset[str],
) -> bool | None:
    text = str(raw or "")
    index = max(0, min(len(text), int(pos)))
    line_start = text.rfind("\n", 0, index) + 1
    line_end = text.find("\n", index)
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end]
    rel = index - line_start
    if not line or rel < 0 or rel > len(line):
        return None

    in_string = False
    escaped = False
    colon_idx = -1
    for i, ch in enumerate(line):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == ":":
            colon_idx = i
            break
    if colon_idx < 0:
        return None
    key_name = _quoted_key_before_colon(line, colon_idx)
    if key_name in protected_value_keys:
        return False
    value_window = _line_local_value_window(line, colon_idx)
    if value_window is None:
        return None
    value_start, value_end, is_string = value_window
    if is_string:
        editable_start = value_start + 1
        editable_end = value_end - 1
    else:
        editable_start = value_start
        editable_end = value_end
    if insert_mode:
        return editable_start <= rel <= editable_end
    return editable_start <= rel < editable_end


def _position_editable_direct(
    raw: str,
    pos: int,
    *,
    insert_mode: bool,
    protected_value_keys: frozenset[str] | None = None,
) -> bool:
    """Check one position without materializing all editable spans."""
    text = str(raw or "")
    if not text:
        return False
    index = max(0, min(len(text), int(pos)))
    protected = {
        str(name or "").strip().casefold()
        for name in (protected_value_keys or GLOBAL_LOCKED_VALUE_KEYS)
        if str(name or "").strip()
    }
    local_result = _line_local_position_editable(
        text,
        index,
        insert_mode=insert_mode,
        protected_value_keys=frozenset(protected),
    )
    if local_result is not None:
        return bool(local_result)
    idx = 0
    pending_key: str | None = None
    while idx < len(text):
        ch = text[idx]
        if insert_mode and index == idx:
            # Allow first-character insertion in empty value slots
            # (for example replacing `true` with `false` after full deletion).
            if ch in (",", "}", "]") and pending_key not in protected:
                return True
            if ch.isspace() and pending_key not in protected:
                prev_char = _prev_nonspace_char(text, idx - 1)
                next_char = _next_nonspace_char(text, idx)
                if prev_char == ":" and next_char in (",", "}", "]"):
                    return True
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
                return False
            token = text[idx : end + 1]
            is_key = _next_nonspace_char(text, end + 1) == ":"
            if is_key:
                pending_key = _decode_key_name(token)
            else:
                if pending_key not in protected:
                    if insert_mode:
                        if (idx + 1) <= index <= end:
                            return True
                    elif (idx + 1) <= index < end:
                        return True
                pending_key = None
            if index < idx:
                return False
            if index <= end + 1 and not is_key:
                return False
            idx = end + 1
            continue
        if text.startswith("true", idx) and _is_word_boundary(text, idx - 1) and _is_word_boundary(text, idx + 4):
            token_end = idx + 4
            token_editable = pending_key not in protected
            if insert_mode:
                if idx <= index <= token_end:
                    return token_editable
            elif idx <= index < token_end:
                return token_editable
            pending_key = None
            if index < idx:
                return False
            if index <= token_end:
                return False
            idx = token_end
            continue
        if text.startswith("false", idx) and _is_word_boundary(text, idx - 1) and _is_word_boundary(text, idx + 5):
            token_end = idx + 5
            token_editable = pending_key not in protected
            if insert_mode:
                if idx <= index <= token_end:
                    return token_editable
            elif idx <= index < token_end:
                return token_editable
            pending_key = None
            if index < idx:
                return False
            if index <= token_end:
                return False
            idx = token_end
            continue
        number_match = _NUMBER_TOKEN.match(text, idx)
        if number_match is not None:
            token_end = int(number_match.end())
            token_editable = pending_key not in protected
            if insert_mode:
                if idx <= index <= token_end:
                    return token_editable
            elif idx <= index < token_end:
                return token_editable
            pending_key = None
            if index < idx:
                return False
            if index <= token_end:
                return False
            idx = token_end
            continue
        # Unquoted scalar fallback: keeps malformed in-progress values editable
        # so users can backspace/replace typos like `1fase` safely.
        if not ch.isspace() and ch not in ('"', ",", "}", "]", "{", "[", ":"):
            token_end = idx
            while token_end < len(text):
                token_ch = text[token_end]
                if token_ch.isspace() or token_ch in (",", "}", "]"):
                    break
                token_end += 1
            token_editable = pending_key not in protected
            if insert_mode:
                if idx <= index <= token_end:
                    return token_editable
            elif idx <= index < token_end:
                return token_editable
            pending_key = None
            if index < idx:
                return False
            if index <= token_end:
                return False
            idx = token_end
            continue
        if ch in (",", "}", "]"):
            pending_key = None
        if index == idx:
            return False
        idx += 1
    return False


def _selection_offsets(owner: Any, raw: str, expected_errors: tuple[type[BaseException], ...]) -> tuple[int, int] | None:
    try:
        sel_first = owner.text.index("sel.first")
        sel_last = owner.text.index("sel.last")
    except expected_errors:
        return None
    start = _offset_from_widget_count(owner, str(sel_first), expected_errors)
    if start is None:
        start = _offset_from_index(raw, str(sel_first))
    end = _offset_from_widget_count(owner, str(sel_last), expected_errors)
    if end is None:
        end = _offset_from_index(raw, str(sel_last))
    if end < start:
        start, end = end, start
    return start, end


def _insert_offset(owner: Any, raw: str, expected_errors: tuple[type[BaseException], ...]) -> int:
    try:
        insert_idx = owner.text.index("insert")
    except expected_errors:
        insert_idx = "1.0"
    from_count = _offset_from_widget_count(owner, str(insert_idx), expected_errors)
    if from_count is not None:
        return min(len(raw), from_count)
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
    selection = _selection_offsets(owner, raw, expected_errors)
    caret = _insert_offset(owner, raw, expected_errors)

    # Fast path: single-cursor key edits should not require full-buffer span builds.
    if selection is None:
        if is_backspace:
            if caret <= 0:
                return True
            return _position_editable_direct(raw, caret - 1, insert_mode=False)
        if is_delete:
            if caret >= len(raw):
                return True
            return _position_editable_direct(raw, caret, insert_mode=False)
        if is_typed or is_enter:
            return _position_editable_direct(raw, caret, insert_mode=True)

    spans = build_editable_spans(raw)
    if selection is not None:
        if not _is_range_editable(spans, selection[0], selection[1]):
            return False

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
