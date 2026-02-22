"""Core JSON highlight decision flow.

Selects highlight spans/notes for parser errors; rendering is delegated via
callbacks so UI layers remain swappable.
"""

def highlight_json_error(owner, exc, apply_highlight_fn, log_error_fn):
    line = getattr(exc, "lineno", None)
    col = getattr(exc, "colno", None)
    try:
        last_line = int(owner.text.index("end-1c").split(".")[0])
        if not line:
            line = 1
        if not col:
            col = 1
        line = min(max(line, 1), max(last_line, 1))
        # Diagnostics baseline: always record parse-entry so failures never appear
        # as "blank/no diagnostics" even if later highlight routing short-circuits.
        try:
            log_error_fn(owner, exc, line, note="overlay_parse_enter")
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            pass
        msg = getattr(exc, "msg", None)
        owner._last_json_error_msg = msg
        diag = owner._build_json_diagnostic(exc)
        if diag:
            line = diag["line"]
            start_index = f"{line}.{diag['start_col']}"
            end_index = f"{line}.{diag['end_col']}"
            apply_highlight_fn(owner, 
                exc, line, start_index, end_index, note=diag["note"]
            )
            return
        if msg in (
            "Illegal trailing comma before end of object",
            "Illegal trailing comma before end of array",
        ):
            illegal_no, illegal_text = owner._find_nearby_illegal_trailing_comma_line(line)
            if illegal_text and illegal_no:
                line = illegal_no
                raw = owner._line_text(line)
                comma_col = owner._trailing_comma_before_close_col(raw)
                if comma_col is None:
                    comma_col = max(col - 1, 0)
                start_index = f"{line}.{comma_col}"
                end_index = f"{line}.{comma_col + 1}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="illegal_trailing_comma_before_close"
                )
                return
        if msg == "Extra data":
            try:
                debug_char = owner._first_non_ws_char()
                note = f"highlight_enter_extra first_char={debug_char!r}"
                log_error_fn(owner, exc, line or 1, note=note)
            except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                pass
            top_close_no, top_close_text = owner._find_nearby_illegal_comma_after_top_level_close_line(line)
            if top_close_text and top_close_no:
                line = top_close_no
                raw = owner._line_text(line)
                span = owner._comma_run_after_top_level_close_span(raw)
                if span:
                    comma_col, end_col = span
                else:
                    comma_col = raw.rstrip().rfind(",")
                    if comma_col < 0:
                        comma_col = max(col - 1, 0)
                    end_col = comma_col + 1
                start_index = f"{line}.{comma_col}"
                end_index = f"{line}.{end_col}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="illegal_comma_after_top_level_close"
                )
                return
        if msg == "Extra data" and owner._missing_object_open_from_extra_data():
            first_line = owner._next_non_empty_line_number(0) or 1
            # Highlight the insertion slot before the first key line.
            # If there is a blank line above, use it; otherwise use line start.
            if first_line > 1 and not owner._line_text(first_line - 1).strip():
                line = first_line - 1
                start_index = f"{line}.0"
                end_index = f"{line}.0"
            else:
                line = max(first_line, 1)
                start_index = f"{line}.0"
                end_index = f"{line}.0"
            apply_highlight_fn(owner, 
                exc, line, start_index, end_index, note="missing_object_open_start"
            )
            return
        if msg and msg.startswith("Invalid control character"):
            stray_line_no, stray_line_text = owner._find_nearby_trailing_stray_quote_line(line)
            if stray_line_text and stray_line_no:
                line = stray_line_no
                line_text = owner._line_text(line)
                qidx = line_text.rfind('"')
                if qidx < 0:
                    qidx = max(col - 1, 0)
                start_index = f"{line}.{qidx}"
                end_index = f"{line}.{qidx + 1}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="trailing_stray_quote_after_comma"
                )
                return
            invalid_tail_no, invalid_tail_text = owner._find_nearby_invalid_trailing_symbols_line(line)
            if invalid_tail_text and invalid_tail_no:
                line = invalid_tail_no
                line_text = owner._line_text(line)
                col_idx = owner._first_invalid_trailing_symbol_col(line_text, lineno=line)
                if col_idx is None:
                    col_idx = max(col - 1, 0)
                start_index = f"{line}.{col_idx}"
                end_col = len(line_text.rstrip())
                if end_col <= col_idx:
                    end_col = col_idx + 1
                end_index = f"{line}.{end_col}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="invalid_trailing_symbol_after_value"
                )
                return
            start_index = f"{line}.{max(col - 1, 0)}"
            end_index = f"{line}.{col}"
            apply_highlight_fn(owner, 
                exc, line, start_index, end_index, note="invalid_control_char"
            )
            return
        if msg in (
            "Expecting ':' delimiter",
            "Expecting property name enclosed in double quotes",
            "Expecting ',' delimiter",
            "Expecting value",
            "Expecting ']'",
            "Expecting '}'",
        ):
            if not (msg == "Expecting ',' delimiter" and owner._is_missing_object_close()):
                missing_key_line, missing_open = owner._find_missing_container_open_after_key_line(line)
                if missing_key_line and missing_open in ("[", "{"):
                    line = missing_key_line
                    line_end = owner.text.index(f"{line}.0 lineend")
                    start_index = line_end
                    end_index = line_end
                    missing_note = (
                        "missing_object_open_after_key"
                        if missing_open == "{"
                        else "missing_list_open_after_key"
                    )
                    apply_highlight_fn(owner, 
                        exc, line, start_index, end_index, note=missing_note
                    )
                    return
        if owner._missing_list_open_from_extra_data():
            line = 1
            start_index = f"{line}.0"
            end_index = f"{line}.0"
            apply_highlight_fn(owner, 
                exc, line, start_index, end_index, note="missing_list_open_start"
            )
            return
        if msg == "Expecting ',' delimiter":
            if not owner._is_missing_object_close() and not owner._is_missing_list_close():
                missing_comma_line = owner._find_missing_comma_between_block_values_line(line)
                if missing_comma_line:
                    line = missing_comma_line
                    line_end = owner.text.index(f"{line}.0 lineend")
                    apply_highlight_fn(owner, 
                        exc, line, line_end, line_end, note="missing_comma_between_blocks"
                    )
                    return
            line_text = owner._line_text(line)
            stray_line_no, stray_line_text = owner._find_nearby_trailing_stray_quote_line(line)
            if stray_line_text and stray_line_no:
                line = stray_line_no
                line_text = owner._line_text(line)
                qidx = line_text.rfind('"')
                if qidx < 0:
                    qidx = max(col - 1, 0)
                start_index = f"{line}.{qidx}"
                end_index = f"{line}.{qidx + 1}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="trailing_stray_quote_after_comma"
                )
                return
            invalid_closer_no, invalid_closer_text = owner._find_nearby_invalid_symbol_after_closer_line(line)
            if invalid_closer_text and invalid_closer_no:
                line = invalid_closer_no
                line_text = owner._line_text(line)
                col_idx = owner._first_invalid_symbol_after_closer_col(line_text)
                if col_idx is None:
                    col_idx = max(col - 1, 0)
                start_index = f"{line}.{col_idx}"
                end_col = len(line_text.rstrip())
                if end_col <= col_idx:
                    end_col = col_idx + 1
                end_index = f"{line}.{end_col}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="invalid_trailing_symbol_after_closer"
                )
                return
            if owner._line_extra_quote_in_string_value(line_text):
                qidx = line_text.rfind('""')
                quote_col = qidx + 1 if qidx >= 0 else max(col - 1, 0)
                start_index = f"{line}.{quote_col}"
                end_index = f"{line}.{quote_col + 1}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="extra_quote_missing_comma"
                )
                return
            invalid_tail_no, invalid_tail_text = owner._find_nearby_invalid_trailing_symbols_line(line)
            if invalid_tail_text and invalid_tail_no:
                line = invalid_tail_no
                line_text = owner._line_text(line)
                col_idx = owner._first_invalid_trailing_symbol_col(line_text, lineno=line)
                if col_idx is None:
                    col_idx = max(col - 1, 0)
                start_index = f"{line}.{col_idx}"
                end_col = len(line_text.rstrip())
                if end_col <= col_idx:
                    end_col = col_idx + 1
                end_index = f"{line}.{end_col}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="invalid_trailing_symbol_after_value"
                )
                return
            if owner._is_missing_object_close():
                # Highlight the EOF insertion point (where the missing '}' belongs),
                # not the previous content line.
                start_index = owner.text.index("end-1c")
                end_index = owner.text.index("end")
                line = int(owner.text.index("end").split(".")[0])
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="missing_object_close_eof"
                )
                return
            wrong_object_line = owner._find_wrong_object_open_line(line)
            if wrong_object_line:
                line = wrong_object_line
                line_text = owner._line_text(line)
                col = line_text.find("[")
                if col < 0:
                    col = 0
                start_index = f"{line}.{col}"
                end_index = f"{line}.{col + 1}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="wrong_object_open_symbol"
                )
                return
            wrong_line = owner._find_wrong_list_open_line(line)
            if wrong_line:
                line = wrong_line
                line_text = owner._line_text(line)
                col_idx = line_text.find("[")
                if col_idx < 0:
                    col_idx = max(col - 1, 0)
                start_index = f"{line}.{col_idx}"
                end_index = f"{line}.{col_idx + 1}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="wrong_list_open_for_object"
                )
                return
            if owner._is_missing_list_close():
                comma_line = owner._find_comma_only_line_before(line)
                if comma_line:
                    line = comma_line
                    line_text = owner._line_text(line)
                    comma_col = line_text.find(",")
                    if comma_col < 0:
                        comma_col = 0
                    start_index = f"{line}.{comma_col}"
                    end_index = f"{line}.{comma_col + 1}"
                    apply_highlight_fn(owner, 
                        exc, line, start_index, end_index, note="missing_list_close_before_comma"
                    )
                    return
                # Insert missing ']' before the object-close line.
                line_text = owner._line_text(line).strip()
                if line_text.startswith("}"):
                    # Prefer a blank insertion line directly above '}' when available;
                    # otherwise highlight the start of the '}' line.
                    blank_line = line - 1 if line > 1 and not owner._line_text(line - 1).strip() else None
                    if blank_line:
                        line = blank_line
                    line = max(line, 1)
                    start_index = f"{line}.0"
                    end_index = start_index
                    apply_highlight_fn(owner, 
                        exc, line, start_index, end_index, note="missing_list_close_before_object_end"
                    )
                    return
                # If the insertion slot is a blank line right below the current value,
                # anchor there to keep the caret at the user's actual edit row.
                next_line = max(int(line) + 1, 1)
                try:
                    next_text = str(owner._line_text(next_line) or "")
                    after_next_text = str(owner._line_text(next_line + 1) or "")
                    current_line_text = str(owner._line_text(line) or "")
                except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                    next_text = ""
                    after_next_text = ""
                    current_line_text = ""
                try:
                    if (not next_text.strip()) and current_line_text.strip().startswith('"'):
                        line = next_line
                        start_index = f"{line}.0"
                        end_index = start_index
                        apply_highlight_fn(owner, 
                            exc, line, start_index, end_index, note="missing_list_close_before_object_end"
                        )
                        return
                except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                    pass
                if (not next_text.strip()) and after_next_text.strip().startswith("}"):
                    line = next_line
                    start_index = f"{line}.0"
                    end_index = start_index
                    apply_highlight_fn(owner, 
                        exc, line, start_index, end_index, note="missing_list_close_before_object_end"
                    )
                    return
                line = max(line, 1)
                line_end = owner.text.index(f"{line}.0 lineend")
                start_index = line_end
                end_index = line_end
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="missing_list_close_before_object_end"
                )
                return
            if owner._close_before_list(getattr(exc, "lineno", None)):
                blank_line = owner._find_blank_line_before(line)
                if blank_line:
                    line = blank_line
                start_index = f"{line}.0"
                end_index = owner.text.index(f"{line}.0 lineend +1c")
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="missing_object_close_before_list"
                )
                return
            if owner._is_missing_object_open_at(line):
                prev_line_num = owner._closest_non_empty_line_before(line)
                insert_line = line
                if prev_line_num:
                    candidate = prev_line_num + 1
                    if candidate <= line and not owner._line_text(candidate).strip():
                        insert_line = candidate
                line = insert_line
                line_text = owner._line_text(line)
                first_non_space = None
                if line_text:
                    for idx, ch in enumerate(line_text):
                        if not ch.isspace():
                            first_non_space = idx
                            break
                if first_non_space is None:
                    line_end = owner.text.index(f"{line}.0 lineend")
                    start_index = line_end
                    end_index = line_end
                else:
                    start_index = f"{line}.{first_non_space}"
                    if owner._line_has_missing_open_key_quote(line_text):
                        end_index = start_index
                    else:
                        end_index = f"{line}.{first_non_space + 1}"
                apply_highlight_fn(owner, exc, line, start_index, end_index)
                return
            if owner._is_missing_object_open(exc):
                line = max(line - 1, 1)
                line_end = owner.text.index(f"{line}.0 lineend")
                start_index = line_end
                end_index = line_end
            elif owner._is_missing_object_close():
                if owner._close_before_list(getattr(exc, "lineno", None)):
                    blank_line = owner._find_blank_line_before(line)
                    if blank_line:
                        line = blank_line
                    else:
                        line = max(line - 1, 1)
                    start_index = f"{line}.0"
                    end_index = owner.text.index(f"{line}.0 lineend +1c")
                else:
                    line, start_index = owner._missing_close_insertion_point("{", "}", exc)
                    line = max(line, 1)
                    end_index = start_index
            elif owner._is_missing_list_close():
                line, start_index = owner._missing_close_insertion_point("[", "]", exc)
                line = max(line, 1)
                end_index = start_index
            else:
                line = max(line - 1, 1)
                line_end = owner.text.index(f"{line}.0 lineend")
                start_index = line_end
                end_index = line_end
        elif msg == "Expecting ':' delimiter":
            missing_key_line, missing_open = owner._find_missing_container_open_after_key_line(line)
            if missing_key_line and missing_open in ("[", "{"):
                line = missing_key_line
                line_end = owner.text.index(f"{line}.0 lineend")
                start_index = line_end
                end_index = line_end
                missing_note = (
                    "missing_object_open_after_key"
                    if missing_open == "{"
                    else "missing_list_open_after_key"
                )
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note=missing_note
                )
                return
            start_index = f"{line}.{max(col - 1, 0)}"
            end_index = f"{line}.{col}"
        elif msg == "Expecting property name enclosed in double quotes":
            missing_key_line, missing_open = owner._find_missing_container_open_after_key_line(line)
            if missing_key_line and missing_open in ("[", "{"):
                line = missing_key_line
                line_end = owner.text.index(f"{line}.0 lineend")
                start_index = line_end
                end_index = line_end
                missing_note = (
                    "missing_object_open_after_key"
                    if missing_open == "{"
                    else "missing_list_open_after_key"
                )
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note=missing_note
                )
                return
            dup_line_no, dup_line_text = owner._find_nearby_duplicate_trailing_comma_line(line)
            if dup_line_text and dup_line_no:
                line = dup_line_no
                line_text = owner._line_text(line)
                comma_col = line_text.rfind(",")
                if comma_col < 0:
                    comma_col = max(col - 1, 0)
                start_index = f"{line}.{comma_col}"
                end_index = f"{line}.{comma_col + 1}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="duplicate_trailing_comma"
                )
                return
            invalid_tail_no, invalid_tail_text = owner._find_nearby_invalid_trailing_symbols_line(line)
            if invalid_tail_text and invalid_tail_no:
                line = invalid_tail_no
                line_text = owner._line_text(line)
                col_idx = owner._first_invalid_trailing_symbol_col(line_text, lineno=line)
                if col_idx is None:
                    col_idx = max(col - 1, 0)
                start_index = f"{line}.{col_idx}"
                end_col = len(line_text.rstrip())
                if end_col <= col_idx:
                    end_col = col_idx + 1
                end_index = f"{line}.{end_col}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="invalid_trailing_symbol_after_value"
                )
                return
            if owner._is_missing_object_close():
                comma_line = owner._find_comma_only_line_before(line)
                if comma_line:
                    line = comma_line
                    line_text = owner._line_text(line)
                    comma_col = line_text.find(",")
                    if comma_col < 0:
                        comma_col = 0
                    start_index = f"{line}.{comma_col}"
                    end_index = f"{line}.{comma_col + 1}"
                    apply_highlight_fn(owner, 
                        exc, line, start_index, end_index, note="missing_object_close_before_comma"
                    )
                    return
            line_text = owner._line_text(line).strip()
            if owner._is_missing_object_close() and line_text.startswith("{"):
                insert_line = line
                prev_non_empty = owner._closest_non_empty_line_before(line)
                if prev_non_empty:
                    prev_text = owner._line_text(prev_non_empty).strip()
                    if prev_text in ("},", "],"):
                        # Missing close often belongs before a sibling-separator close.
                        if prev_non_empty > 1 and not owner._line_text(prev_non_empty - 1).strip():
                            insert_line = prev_non_empty - 1
                        else:
                            insert_line = prev_non_empty
                    elif line > 1 and not owner._line_text(line - 1).strip():
                        insert_line = line - 1
                elif line > 1 and not owner._line_text(line - 1).strip():
                    insert_line = line - 1
                line = max(insert_line, 1)
                start_index = owner.text.index(f"{line}.0 lineend")
                end_index = start_index
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="missing_object_close_before_next_object"
                )
                return
            comma_line = owner._find_comma_only_line_before(line)
            if comma_line:
                line = comma_line
                line_text = owner._line_text(line)
                comma_col = line_text.find(",")
                if comma_col < 0:
                    comma_col = 0
                start_index = f"{line}.{comma_col}"
                end_index = f"{line}.{comma_col + 1}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="missing_object_close_before_comma"
                )
                return
            line_text = owner._line_text(line)
            if line_text.strip().startswith("{"):
                key_line = owner._missing_list_open_key_line(line)
                if key_line:
                    line = key_line
                    line_end = owner.text.index(f"{line}.0 lineend")
                    start_index = line_end
                    end_index = line_end
                else:
                    first_non_space = 0
                    if line_text:
                        for idx, ch in enumerate(line_text):
                            if not ch.isspace():
                                first_non_space = idx
                                break
                    start_index = f"{line}.{first_non_space}"
                    if line_text and first_non_space < len(line_text):
                        end_index = f"{line}.{first_non_space + 1}"
                    else:
                        end_index = owner.text.index(f"{line}.0 lineend")
            else:
                first_non_space = 0
                if line_text:
                    for idx, ch in enumerate(line_text):
                        if not ch.isspace():
                            first_non_space = idx
                            break
                start_index = f"{line}.{first_non_space}"
                missing_open_key_quote = owner._line_has_missing_open_key_quote(line_text)
                if missing_open_key_quote:
                    # Place insertion cursor before the property name so the
                    # missing opening quote can be typed at the fix point.
                    end_index = start_index
                elif line_text and first_non_space < len(line_text):
                    end_index = f"{line}.{first_non_space + 1}"
                else:
                    end_index = owner.text.index(f"{line}.0 lineend")
        elif msg in ("Expecting ']'", "Expecting '}'"):
            if exc.msg == "Expecting ']'":
                line, start_index = owner._missing_close_insertion_point("[", "]", exc)
            else:
                line, start_index = owner._missing_close_insertion_point("{", "}", exc)
            line = max(line, 1)
            end_index = start_index
        elif msg == "Invalid control character":
            start_index = f"{line}.{max(col - 1, 0)}"
            end_index = f"{line}.{col}"
        elif msg == "Expecting value":
            line_text = owner._line_text(line)
            if owner._is_key_colon_comma_line(line_text):
                comma_col = line_text.find(",")
                if comma_col < 0:
                    comma_col = max(col - 1, 0)
                start_index = f"{line}.{comma_col}"
                end_index = f"{line}.{comma_col + 1}"
                apply_highlight_fn(owner, 
                    exc, line, start_index, end_index, note="missing_list_open_typed_comma"
                )
                return
            if owner._is_missing_list_open_at_start(exc):
                line = 1
                start_index = f"{line}.0"
                end_index = f"{line}.0"
            elif owner._is_missing_object_open(exc):
                line = max(line - 1, 1)
                line_end = owner.text.index(f"{line}.0 lineend")
                start_index = line_end
                end_index = line_end
            elif owner._is_missing_list_open(exc):
                line = max(line - 1, 1)
                line_end = owner.text.index(f"{line}.0 lineend")
                start_index = line_end
                end_index = line_end
            elif owner._is_missing_list_close() or owner._is_missing_object_close():
                if owner._is_missing_object_close():
                    line, start_index = owner._missing_close_insertion_point("{", "}", exc)
                else:
                    line, start_index = owner._missing_close_insertion_point("[", "]", exc)
                line = max(line, 1)
                end_index = start_index
            else:
                start_index = f"{line}.{max(col - 1, 0)}"
                end_index = f"{line}.{col}"
        elif msg in ("Unexpected ']'", "Unexpected '}'", "Unterminated string"):
            start_index = f"{line}.{max(col - 1, 0)}"
            end_index = f"{line}.{col}"
        elif msg == "Extra data":
            if owner._missing_list_open_top_level():
                line = 1
                start_index = f"{line}.0"
                end_index = f"{line}.0"
            else:
                next_line = owner._next_non_empty_line(line)
                if next_line:
                    line = next_line
                line_end = owner.text.index(f"{line}.0 lineend")
                start_index = f"{line}.0"
                end_index = line_end
        else:
            line = max(line - 1, 1)
            line_end = owner.text.index(f"{line}.0 lineend")
            start_index = line_end
            end_index = line_end
        apply_highlight_fn(owner, exc, line, start_index, end_index)
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError) as highlight_exc:
        try:
            log_error_fn(owner, exc, line or 1, note=f"highlight_failed: {highlight_exc}")
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            pass
        return
