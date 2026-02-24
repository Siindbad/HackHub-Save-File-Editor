"""JSON repair rules used by apply/live feedback flows."""

from __future__ import annotations

import difflib
import re

from typing import Any

from core import json_diagnostics as json_diag_core
from core.exceptions import EXPECTED_ERRORS
from core.domain_impl.json import json_closer_symbol_service
from core.domain_impl.json import json_colon_comma_service
from core.domain_impl.json import json_nearby_line_service
from core.domain_impl.json import json_open_symbol_service
from core.domain_impl.json import json_property_key_rule_service
from core.domain_impl.json import json_quoted_item_tail_service
from core.domain_impl.json import json_scalar_tail_service
from core.domain_impl.json import json_top_level_close_service


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
