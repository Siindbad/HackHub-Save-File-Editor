"""Core JSON error diagnostic builders.

These functions centralize parse-diagnostic decision logic while the editor
object supplies context helpers and text access.
"""

import json

def format_json_error(owner, exc):
    msg = getattr(exc, "msg", None)
    owner._last_json_error_msg = msg
    owner._last_json_error_diag = None
    if isinstance(exc, json.JSONDecodeError) or msg:
        diag = owner._build_json_diagnostic(exc)
        if diag:
            owner._last_json_error_diag = diag
            return owner._format_suggestion(diag["header"], diag["before"], diag["after"])
        if msg in (
            "Illegal trailing comma before end of object",
            "Illegal trailing comma before end of array",
        ):
            illegal_no, illegal_text = owner._find_nearby_illegal_trailing_comma_line(
                getattr(exc, "lineno", None) or 1
            )
            if illegal_text:
                return owner._format_suggestion(
                    "Invalid Entry: remove the trailing comma.",
                    illegal_text.strip(),
                    owner._fix_illegal_trailing_comma_before_close(illegal_text).strip(),
                )
        example = owner._example_for_error(exc)
        # Missing list open after key (e.g. '"purchasedItems":' followed by quoted items).
        if msg in (
            "Expecting ':' delimiter",
            "Expecting property name enclosed in double quotes",
            "Expecting ',' delimiter",
            "Expecting value",
            "Expecting ']'",
            "Expecting '}'",
        ):
            if not (msg == "Expecting ',' delimiter" and owner._is_missing_object_close()):
                missing_key_line, missing_open = owner._find_missing_container_open_after_key_line(
                    getattr(exc, "lineno", None)
                )
                if missing_key_line and missing_open in ("[", "{"):
                    key_text = owner._line_text(missing_key_line).strip()
                    return owner._format_suggestion(
                        f'Invalid Entry: add "{missing_open}" after the highlighted line.',
                        key_text,
                        f"{key_text} {missing_open}",
                    )
        # Prefer missing-quote repair when the parser error points to a nearby
        # line but the real issue is an unquoted scalar value (e.g. id/IBAN).
        if msg in ("Expecting value", "Expecting ',' delimiter"):
            bool_line_no, bool_line_text, bool_diag = owner._find_nearby_boolean_literal_typo_line(
                getattr(exc, "lineno", None)
            )
            if bool_line_text and bool_diag:
                return owner._format_suggestion(
                    "Invalid Entry: fix the boolean value.",
                    bool_line_text.strip(),
                    bool_diag["after"].strip(),
                )
            nearby_line_no, nearby_line_text = owner._find_nearby_unquoted_value_line(
                getattr(exc, "lineno", None)
            )
            if nearby_line_text:
                quoted = owner._quote_unquoted_value(nearby_line_text)
                if quoted and quoted != nearby_line_text:
                    return owner._format_suggestion(
                        "Invalid Entry: add the missing quote.",
                        nearby_line_text,
                        quoted,
                    )
        if msg == "Expecting ',' delimiter":
            lineno = getattr(exc, "lineno", None)
            line_text = owner._line_text(lineno).strip() if lineno else ""
            stray_line_no, stray_line_text = owner._find_nearby_trailing_stray_quote_line(lineno)
            if stray_line_text:
                return owner._format_suggestion(
                    "Invalid Entry: remove the extra quote.",
                    stray_line_text,
                    owner._fix_trailing_stray_quote_after_comma(stray_line_text),
                )
            invalid_closer_no, invalid_closer_text = owner._find_nearby_invalid_symbol_after_closer_line(lineno)
            if invalid_closer_text:
                return owner._format_suggestion(
                    "Invalid Entry: replace the invalid trailing symbol with a comma.",
                    invalid_closer_text,
                    owner._fix_invalid_symbol_after_closer(invalid_closer_text),
                )
            if owner._line_extra_quote_in_string_value(line_text):
                return owner._format_suggestion(
                    "Invalid Entry: add a comma near the highlighted line.",
                    line_text,
                    owner._fix_extra_quote_to_comma(line_text),
                )
            invalid_tail_no, invalid_tail_text = owner._find_nearby_invalid_trailing_symbols_line(lineno)
            if invalid_tail_text:
                return owner._format_suggestion(
                    "Invalid Entry: replace the invalid trailing symbol with a comma.",
                    invalid_tail_text,
                    owner._fix_invalid_trailing_symbols_after_string_value(invalid_tail_text, invalid_tail_no),
                )
            if owner._is_missing_object_close():
                return owner._format_suggestion(
                    "Invalid Entry: add the missing closing bracket.",
                    "",
                    "}",
                )
            wrong_object_line = owner._find_wrong_object_open_line(getattr(exc, "lineno", None))
            if wrong_object_line:
                wrong_text = owner._line_text(wrong_object_line).strip()
                before = wrong_text
                after = wrong_text.replace("[", "{", 1)
                return owner._format_suggestion(
                    "Invalid Entry: replace \"[\" with \"{\".",
                    before,
                    after,
                )
            wrong_line = owner._find_wrong_list_open_line(getattr(exc, "lineno", None))
            if wrong_line:
                return owner._format_suggestion(
                    "Invalid Entry: replace \"[\" with \"{\".",
                    "[",
                    "{",
                )
            if owner._is_missing_list_close():
                lineno = getattr(exc, "lineno", None) or 1
                comma_line = owner._find_comma_only_line_before(lineno)
                if comma_line:
                    return owner._format_suggestion(
                        "Invalid Entry: add the missing closing bracket.",
                        ",",
                        "],",
                    )
                return owner._format_suggestion(
                    "Invalid Entry: add the missing closing bracket.",
                    "",
                    "]",
                )
            if owner._is_missing_object_open_at(getattr(exc, "lineno", None)):
                before, after = "", "{"
                return owner._format_suggestion(
                    "Invalid Entry: add \"{\" before the highlighted line.",
                    before,
                    after,
                )
            if owner._close_before_list(getattr(exc, "lineno", None)):
                before, after = "", "}"
                return owner._format_suggestion(
                    "Invalid Entry: add the missing closing bracket.",
                    before,
                    after,
                )
            if owner._is_missing_object_open(exc):
                before, after = owner._suggestion_from_example(example, add_after="{")
                return owner._format_suggestion(
                    "Invalid Entry: add \"{\" after the highlighted line.",
                    before,
                    after,
                )
            if owner._is_missing_object_close():
                add_after = "}" if owner._close_before_list(getattr(exc, "lineno", None)) else "},"
                before, after = owner._suggestion_from_example(example, add_after=add_after)
                return owner._format_suggestion(
                    "Invalid Entry: add the missing closing bracket.",
                    before,
                    after,
                )
            if owner._is_missing_list_close():
                lineno = getattr(exc, "lineno", None)
                next_text = owner._next_non_empty_line(lineno or 1).strip()
                add_after = "]" if next_text.startswith(("}", "]")) else "],"
                before, after = owner._suggestion_from_example(example, add_after=add_after)
                return owner._format_suggestion(
                    "Invalid Entry: add the missing closing bracket.",
                    before,
                    after,
                )
            before, after = owner._suggestion_from_example(example, add_after=",")
            return owner._format_suggestion(
                "Invalid Entry: add a comma near the highlighted line.",
                before,
                after,
            )
        if msg == "Expecting property name enclosed in double quotes":
            missing_key_line, missing_open = owner._find_missing_container_open_after_key_line(
                getattr(exc, "lineno", None)
            )
            if missing_key_line and missing_open in ("[", "{"):
                key_text = owner._line_text(missing_key_line).strip()
                return owner._format_suggestion(
                    f'Invalid Entry: add "{missing_open}" after the highlighted line.',
                    key_text,
                    f"{key_text} {missing_open}",
                )
            dup_line_no, dup_line_text = owner._find_nearby_duplicate_trailing_comma_line(
                getattr(exc, "lineno", None)
            )
            if dup_line_text:
                return owner._format_suggestion(
                    "Invalid Entry: remove the extra comma.",
                    dup_line_text,
                    owner._fix_duplicate_trailing_comma(dup_line_text),
                )
            invalid_tail_no, invalid_tail_text = owner._find_nearby_invalid_trailing_symbols_line(
                getattr(exc, "lineno", None)
            )
            if invalid_tail_text:
                return owner._format_suggestion(
                    "Invalid Entry: replace the invalid trailing symbol with a comma.",
                    invalid_tail_text,
                    owner._fix_invalid_trailing_symbols_after_string_value(invalid_tail_text, invalid_tail_no),
                )
            comma_line = owner._find_comma_only_line_before(getattr(exc, "lineno", None) or 1)
            if comma_line:
                return owner._format_suggestion(
                    "Invalid Entry: add the missing closing bracket.",
                    ",",
                    "},",
                )
            lineno = getattr(exc, "lineno", None)
            line_text = ""
            if lineno:
                try:
                    line_text = owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()
                except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                    line_text = ""
            if owner._is_missing_object_close() and line_text.startswith("{"):
                return owner._format_suggestion(
                    "Invalid Entry: add the missing closing bracket.",
                    "",
                    "}",
                )
            if line_text == "{,":
                return owner._format_suggestion(
                    "Invalid Entry: remove the comma after \"{\".",
                    "{,",
                    "{",
                )
            if line_text.startswith("{"):
                key_line = owner._missing_list_open_key_line(lineno)
                if key_line:
                    key_text = owner._line_text(key_line).strip()
                    before = key_text
                    after = key_text + " ["
                    return owner._format_suggestion(
                        "Invalid Entry: add \"[\" after the highlighted line.",
                        before,
                        after,
                    )
            before = line_text if line_text else example
            after = owner._quote_property_name(before)
            return owner._format_suggestion(
                "Invalid Entry: add quotes around the highlighted name.",
                before,
                after,
            )
        if msg == "Expecting ':' delimiter":
            missing_key_line, missing_open = owner._find_missing_container_open_after_key_line(
                getattr(exc, "lineno", None)
            )
            if missing_key_line and missing_open in ("[", "{"):
                key_text = owner._line_text(missing_key_line).strip()
                return owner._format_suggestion(
                    f'Invalid Entry: add "{missing_open}" after the highlighted line.',
                    key_text,
                    f"{key_text} {missing_open}",
                )
            line_text = ""
            try:
                lineno = getattr(exc, "lineno", None)
                if lineno:
                    line_text = owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()
            except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                line_text = ""
            before = line_text if line_text else example
            if line_text and owner._line_has_trailing_stray_quote_after_comma(line_text):
                after = owner._fix_trailing_stray_quote_after_comma(line_text)
                return owner._format_suggestion(
                    "Invalid Entry: remove the extra quote.",
                    before,
                    after,
                )
            if line_text and line_text.count("\"") % 2 == 1:
                after = owner._fix_missing_quote(line_text)
            else:
                after = owner._missing_colon_example(line_text) if line_text else "\"key\": \"value\""
            return owner._format_suggestion(
                "Invalid Entry: add a colon after the highlighted name.",
                before,
                after,
            )
        if msg and msg.startswith("Invalid control character"):
            stray_line_no, stray_line_text = owner._find_nearby_trailing_stray_quote_line(
                getattr(exc, "lineno", None)
            )
            if stray_line_text:
                return owner._format_suggestion(
                    "Invalid Entry: remove the extra quote.",
                    stray_line_text,
                    owner._fix_trailing_stray_quote_after_comma(stray_line_text),
                )
            invalid_tail_no, invalid_tail_text = owner._find_nearby_invalid_trailing_symbols_line(
                getattr(exc, "lineno", None)
            )
            if invalid_tail_text:
                return owner._format_suggestion(
                    "Invalid Entry: replace the invalid trailing symbol with a comma.",
                    invalid_tail_text,
                    owner._fix_invalid_trailing_symbols_after_string_value(invalid_tail_text, invalid_tail_no),
                )
            line_text = ""
            try:
                lineno = getattr(exc, "lineno", None)
                if lineno:
                    line_text = owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()
            except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                line_text = ""
            before = line_text if line_text else example
            after = owner._fix_missing_quote(line_text) if line_text else "\"key\": \"value\""
            return owner._format_suggestion(
                "Invalid Entry: add the missing quote.",
                before,
                after,
            )
        if msg in ("Expecting ']'", "Expecting '}'"):
            before, after = owner._suggestion_from_example(example, add_after=example.strip())
            return owner._format_suggestion(
                "Invalid Entry: add the missing closing bracket.",
                before,
                after,
            )
        if msg == "Expecting value":
            line_text = ""
            try:
                lineno = getattr(exc, "lineno", None)
                if lineno:
                    line_text = owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()
            except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                line_text = ""
            if owner._is_key_colon_comma_line(line_text):
                return owner._format_suggestion(
                    "Invalid Entry: add \"[\" after the highlighted line.",
                    line_text,
                    owner._key_colon_comma_to_list_open(line_text),
                )
            if line_text:
                quoted = owner._quote_unquoted_scalar_line(line_text)
                if quoted and quoted != line_text:
                    return owner._format_suggestion(
                        "Invalid Entry: add the missing quote.",
                        line_text,
                        quoted,
                    )
            # Parser can report the next line; check nearby previous lines for
            # unquoted scalar values and prefer the quote fix in that case.
            nearby_line_no, nearby_line_text = owner._find_nearby_unquoted_value_line(
                getattr(exc, "lineno", None)
            )
            if nearby_line_text:
                quoted = owner._quote_unquoted_scalar_line(nearby_line_text)
                if quoted and quoted != nearby_line_text:
                    return owner._format_suggestion(
                        "Invalid Entry: add the missing quote.",
                        nearby_line_text,
                        quoted,
                    )
            if owner._is_missing_list_open_at_start(exc):
                before, after = "", "["
                return owner._format_suggestion(
                    "Invalid Entry: add \"[\" before the highlighted line.",
                    before,
                    after,
                )
            if owner._is_missing_object_open(exc):
                before, after = owner._suggestion_from_example(example, add_after="{")
                return owner._format_suggestion(
                    "Invalid Entry: add \"{\" after the highlighted line.",
                    before,
                    after,
                )
            if owner._is_missing_list_open(exc):
                before, after = owner._suggestion_from_example(example, add_after="[")
                return owner._format_suggestion(
                    "Invalid Entry: add \"[\" after the highlighted line.",
                    before,
                    after,
                )
            if owner._is_missing_list_close():
                before, after = owner._suggestion_from_example(example, add_after="],")
                return owner._format_suggestion(
                    "Invalid Entry: add the missing closing bracket.",
                    before,
                    after,
                )
        if msg == "Extra data":
            top_close_no, top_close_text = owner._find_nearby_illegal_comma_after_top_level_close_line(
                getattr(exc, "lineno", None) or 1
            )
            if top_close_text:
                return owner._format_suggestion(
                    "Invalid Entry: remove the trailing comma.",
                    top_close_text.strip(),
                    owner._fix_illegal_comma_after_top_level_close(top_close_text).strip(),
                )
            if owner._missing_object_open_from_extra_data():
                before, after = "", "{"
                return owner._format_suggestion(
                    "Invalid Entry: add \"{\" before the highlighted line.",
                    before,
                    after,
                )
            if owner._missing_list_open_from_extra_data():
                before, after = "", "["
                return owner._format_suggestion(
                    "Invalid Entry: add \"[\" before the highlighted line.",
                    before,
                    after,
                )
            before, after = owner._suggestion_from_example(example)
            return owner._format_suggestion(
                "Invalid Entry: extra data after a complete value. Remove it or wrap values in [].",
                before,
                after,
            )
        if msg in ("Unexpected ']'", "Unexpected '}'"):
            before, after = owner._suggestion_from_example(example)
            return owner._format_suggestion(
                "Invalid Entry: remove the extra closing bracket.",
                before,
                after,
            )
        if msg == "Unterminated string":
            before, after = owner._suggestion_from_example(example, add_after="\"")
            return owner._format_suggestion(
                "Invalid Entry: close the quote.",
                before,
                after,
            )
        # Default suggestion: if the example looks like an unterminated quoted
        # string (starts with a quote but lacks the closing quote), suggest
        # adding the missing closing quote so the splash shows the fix.
        before = example
        after = example
        try:
            if isinstance(example, str) and example.startswith('"') and not example.endswith('"'):
                before, after = owner._suggestion_from_example(example, add_after='"')
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            before, after = example, example
        return (
            "Invalid Entry: check the highlighted line.\n\n"
            f"{owner._format_suggestion('Suggestion', before, after, header_only=True)}"
        )
    return str(exc)


def build_symbol_json_diagnostic(owner, exc, lineno=None):
    msg = getattr(exc, "msg", "") or ""
    if msg not in (
        "Expecting ',' delimiter",
        "Expecting ':' delimiter",
        "Expecting property name enclosed in double quotes",
        "Expecting value",
        "Illegal trailing comma before end of object",
        "Illegal trailing comma before end of array",
        "Extra data",
    ) and not msg.startswith("Invalid control character") and not msg.startswith("Invalid \\escape"):
        return None

    line_no = lineno or (getattr(exc, "lineno", None) or 1)
    colno = getattr(exc, "colno", None) or 1

    # Missing closing quote in object key should win over symbol-tail rules,
    # regardless of which parser message variant was raised.
    invalid_escape_no, invalid_escape_text = owner._find_nearby_property_key_invalid_escape_line(line_no)
    if invalid_escape_text and invalid_escape_no:
        raw = owner._line_text(invalid_escape_no)
        span = owner._property_key_invalid_escape_span(raw)
        if span:
            start_col, end_col = span
        else:
            start_col = max(colno - 1, 0)
            end_col = start_col + 1
        return {
            "header": "Invalid Entry: replace the invalid escape with a double quote.",
            "before": invalid_escape_text.strip(),
            "after": owner._fix_property_key_invalid_escape(invalid_escape_text).strip(),
            "line": invalid_escape_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": "symbol_wrong_property_quote_char",
        }

    # Missing closing quote in object key should win over symbol-tail rules,
    # regardless of which parser message variant was raised.
    missing_key_quote_diag = owner._missing_key_quote_before_colon_diag(line_no, colno=colno)
    if missing_key_quote_diag:
        return missing_key_quote_diag

    # Wrong closer token in Expecting-value paths should use symbol-note
    # routing so the bad bracket is highlighted in red with a direct fix.
    # Keep missing-list-close handling prioritized because that path gives a
    # clearer key-line before/after correction for object-end `}` cases.
    if msg == "Expecting value":
        close_line, _insert_col, _before_line, _after_line = owner._find_missing_list_close_before_object_end(
            line_no
        )
        if not close_line:
            wrong_close = owner._find_wrong_closing_symbol_line(line_no, lookback=3)
            if wrong_close:
                bad_line, start_col, end_col, bad_token, expected, before_line, after_line = wrong_close
                token = str(bad_token or "").strip()
                if token.startswith(("]", "}")):
                    header = (
                        f'Invalid Entry: replace "{token}" with "{expected}".'
                        if token
                        else f'Invalid Entry: replace the wrong bracket with "{expected}".'
                    )
                    return {
                        "header": header,
                        "before": str(before_line or "").strip(),
                        "after": str(after_line or "").strip(),
                        "line": int(bad_line),
                        "start_col": int(start_col),
                        "end_col": int(end_col),
                        "note": "symbol_wrong_closing_bracket",
                    }
            raw_line = owner._line_text(line_no)
            stripped_line = str(raw_line or "").strip()
            if stripped_line.startswith(("]", "}")):
                first_col = 0
                for idx, ch in enumerate(str(raw_line or "")):
                    if not ch.isspace():
                        first_col = idx
                        break
                token = stripped_line.split()[0]
                expected = None
                if int(line_no) == 1:
                    next_line_no = owner._next_non_empty_line_number(1)
                    next_text = owner._line_text(next_line_no).strip() if next_line_no else ""
                    if owner._line_looks_like_object_property(next_text):
                        expected = "{"
                    elif next_text.startswith(("{", '"')):
                        expected = "["
                if not expected:
                    expected = "}" if token.startswith("]") else "]"
                return {
                    "header": f'Invalid Entry: replace "{token}" with "{expected}".',
                    "before": token,
                    "after": expected,
                    "line": int(line_no),
                    "start_col": int(first_col),
                    "end_col": int(first_col + len(token)),
                    "note": "symbol_wrong_closing_bracket",
                }
            if int(line_no) == 1:
                next_line_no = owner._next_non_empty_line_number(1)
                next_text = owner._line_text(next_line_no).strip() if next_line_no else ""
                if owner._line_looks_like_object_property(next_text):
                    raw_src = str(raw_line or "")
                    first_col = None
                    for idx, ch in enumerate(raw_src):
                        if ch == "\ufeff":
                            continue
                        if not ch.isspace():
                            first_col = idx
                            break
                    if first_col is not None:
                        end_col = first_col
                        while end_col < len(raw_src) and not raw_src[end_col].isspace():
                            end_col += 1
                        token = raw_src[first_col:end_col]
                        if token and token != "{" and not token.startswith(("{", '"', "[")):
                            return {
                                "header": f'Invalid Entry: replace "{token}" with "{{".',
                                "before": token,
                                "after": "{",
                                "line": 1,
                                "start_col": int(first_col),
                                "end_col": int(max(end_col, first_col + 1)),
                                "note": "symbol_wrong_opening_bracket",
                            }

    # Extra-data with an invalid top token before object properties should
    # flag that token as a red symbol error and suggest object-open "{"
    # instead of insertion-only missing-open guidance.
    if msg == "Extra data":
        first_line_no = owner._next_non_empty_line_number(0)
        if first_line_no == 1:
            raw_first = owner._line_text(1)
            first_col = None
            for idx, ch in enumerate(str(raw_first or "")):
                if ch == "\ufeff":
                    continue
                if not ch.isspace():
                    first_col = idx
                    break
            if first_col is not None:
                end_col = first_col
                raw_src = str(raw_first or "")
                while end_col < len(raw_src) and not raw_src[end_col].isspace():
                    end_col += 1
                token = raw_src[first_col:end_col]
                next_line_no = owner._next_non_empty_line_number(1)
                next_text = owner._line_text(next_line_no).strip() if next_line_no else ""
                if (
                    token
                    and token != "{"
                    and not token.startswith(('"', "{", "["))
                    and owner._line_looks_like_object_property(next_text)
                ):
                    return {
                        "header": f'Invalid Entry: replace "{token}" with "{{".',
                        "before": token,
                        "after": "{",
                        "line": 1,
                        "start_col": int(first_col),
                        "end_col": int(max(end_col, first_col + 1)),
                        "note": "symbol_wrong_opening_bracket",
                    }

    # Missing colon between key and value: "key" 123 -> "key": 123
    if msg == "Expecting ':' delimiter":
        missing_colon_no, missing_colon_text = owner._find_nearby_missing_colon_line(line_no)
        if missing_colon_text and missing_colon_no:
            raw = owner._line_text(missing_colon_no)
            span = owner._missing_colon_key_value_span(raw)
            if span:
                start_col, end_col = span
            else:
                start_col = max(colno - 1, 0)
                end_col = start_col
            return {
                "header": "Invalid Entry: add a colon after the highlighted name.",
                "before": missing_colon_text.strip(),
                "after": owner._missing_colon_example(missing_colon_text).strip(),
                "line": missing_colon_no,
                "start_col": start_col,
                "end_col": end_col,
                "note": "missing_colon_between_key_value",
            }

    # Key typo: "key",: value
    comma_before_no, comma_before_text = owner._find_nearby_comma_before_colon_line(line_no)
    if comma_before_text and comma_before_no:
        raw = owner._line_text(comma_before_no)
        span = owner._comma_before_colon_span(raw)
        if span:
            start_col, end_col = span
        else:
            start_col = max(colno - 1, 0)
            end_col = start_col + 1
        return {
            "header": "Invalid Entry: remove the extra comma.",
            "before": comma_before_text.strip(),
            "after": owner._fix_comma_before_colon(comma_before_text).strip(),
            "line": comma_before_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": "symbol_comma_before_colon",
        }

    # Value typo: "key":, value
    comma_after_no, comma_after_text = owner._find_nearby_comma_after_colon_line(line_no)
    if comma_after_text and comma_after_no:
        raw = owner._line_text(comma_after_no)
        span = owner._comma_after_colon_span(raw)
        if span:
            start_col, end_col = span
        else:
            start_col = max(colno - 1, 0)
            end_col = start_col + 1
        return {
            "header": "Invalid Entry: remove the extra comma.",
            "before": comma_after_text.strip(),
            "after": owner._fix_comma_after_colon(comma_after_text).strip(),
            "line": comma_after_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": "symbol_comma_after_colon",
        }

    colon_bad_no, colon_bad_text = owner._find_nearby_invalid_prefix_after_colon_line(line_no)
    if colon_bad_text and colon_bad_no:
        raw = owner._line_text(colon_bad_no)
        analysis = owner._analyze_invalid_prefix_after_colon(raw)
        if analysis:
            start_col = analysis["start_col"]
            end_col = analysis["end_col"]
            after_line = analysis["after"].strip()
        else:
            start_col = max(colno - 1, 0)
            end_col = start_col + 1
            after_line = owner._fix_invalid_prefix_after_colon(colon_bad_text).strip()
        header = (
            "Invalid Entry: remove the invalid symbol after the colon."
            if after_line and not after_line.endswith(":")
            else "Invalid Entry: add a valid value after the colon."
        )
        return {
            "header": header,
            "before": colon_bad_text.strip(),
            "after": after_line,
            "line": colon_bad_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": "symbol_after_colon",
        }

    # Closer typo: ",}" / ",]" should be "}," / "],".
    comma_close_no, comma_close_text = owner._find_nearby_comma_before_closer_line(line_no)
    if comma_close_text and comma_close_no:
        raw = owner._line_text(comma_close_no)
        span = owner._comma_before_closer_span(raw)
        if span:
            start_col, end_col = span
        else:
            start_col = max(colno - 1, 0)
            end_col = start_col + 1
        return {
            "header": "Invalid Entry: move the comma after the closing bracket.",
            "before": comma_close_text.strip(),
            "after": owner._fix_comma_before_closer(comma_close_text).strip(),
            "line": comma_close_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": "symbol_comma_before_closer",
        }

    # Comma-only separator line with invalid trailing symbols (for example ",)" / ",a").
    comma_tail_no, comma_tail_text = owner._find_nearby_comma_line_invalid_tail_line(line_no)
    if comma_tail_text and comma_tail_no:
        raw = owner._line_text(comma_tail_no)
        span = owner._comma_line_invalid_tail_span(raw)
        if span:
            start_col, end_col = span
        else:
            start_col = max(colno - 1, 0)
            end_col = start_col + 1
        return {
            "header": "Invalid Entry: replace the invalid trailing symbol with a closing bracket.",
            "before": comma_tail_text.strip(),
            "after": owner._fix_comma_line_invalid_tail(comma_tail_text, lineno=comma_tail_no).strip(),
            "line": comma_tail_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": "symbol_comma_before_close_tail",
        }

    # Top-level: "}," / "],," at EOF => remove trailing comma run.
    if msg == "Extra data":
        top_tail_no, top_tail_text = owner._find_nearby_top_level_close_symbol_run_line(line_no)
        if top_tail_text and top_tail_no:
            raw = owner._line_text(top_tail_no)
            span = owner._top_level_close_symbol_run_span(raw)
            if span:
                start_col, end_col = span
            else:
                start_col = max(colno - 1, 0)
                end_col = start_col + 1
            tail = raw[start_col:].strip() if start_col < len(raw) else ""
            if tail and set(tail) == {","}:
                header = "Invalid Entry: remove the trailing comma."
            else:
                header = "Invalid Entry: remove the invalid trailing symbol."
            return {
                "header": header,
                "before": top_tail_text.strip(),
                "after": owner._fix_top_level_close_symbol_run(top_tail_text).strip(),
                "line": top_tail_no,
                "start_col": start_col,
                "end_col": end_col,
                "note": "symbol_top_level_close_tail_run",
            }
        top_close_no, top_close_text = owner._find_nearby_illegal_comma_after_top_level_close_line(line_no)
        if top_close_text and top_close_no:
            raw = owner._line_text(top_close_no)
            span = owner._comma_run_after_top_level_close_span(raw)
            if span:
                start_col, end_col = span
            else:
                start_col = raw.rstrip().rfind(",")
                if start_col < 0:
                    start_col = max(colno - 1, 0)
                end_col = start_col + 1
            return {
                "header": "Invalid Entry: remove the trailing comma.",
                "before": top_close_text.strip(),
                "after": owner._fix_illegal_comma_after_top_level_close(top_close_text).strip(),
                "line": top_close_no,
                "start_col": start_col,
                "end_col": end_col,
                "note": "symbol_top_level_close_comma_run",
            }

    # Value line ending in comma before explicit close line.
    illegal_comma_no, illegal_comma_text = owner._find_nearby_illegal_trailing_comma_line(line_no)
    if illegal_comma_text and illegal_comma_no:
        raw = owner._line_text(illegal_comma_no)
        start_col = owner._trailing_comma_before_close_col(raw)
        if start_col is None:
            start_col = max(colno - 1, 0)
        return {
            "header": "Invalid Entry: remove the trailing comma.",
            "before": illegal_comma_text.strip(),
            "after": owner._fix_illegal_trailing_comma_before_close(illegal_comma_text).strip(),
            "line": illegal_comma_no,
            "start_col": start_col,
            "end_col": start_col + 1,
            "note": "symbol_trailing_comma_before_close",
        }

    # Generic duplicate-comma run at line end (e.g. "value",,).
    dup_run_no, dup_run_text = owner._find_nearby_duplicate_comma_run_line(line_no)
    if dup_run_text and dup_run_no:
        raw = owner._line_text(dup_run_no)
        span = owner._duplicate_comma_run_span(raw, lineno=dup_run_no)
        if span:
            start_col, end_col = span
        else:
            start_col = max(colno - 1, 0)
            end_col = start_col + 1
        keep_one = owner._line_requires_trailing_comma(dup_run_no)
        header = (
            "Invalid Entry: remove the extra comma."
            if keep_one
            else "Invalid Entry: remove the trailing comma."
        )
        return {
            "header": header,
            "before": dup_run_text.strip(),
            "after": owner._fix_duplicate_comma_run(dup_run_text, lineno=dup_run_no).strip(),
            "line": dup_run_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": "symbol_duplicate_comma_run",
        }

    # Quoted array item with mixed invalid tail symbols (e.g. ",,,,,@").
    bad_tail_no, bad_tail_text = owner._find_nearby_invalid_tail_after_quoted_item_line(line_no)
    if bad_tail_text and bad_tail_no:
        raw = owner._line_text(bad_tail_no)
        span = owner._quoted_item_invalid_tail_span(raw)
        if span:
            start_col, end_col = span
        else:
            start_col = max(colno - 1, 0)
            end_col = start_col + 1
        return {
            "header": "Invalid Entry: remove the invalid trailing symbol.",
            "before": bad_tail_text.strip(),
            "after": owner._fix_invalid_tail_after_quoted_item(bad_tail_text, bad_tail_no).strip(),
            "line": bad_tail_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": "symbol_quoted_item_invalid_tail",
        }

    # Invalid symbol run directly after opener ({ or [).
    open_no, open_text = owner._find_nearby_invalid_symbol_after_open_line(line_no)
    if open_text and open_no:
        raw = owner._line_text(open_no)
        span = owner._invalid_symbol_after_open_span(raw)
        if span:
            opener, start_col, end_col, symbol_text = span
        else:
            opener = "{"
            start_col = max(colno - 1, 0)
            end_col = start_col + 1
            symbol_text = ""
        fixed = owner._fix_invalid_symbol_after_open(raw).strip()
        if not fixed:
            fixed = opener
        header = (
            f'Invalid Entry: remove the comma after "{opener}".'
            if symbol_text == ","
            else f'Invalid Entry: remove the invalid symbol after "{opener}".'
        )
        return {
            "header": header,
            "before": open_text,
            "after": fixed,
            "line": open_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": "symbol_after_open",
        }

    # Duplicate comma at line end.
    dup_no, dup_text = owner._find_nearby_duplicate_trailing_comma_line(line_no)
    if dup_text and dup_no:
        raw = owner._line_text(dup_no)
        start_col = raw.rfind(",")
        if start_col < 0:
            start_col = max(colno - 1, 0)
        return {
            "header": "Invalid Entry: remove the extra comma.",
            "before": dup_text,
            "after": owner._fix_duplicate_trailing_comma(dup_text),
            "line": dup_no,
            "start_col": start_col,
            "end_col": start_col + 1,
            "note": "symbol_duplicate_trailing_comma",
        }

    # Invalid symbol run after a closer (}, ], etc).
    cl_no, cl_text = owner._find_nearby_invalid_symbol_after_closer_line(line_no)
    if cl_text and cl_no:
        raw = owner._line_text(cl_no)
        start_col = owner._first_invalid_symbol_after_closer_col(raw)
        if start_col is None:
            start_col = max(colno - 1, 0)
        end_col = len(raw.rstrip())
        if end_col <= start_col:
            end_col = start_col + 1
        return {
            "header": "Invalid Entry: replace the invalid trailing symbol with a comma.",
            "before": cl_text,
            "after": owner._fix_invalid_symbol_after_closer(cl_text),
            "line": cl_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": "symbol_after_closer",
        }

    # Invalid symbol run after a completed quoted string value.
    tail_no, tail_text = owner._find_nearby_invalid_trailing_symbols_line(line_no)
    if tail_text and tail_no:
        raw = owner._line_text(tail_no)
        start_col = owner._first_invalid_trailing_symbol_col(raw, lineno=tail_no)
        if start_col is None:
            start_col = max(colno - 1, 0)
        end_col = len(raw.rstrip())
        if end_col <= start_col:
            end_col = start_col + 1
        after_line = owner._fix_invalid_trailing_symbols_after_string_value(tail_text, tail_no)
        header = (
            "Invalid Entry: replace the invalid trailing symbol with a comma."
            if after_line.rstrip().endswith(",")
            else "Invalid Entry: remove the invalid trailing symbol."
        )
        return {
            "header": header,
            "before": tail_text,
            "after": after_line,
            "line": tail_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": "symbol_after_value",
        }

    return None


def build_json_diagnostic(owner, exc):
    msg = getattr(exc, "msg", "") or ""
    if msg not in (
        "Expecting ',' delimiter",
        "Expecting ':' delimiter",
        "Expecting property name enclosed in double quotes",
        "Expecting value",
        "Illegal trailing comma before end of object",
        "Illegal trailing comma before end of array",
        "Extra data",
    ) and not msg.startswith("Invalid control character") and not msg.startswith("Invalid \\escape"):
        return None

    lineno = getattr(exc, "lineno", None) or 1
    line_text = owner._line_text(lineno)
    stripped = line_text.strip()

    # 1) key: ,   -> key: [
    if owner._is_key_colon_comma_line(stripped):
        comma_col = line_text.find(",")
        if comma_col < 0:
            comma_col = max((getattr(exc, "colno", 1) or 1) - 1, 0)
        return {
            "header": 'Invalid Entry: add "[" after the highlighted line.',
            "before": stripped,
            "after": owner._key_colon_comma_to_list_open(stripped),
            "line": lineno,
            "start_col": comma_col,
            "end_col": comma_col + 1,
            "note": "missing_list_open_typed_comma",
        }

    # Missing closing value quote before comma/EOL should be resolved first
    # so cursor focus lands on the quote insertion point (before comma).
    if msg.startswith("Invalid control character") or msg in ("Expecting ',' delimiter", "Expecting value"):
        invalid_tail_no, invalid_tail_text, invalid_tail_span = (
            owner._find_nearby_unclosed_quoted_value_invalid_tail_line(lineno)
        )
        if invalid_tail_text and invalid_tail_no and invalid_tail_span:
            start_col, end_col = invalid_tail_span
            if end_col <= start_col:
                end_col = start_col + 1
            return {
                "header": "Invalid Entry: remove the invalid trailing symbol.",
                "before": str(invalid_tail_text).strip(),
                "after": owner._fix_missing_quote(str(invalid_tail_text)).strip(),
                "line": int(invalid_tail_no),
                "start_col": int(start_col),
                "end_col": int(end_col),
                "note": "invalid_trailing_symbol_after_value",
            }
        missing_quote_no, missing_quote_text, insert_col = owner._find_nearby_missing_value_close_quote_line(
            lineno
        )
        if missing_quote_text and missing_quote_no and insert_col is not None:
            return {
                "header": "Invalid Entry: add the missing quote.",
                "before": str(missing_quote_text).strip(),
                "after": owner._fix_missing_quote(str(missing_quote_text)).strip(),
                "line": int(missing_quote_no),
                "start_col": int(insert_col),
                "end_col": int(insert_col),
                "note": "missing_value_close_quote",
            }

    symbol_diag_builder = getattr(owner, "_build_symbol_json_diagnostic", None)
    if callable(symbol_diag_builder):
        symbol_diag = symbol_diag_builder(exc, lineno=lineno)
    else:
        # Test harness may bind only a subset of methods onto a namespace.
        symbol_diag = None
    if symbol_diag:
        return symbol_diag

    if (
        msg == "Expecting ',' delimiter"
        and not owner._is_missing_object_close()
        and not owner._is_missing_list_close()
    ):
        missing_comma_line = owner._find_missing_comma_between_block_values_line(lineno)
        if missing_comma_line:
            raw = owner._line_text(missing_comma_line)
            end_col = len(raw.rstrip())
            return {
                "header": "Invalid Entry: add a comma near the highlighted line.",
                "before": raw.strip(),
                "after": (raw.rstrip() + ",").strip(),
                "line": missing_comma_line,
                "start_col": end_col,
                "end_col": end_col,
                "note": "missing_comma_between_blocks",
            }

    if msg == "Expecting property name enclosed in double quotes" and owner._is_missing_object_close():
        comma_line = owner._find_comma_only_line_before(lineno)
        if comma_line:
            raw = owner._line_text(comma_line)
            comma_col = raw.find(",")
            if comma_col < 0:
                comma_col = 0
            return {
                "header": "Invalid Entry: add the missing closing bracket.",
                "before": ",",
                "after": "},",
                "line": comma_line,
                "start_col": comma_col,
                "end_col": comma_col + 1,
                "note": "missing_object_close_before_comma",
            }

    # 1.5) Bareword literal typo after ":" (e.g. "rue", "flase").
    if msg in ("Expecting value", "Expecting ',' delimiter"):
        bool_no, bool_text, bool_diag = owner._find_nearby_boolean_literal_typo_line(lineno)
        if bool_text and bool_no and bool_diag:
            return {
                "header": "Invalid Entry: fix the boolean value.",
                "before": bool_text.strip(),
                "after": bool_diag["after"].strip(),
                "line": bool_no,
                "start_col": bool_diag["start_col"],
                "end_col": bool_diag["end_col"],
                "note": "boolean_literal_typo",
            }

    # Missing opening value quote should be insertion-focused on the edited
    # line, but only after symbol + literal typo diagnostics have priority.
    if msg in ("Expecting value", "Expecting ',' delimiter"):
        open_quote_no, open_quote_text, insert_col = owner._find_nearby_missing_value_open_quote_line(lineno)
        if open_quote_text and open_quote_no and insert_col is not None:
            return {
                "header": "Invalid Entry: add the missing quote.",
                "before": str(open_quote_text).strip(),
                "after": owner._quote_unquoted_scalar_line(str(open_quote_text)).strip(),
                "line": int(open_quote_no),
                "start_col": int(insert_col),
                "end_col": int(insert_col),
                "note": "missing_value_open_quote",
            }

    # `[` opened list directly followed by object closer `}`.
    # Show a concrete insertion fix at the `}` line.
    if msg == "Expecting value":
        close_line, insert_col, before_line, after_line = owner._find_missing_list_close_before_object_end(lineno)
        if close_line:
            return {
                "header": "Invalid Entry: add the missing closing bracket.",
                "before": str(before_line or "").strip() or '"<key>": [',
                "after": str(after_line or "").strip() or '"<key>": []',
                "line": close_line,
                "start_col": int(insert_col),
                "end_col": int(insert_col),
                "note": "missing_list_close_before_object_end",
            }

    # 2) Extra-data case: trailing comma after top-level close (e.g. "},").
    if msg == "Extra data":
        top_close_no, top_close_text = owner._find_nearby_illegal_comma_after_top_level_close_line(lineno)
        if top_close_text and top_close_no:
            raw = owner._line_text(top_close_no)
            span = owner._comma_run_after_top_level_close_span(raw)
            if span:
                comma_col, end_col = span
            else:
                comma_col = raw.rstrip().rfind(",")
                if comma_col < 0:
                    comma_col = max((getattr(exc, "colno", 1) or 1) - 1, 0)
                end_col = comma_col + 1
            return {
                "header": "Invalid Entry: remove the trailing comma.",
                "before": top_close_text.strip(),
                "after": owner._fix_illegal_comma_after_top_level_close(top_close_text).strip(),
                "line": top_close_no,
                "start_col": comma_col,
                "end_col": end_col,
                "note": "illegal_comma_after_top_level_close",
            }

    # 3) "value", followed by object/array closer on next non-empty line.
    illegal_comma_no, illegal_comma_text = owner._find_nearby_illegal_trailing_comma_line(lineno)
    if illegal_comma_text and illegal_comma_no:
        raw = owner._line_text(illegal_comma_no)
        comma_col = owner._trailing_comma_before_close_col(raw)
        if comma_col is None:
            comma_col = max((getattr(exc, "colno", 1) or 1) - 1, 0)
        return {
            "header": "Invalid Entry: remove the trailing comma.",
            "before": illegal_comma_text.strip(),
            "after": owner._fix_illegal_trailing_comma_before_close(illegal_comma_text).strip(),
            "line": illegal_comma_no,
            "start_col": comma_col,
            "end_col": comma_col + 1,
            "note": "illegal_trailing_comma_before_close",
        }

    # 4) {, / [@ / etc -> remove invalid symbol(s) after opener
    open_no, open_text = owner._find_nearby_invalid_symbol_after_open_line(lineno)
    if open_text and open_no:
        raw = owner._line_text(open_no)
        span = owner._invalid_symbol_after_open_span(raw)
        if span:
            opener, col_idx, end_col, symbol_text = span
        else:
            opener = "{"
            col_idx = max((getattr(exc, "colno", 1) or 1) - 1, 0)
            end_col = col_idx + 1
            symbol_text = ""
        fixed = owner._fix_invalid_symbol_after_open(raw).strip()
        if not fixed:
            fixed = opener
        header = (
            f'Invalid Entry: remove the comma after "{opener}".'
            if symbol_text == ","
            else f'Invalid Entry: remove the invalid symbol after "{opener}".'
        )
        return {
            "header": header,
            "before": open_text,
            "after": fixed,
            "line": open_no,
            "start_col": col_idx,
            "end_col": end_col,
            "note": "invalid_symbol_after_open",
        }

    # 5) ...","  -> remove extra quote
    stray_no, stray_text = owner._find_nearby_trailing_stray_quote_line(lineno)
    if stray_text and stray_no:
        raw = owner._line_text(stray_no)
        qidx = raw.rfind('"')
        if qidx < 0:
            qidx = max((getattr(exc, "colno", 1) or 1) - 1, 0)
        return {
            "header": "Invalid Entry: remove the extra quote.",
            "before": stray_text,
            "after": owner._fix_trailing_stray_quote_after_comma(stray_text),
            "line": stray_no,
            "start_col": qidx,
            "end_col": qidx + 1,
            "note": "trailing_stray_quote_after_comma",
        }

    # 6) ...""  -> replace extra quote with comma
    ex_no, ex_text = owner._find_nearby_extra_quote_in_value_line(lineno)
    if ex_text and ex_no:
        raw = owner._line_text(ex_no)
        qidx = raw.rfind('""')
        qcol = qidx + 1 if qidx >= 0 else max((getattr(exc, "colno", 1) or 1) - 1, 0)
        return {
            "header": "Invalid Entry: add a comma near the highlighted line.",
            "before": ex_text,
            "after": owner._fix_extra_quote_to_comma(ex_text),
            "line": ex_no,
            "start_col": qcol,
            "end_col": qcol + 1,
            "note": "extra_quote_missing_comma",
        }

    # 7) ...,,  -> remove extra comma
    dup_no, dup_text = owner._find_nearby_duplicate_trailing_comma_line(lineno)
    if dup_text and dup_no:
        raw = owner._line_text(dup_no)
        comma_col = raw.rfind(",")
        if comma_col < 0:
            comma_col = max((getattr(exc, "colno", 1) or 1) - 1, 0)
        return {
            "header": "Invalid Entry: remove the extra comma.",
            "before": dup_text,
            "after": owner._fix_duplicate_trailing_comma(dup_text),
            "line": dup_no,
            "start_col": comma_col,
            "end_col": comma_col + 1,
            "note": "duplicate_trailing_comma",
        }

    # 8) }./]@ etc -> invalid symbol after closer
    cl_no, cl_text = owner._find_nearby_invalid_symbol_after_closer_line(lineno)
    if cl_text and cl_no:
        raw = owner._line_text(cl_no)
        col_idx = owner._first_invalid_symbol_after_closer_col(raw)
        if col_idx is None:
            col_idx = max((getattr(exc, "colno", 1) or 1) - 1, 0)
        end_col = len(raw.rstrip())
        if end_col <= col_idx:
            end_col = col_idx + 1
        return {
            "header": "Invalid Entry: replace the invalid trailing symbol with a comma.",
            "before": cl_text,
            "after": owner._fix_invalid_symbol_after_closer(cl_text),
            "line": cl_no,
            "start_col": col_idx,
            "end_col": end_col,
            "note": "invalid_trailing_symbol_after_closer",
        }

    # 9) "key": "value",@  or ,11  -> invalid tail after value
    tail_no, tail_text = owner._find_nearby_invalid_trailing_symbols_line(lineno)
    if tail_text and tail_no:
        raw = owner._line_text(tail_no)
        col_idx = owner._first_invalid_trailing_symbol_col(raw, lineno=tail_no)
        if col_idx is None:
            col_idx = max((getattr(exc, "colno", 1) or 1) - 1, 0)
        end_col = len(raw.rstrip())
        if end_col <= col_idx:
            end_col = col_idx + 1
        after_line = owner._fix_invalid_trailing_symbols_after_string_value(tail_text, tail_no)
        header = (
            "Invalid Entry: replace the invalid trailing symbol with a comma."
            if after_line.rstrip().endswith(",")
            else "Invalid Entry: remove the invalid trailing symbol."
        )
        return {
            "header": header,
            "before": tail_text,
            "after": after_line,
            "line": tail_no,
            "start_col": col_idx,
            "end_col": end_col,
            "note": "invalid_trailing_symbol_after_value",
        }

    return None

def _quote_unquoted_value(owner, line_text):
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

def _quote_unquoted_scalar_line(owner, line_text):
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

def _line_needs_value_quotes(owner, line_text):
    if not line_text:
        return False
    fixed = owner._quote_unquoted_scalar_line(line_text)
    return bool(fixed and fixed != line_text)

def _missing_value_close_quote_insert_col(owner, line_text):
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

def _missing_value_open_quote_insert_col(owner, line_text):
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

def _find_nearby_missing_value_close_quote_line(owner, lineno, lookback=2):
    if not lineno:
        return None, None, None
    candidates = []
    try:
        candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        pass
    line = max(lineno - 1, 1)
    scanned = 0
    while line >= 1 and scanned < lookback:
        try:
            txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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

def _find_nearby_missing_value_open_quote_line(owner, lineno, lookback=3):
    if not lineno:
        return None, None, None
    candidates = []
    try:
        candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        pass
    line = max(lineno - 1, 1)
    scanned = 0
    while line >= 1 and scanned < lookback:
        try:
            txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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

def _find_nearby_unquoted_value_line(owner, lineno, lookback=3):
    if not lineno:
        return None, None
    # Check current line first, then a few previous non-empty lines.
    candidates = []
    try:
        candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()))
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        pass
    line = max(lineno - 1, 1)
    scanned = 0
    while line >= 1 and scanned < lookback:
        try:
            txt = owner.text.get(f"{line}.0", f"{line}.0 lineend").strip()
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            break
        if txt:
            candidates.append((line, txt))
            scanned += 1
        line -= 1
    for ln, txt in candidates:
        if owner._line_needs_value_quotes(txt):
            return ln, txt
    return None, None

def _suggest_json_literal_from_token(owner, token):
    return json_diag_core.suggest_json_literal_from_token(token)

def _boolean_literal_typo_diagnostic(owner, line_text):
    return json_diag_core.boolean_literal_typo_diagnostic(line_text)

def _find_nearby_boolean_literal_typo_line(owner, lineno, lookback=3):
    return json_diag_core.find_nearby_boolean_literal_typo_line(
        owner._line_text,
        lineno,
        lookback=lookback,
    )

def _is_wrong_list_open_for_object(owner, prev_text, next_text):
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

def _find_wrong_list_open_line(owner, lineno, lookback=3):
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

def _find_wrong_object_open_line(owner, lineno, lookback=3):
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

def _expected_closer_before_position(owner, target_line, target_col):
    return json_diag_core.expected_closer_before_position(
        owner._line_text,
        target_line,
        target_col,
    )

def _find_wrong_closing_symbol_line(owner, lineno, lookback=2):
    return json_diag_core.find_wrong_closing_symbol_line(
        owner._line_text,
        lineno,
        lookback=lookback,
    )

def _find_missing_list_close_before_object_end(owner, lineno, lookback=4):
    return json_diag_core.find_missing_list_close_before_object_end(
        owner._line_text,
        owner._closest_non_empty_line_before,
        lineno,
        lookback=lookback,
    )

def _next_non_empty_line_number(owner, start_line):
    try:
        last_line = int(owner.text.index("end-1c").split(".")[0])
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        return None
    line = max(start_line + 1, 1)
    while line <= last_line:
        text = owner._line_text(line)
        if text.strip():
            return line
        line += 1
    return None

def _missing_list_open_key_line(owner, lineno):
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

@staticmethod
def _line_looks_like_object_property(line_text):
    return bool(re.match(r'^"[^"]+"\s*:', str(line_text or "").strip()))

def _find_missing_container_open_after_key_line(owner, lineno, lookback=6):
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

def _find_missing_list_open_after_key_line(owner, lineno, lookback=6):
    line, opener = owner._find_missing_container_open_after_key_line(
        lineno, lookback=lookback
    )
    if opener == "[":
        return line
    return None

def _missing_close_example(owner, msg):
    if msg in ("Expecting ']'", "Unexpected ']'"):
        return "],"
    return "},"

def _format_suggestion(owner, header, before, after, header_only=False):
    if header_only:
        return f"Suggestion:\n- Before: {before}\n- After:  {after}"
    return f"{header}\n\nSuggestion:\n- Before: {before}\n- After:  {after}"

def _suggestion_from_example(owner, example, add_after=None, add_colon=False, quote_key=False):
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
def _is_missing_object_open_at(owner, lineno):
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

def _line_text(owner, lineno):
    try:
        return owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        return ""

def _line_has_missing_open_key_quote(owner, line_text):
    stripped = (line_text or "").lstrip()
    if not stripped or stripped.startswith("\""):
        return False
    if "\":" not in stripped:
        return False
    first = stripped[0]
    return first.isalpha() or first == "_"

def _missing_close_target_line_from_exc(owner, exc, open_bracket, close_bracket):
    line = getattr(exc, "lineno", None)
    if line:
        return line
    return owner._missing_close_target_line(open_bracket, close_bracket)

def _missing_close_target_line_any(owner, exc):
    if owner._is_missing_object_close():
        line, _idx = owner._missing_close_insertion_point("{", "}", exc)
        if line:
            return line
    if owner._is_missing_list_close():
        line, _idx = owner._missing_close_insertion_point("[", "]", exc)
        if line:
            return line
    return None

def _missing_list_close_target_line(owner, exc):
    line, _idx = owner._missing_close_insertion_point("[", "]", exc)
    return line

def _unmatched_open_bracket_lines(owner, open_bracket, close_bracket):
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

def _is_missing_list_close(owner):
    return bool(owner._unmatched_open_bracket_lines("[", "]"))

def _is_missing_object_close(owner):
    return bool(owner._unmatched_open_bracket_lines("{", "}"))

def _last_unmatched_bracket_line(owner, open_bracket, close_bracket):
    stack = owner._unmatched_open_bracket_lines(open_bracket, close_bracket)
    if stack:
        return stack[-1]
    return None

def _line_indent_width(owner, lineno):
    raw = owner._line_text(lineno)
    return len(raw) - len(raw.lstrip(" \t"))

def _missing_close_insertion_point(owner, open_bracket, close_bracket, exc=None):
    open_line = owner._last_unmatched_bracket_line(open_bracket, close_bracket)
    try:
        max_line = int(owner.text.index("end-1c").split(".")[0])
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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

def _missing_object_close_target_line(owner, exc):
    line, _idx = owner._missing_close_insertion_point("{", "}", exc)
    return line

def _find_comma_only_line_before(owner, start_line):
    line = max(start_line - 1, 1)
    while line >= 1:
        try:
            text = owner.text.get(f"{line}.0", f"{line}.0 lineend").strip()
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            return None
        if text == ",":
            return line
        line -= 1
    return None

def _find_missing_comma_between_block_values_line(owner, line):
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

def _find_blank_line_before(owner, start_line):
    line = max(start_line - 1, 1)
    while line >= 1:
        try:
            text = owner.text.get(f"{line}.0", f"{line}.0 lineend")
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            return None
        if text.strip() == "":
            return line
        line -= 1
    return None

def _closest_non_empty_line_before(owner, start_line):
    line = max(start_line - 1, 1)
    while line >= 1:
        try:
            text = owner.text.get(f"{line}.0", f"{line}.0 lineend").strip()
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            return None
        if text:
            return line
        line -= 1
    return None

def _last_non_empty_line_number(owner):
    try:
        line = int(owner.text.index("end-1c").split(".")[0])
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        return None
    while line >= 1:
        try:
            text = owner.text.get(f"{line}.0", f"{line}.0 lineend").strip()
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            return None
        if text:
            return line
        line -= 1
    return None


def _missing_close_target_line(owner, open_bracket, close_bracket):
    open_line = owner._last_unmatched_bracket_line(open_bracket, close_bracket)
    if not open_line:
        return None
    line = open_line + 1
    last_line = int(owner.text.index("end-1c").split(".")[0])
    while line <= last_line:
        try:
            text = owner.text.get(f"{line}.0", f"{line}.0 lineend")
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            return open_line
        if text.strip():
            return line
        line += 1
    return open_line

def _is_missing_object_open(owner, exc):
    lineno = getattr(exc, "lineno", None)
    if not lineno:
        return False
    prev_line = owner._previous_non_empty_line(lineno)
    if not prev_line:
        return False
    prev_line_stripped = prev_line.strip()
    return prev_line_stripped.endswith("\":") and not prev_line_stripped.endswith("\": {")

def _is_missing_list_open(owner, exc):
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

def _is_missing_list_open_at_start(owner, exc, allow_any_position=False):
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

def _missing_list_open_top_level(owner):
    first_line = owner._next_non_empty_line(1)
    if not first_line:
        return False
    first_text = owner._line_text(first_line).lstrip()
    if first_text.startswith("\ufeff"):
        first_text = first_text.lstrip("\ufeff")
    if not first_text or first_text.startswith("["):
        return False
    return first_text.startswith("{") or first_text.startswith("\"")

def _missing_object_open_from_extra_data(owner):
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

def _first_non_ws_char(owner):
    try:
        text = owner.text.get("1.0", "end-1c")
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        return ""
    for ch in text:
        if ch == "\ufeff":
            continue
        if ch.isspace():
            continue
        return ch
    return ""

def _missing_list_open_from_extra_data(owner):
    # Only treat as missing list open for the "Extra data" parser error.
    if getattr(owner, "_last_json_error_msg", "") != "Extra data":
        return False
    if owner._missing_object_open_from_extra_data():
        return False
    first_char = owner._first_non_ws_char()
    if not first_char or first_char == "[":
        return False
    return True

def _previous_non_empty_line(owner, lineno):
    line = max(lineno - 1, 1)
    while line >= 1:
        try:
            text = owner.text.get(f"{line}.0", f"{line}.0 lineend")
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            return ""
        if text.strip():
            return text
        line -= 1
    return ""

def _next_non_empty_line(owner, lineno):
    line = max(lineno, 1)
    last_line = int(owner.text.index("end-1c").split(".")[0])
    while line <= last_line:
        try:
            text = owner.text.get(f"{line}.0", f"{line}.0 lineend")
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            return ""
        if text.strip():
            return text
        line += 1
    return ""

def _missing_object_example(owner, lineno):
    prev_line = owner._previous_non_empty_line(lineno)
    if not prev_line:
        return "\"data\": {"
    prev_line_stripped = prev_line.strip()
    if prev_line_stripped.endswith("\":"):
        return prev_line_stripped + " {"
    return "\"data\": {"

def _close_before_list(owner, lineno):
    next_text = owner._next_non_empty_line(lineno or 1)
    if not next_text:
        return False
    return next_text.strip().startswith("]")

def _quote_property_name(owner, line_text):
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

def _highlight_custom_range(owner, line, start_col, end_col):
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
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        return

def _fix_missing_at(owner, value, domain_roots=None):
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
    # If there's no dot in the value, it's unlikely to be an email (e.g. IBAN).
    # Do not append '@' in that case; return the original value unchanged.
    return value

def _format_phone(owner, value):
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) != 10:
        return None
    return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"

def _find_phone_format_issue(owner):
    try:
        text = owner.text.get("1.0", "end-1c")
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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

def _fix_missing_space_after_colon(owner, line_text):
    if not line_text:
        return line_text
    # Normalize object-member style: "key": value
    return re.sub(r'^(\s*"[^"]+"\s*):\s*(\S.*)$', r"\1: \2", line_text.rstrip(), count=1)

def _find_json_spacing_issue(owner):
    """Detect valid-JSON style issues we enforce in editor text.

    Current rule:
    - object member must include a space after ":" (e.g. `"key": value`)
    """
    try:
        text = owner.text.get("1.0", "end-1c")
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        return None
    for line_no, line_text in enumerate(text.splitlines(), start=1):
        # Match object-member lines where ":" is immediately followed by a
        # non-whitespace character (e.g. `"isMine":true`).
        m = re.match(r'^(?P<head>\s*"[^"]+"\s*):(?P<tail>\S.*)$', line_text)
        if not m:
            continue
        head = m.group("head") or ""
        tail = m.group("tail") or ""
        if not tail:
            continue
        before = line_text.strip()
        after = owner._fix_missing_space_after_colon(line_text).strip()
        # Highlight at the value start after ":" so the missing space is obvious.
        start_col = len(head) + 1
        end_col = start_col + 1
        return line_no, start_col, end_col, before, after
    return None

def _find_missing_email_at(owner):
    try:
        text = owner.text.get("1.0", "end-1c")
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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

def _path_targets_email(owner, path):
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

def _looks_like_email_candidate(owner, value):
    value = (value or "").strip()
    if not value:
        return False
    if "@" in value:
        return True
    if "." not in value:
        return False
    return re.search(r"[A-Za-z]", value) is not None

def _should_validate_email_path_value(owner, path, value):
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

def _iter_candidate_email_values(owner, node, rel_path=None):
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

def _format_path_for_display(owner, path):
    return tree_view_service.format_path_for_display(path)

def _find_value_span_in_editor(owner, value, preferred_key=None):
    try:
        text = owner.text.get("1.0", "end-1c")
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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

def _find_invalid_email_in_value(owner, base_path, value):
    # Direct string edit for an email-targeted field.
    if (
        isinstance(value, str)
        and owner._path_targets_email(base_path)
        and owner._should_validate_email_path_value(base_path, value)
    ):
        issue = owner._validate_email_address(value)
        if issue:
            return base_path, value, issue
    # Nested object/list edit: validate all candidate email fields.
    if isinstance(value, (dict, list)):
        for rel_path, email_val in owner._iter_candidate_email_values(value):
            issue = owner._validate_email_address(email_val)
            if issue:
                return list(base_path) + list(rel_path), email_val, issue
    return None

def _best_domain_root_similarity(owner, root):
    if not root:
        return 0.0
    return max(
        (difflib.SequenceMatcher(None, root.lower(), known).ratio() for known in owner.KNOWN_EMAIL_DOMAIN_ROOTS),
        default=0.0,
    )

def _suggest_known_domain_from_local_and_domain(owner, local, domain):
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

def _suggest_email_for_malformed(owner, value):
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
    # If the second-level domain is too short, first try rebuilding it
    # from known roots by pulling only the missing prefix from local-part.
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
            # Prefer the longest matched root (more specific fix).
            if len(root) > best_prefix_len:
                best_prefix_len = len(root)
                best_prefix_fix = f"{cand_local}@{cand_domain}"
        if best_prefix_fix:
            return best_prefix_fix

    merged = local + sld
    local_re = re.compile(r"^[A-Za-z0-9._%+\-]+$")
    best = None
    best_score = -10**9
    original_len = len(local)
    for split_idx in range(1, len(merged)):
        cand_local = merged[:split_idx]
        cand_sld = merged[split_idx:]
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
        score -= abs(split_idx - original_len) * 2.0
        if score > best_score:
            best_score = score
            best = f"{cand_local}@{cand_domain}"
    return best if best else "<name>@<domain.tld>"

def _validate_email_address(owner, value):
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
            close = difflib.get_close_matches(domain_lower, sorted(owner.KNOWN_EMAIL_DOMAINS), n=1, cutoff=0.72)
            if close:
                suggestion = f"{local}@{close[0]}"
        return {
            "message": "Invalid Entry: unknown email domain.",
            "log_msg": "Unknown email domain",
            "note": "unknown_email_domain",
            "suggested": suggestion or "<name>@<domain.tld>",
        }

    return None

def _is_valid_email_domain(owner, domain):
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

def _find_invalid_email_format_issue(owner):
    try:
        text = owner.text.get("1.0", "end-1c")
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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

def _fix_missing_quote(owner, line_text):
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

def _unclosed_quoted_value_invalid_tail_span(owner, line_text):
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

def _find_nearby_unclosed_quoted_value_invalid_tail_line(owner, lineno, lookback=2):
    if not lineno:
        return None, None, None
    candidates = []
    try:
        candidates.append((lineno, owner.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        pass
    line = max(lineno - 1, 1)
    scanned = 0
    while line >= 1 and scanned < lookback:
        try:
            txt = owner.text.get(f"{line}.0", f"{line}.0 lineend")
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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

def _comma_example_line(owner, lineno):
    if not lineno:
        return "\"item1\",\n\"item2\""
    target_line = max(lineno - 1, 1)
    try:
        line_text = owner.text.get(f"{target_line}.0", f"{target_line}.0 lineend").strip()
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        line_text = ""
    if not line_text:
        return "\"item1\",\n\"item2\""
    if not line_text.endswith(","):
        line_text = line_text.rstrip()
        line_text = line_text + ","
    return line_text

def _symbol_error_focus_index(owner, start_index, end_index):
    try:
        segment = owner.text.get(start_index, end_index)
        if not segment:
            return end_index
        trimmed = len(segment.rstrip())
        if trimmed <= 0:
            return end_index
        return owner.text.index(f"{start_index} +{trimmed}c")
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        return end_index

def _apply_json_error_highlight(owner, exc, line, start_index, end_index, note=""):
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
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            pass
    owner._error_focus_index = focus_index
    if insertion_only:
        # Ensure insertion target is visible before placing marker/pin.
        try:
            owner.text.see(start_index)
            owner.text.update_idletasks()
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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
            except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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
                    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                        pass
                else:
                    subtle_start = start_index
                    subtle_end = owner.text.index(f"{start_index} +1c")
                owner.text.tag_add("json_error", subtle_start, subtle_end)
            except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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


