"""JSON diagnostics helpers delegated from JsonEditor."""

from __future__ import annotations

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
from core.domain_impl.json import json_closer_symbol_service
from core.domain_impl.json import json_colon_comma_service
from core.domain_impl.json import json_edit_flow_service
from core.domain_impl.json import json_error_diag_service
from core.domain_impl.json import json_error_highlight_render_service
from core.domain_impl.json import json_nearby_line_service
from core.domain_impl.json import json_open_symbol_service
from core.domain_impl.json import json_parse_feedback_service
from core.domain_impl.json import json_property_key_rule_service
from core.domain_impl.json import json_quoted_item_tail_service
from core.domain_impl.json import json_scalar_tail_service
from core.domain_impl.json import json_top_level_close_service
from core.domain_impl.json import json_validation_feedback_service
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
