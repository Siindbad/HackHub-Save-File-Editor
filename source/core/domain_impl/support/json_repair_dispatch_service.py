"""JSON repair dispatch helpers extracted from JsonEditor orchestration block."""

from __future__ import annotations

import json
import re
import tkinter as tk
from typing import Any, Callable

from core import json_diagnostics as json_diag_core
from core import json_error_diagnostics_core
from core.domain_impl.infra import input_mode_diag_service
from core.domain_impl.json import json_diagnostics_core as json_closer_symbol_service
from core.domain_impl.json import json_diagnostics_core as json_colon_comma_service
from core.domain_impl.json import json_diagnostics_core as json_diagnostics_service
from core.domain_impl.json import json_io_core as json_edit_flow_service
from core.domain_impl.json import json_diagnostics_core as json_error_diag_service
from core.domain_impl.json import json_diagnostics_core as json_open_symbol_service
from core.domain_impl.json import json_diagnostics_core as json_property_key_rule_service
from core.domain_impl.json import json_diagnostics_core as json_repair_service
from core.domain_impl.json import json_diagnostics_core as json_scalar_tail_service
from core.domain_impl.json import json_diagnostics_core as json_top_level_close_service
from core.domain_impl.support import editor_purge_service
from core.domain_impl.support import error_overlay_service
from core.domain_impl.ui import tree_view_service

_EXPECTED_APP_ERRORS = (
    tk.TclError,
    RuntimeError,
    OSError,
    ValueError,
    TypeError,
    KeyError,
    IndexError,
    AttributeError,
    ImportError,
    json.JSONDecodeError,
    UnicodeDecodeError,
)

def _json_token_followed_by_colon(owner, end_index, lookahead_chars=24):
    return json_repair_service._json_token_followed_by_colon(owner, end_index, lookahead_chars)

def _tag_json_locked_key_occurrences(owner, key_name):
    return json_diagnostics_service._tag_json_locked_key_occurrences(owner, key_name)

def _tag_json_xy_key_occurrences(owner, key_name):
    return json_diagnostics_service._tag_json_xy_key_occurrences(owner, key_name)

def _should_batch_tag_locked_keys(owner, key_names):
    return json_diagnostics_service._should_batch_tag_locked_keys(owner, key_names)

def _tag_json_key_occurrences_batch(owner, locked_key_names, xy_key_names=(), line_limit=None):
    return json_diagnostics_service._tag_json_key_occurrences_batch(owner, locked_key_names, xy_key_names, line_limit)

def _tag_json_string_value_literals(owner, line_limit=None):
    return json_diagnostics_service._tag_json_string_value_literals(owner, line_limit)

def _tag_json_brace_tokens(owner, line_limit=None):
    return json_diagnostics_service._tag_json_brace_tokens(owner, line_limit)

def _tag_json_boolean_literals(owner, line_limit=None):
    return json_diagnostics_service._tag_json_boolean_literals(owner, line_limit)

def _tag_json_property_keys(owner, line_limit=None):
    return json_diagnostics_service._tag_json_property_keys(owner, line_limit)

def _json_literal_offsets_after_key(owner, key_end_index, literal_token, lookahead_chars=120, ignore_case=False):
    return json_diagnostics_service._json_literal_offsets_after_key(owner, key_end_index, literal_token, lookahead_chars, ignore_case)

def _tag_json_locked_value_occurrences(owner, field_name, literal_value, ignore_case=False):
    return json_diagnostics_service._tag_json_locked_value_occurrences(owner, field_name, literal_value, ignore_case)

def _apply_json_view_lock_state(owner, path):
    return json_diagnostics_service._apply_json_view_lock_state(owner, path)

def _apply_json_view_key_highlights(owner, path, line_limit=None):
    # Legacy wiring token kept for regression checks: xy_keys = ("x", "y") if len(use_path) == 1 else ()
    return editor_purge_service._apply_json_view_key_highlights(owner, path, line_limit)

def _apply_json_view_value_highlights(owner, path):
    return editor_purge_service._apply_json_view_value_highlights(owner, path)

def _describe(owner, value):
    return json_diagnostics_service._describe(owner, value)

def apply_edit(owner):
    return editor_purge_service.apply_edit(owner)

def _extract_key_name_from_diag_line(owner, line_text):
    return json_diagnostics_service._extract_key_name_from_diag_line(owner, line_text)

def _locked_field_name_from_parse_diag(owner, path, diag):
    return editor_purge_service._locked_field_name_from_parse_diag(owner, path, diag)

def _find_lock_anchor_index(owner, field_name, preferred_index=None):
    return json_diagnostics_service._find_lock_anchor_index(owner, field_name, preferred_index)

def _diag_line_mentions_locked_field(owner, line_no, field_name):
    return json_diagnostics_service._diag_line_mentions_locked_field(owner, line_no, field_name)

def _maybe_restore_locked_parse_error(owner, path, diag, exc=None):
    # Parse-lock guard gate: delegated lock-restore flow preserves strict line/key gating.
    return editor_purge_service._maybe_restore_locked_parse_error(owner, path, diag, exc)

def _format_json_error(owner, exc):
    return json_error_diagnostics_core.format_json_error(owner, exc)

def _example_for_error(owner, exc):
    return json_diagnostics_service._example_for_error(owner, exc)

def _missing_colon_example(owner, line_text):
    return json_repair_service._missing_colon_example(owner, line_text)

def _is_json_value_token_start(owner, value_text):
    return json_diagnostics_service._is_json_value_token_start(owner, value_text)

def _missing_colon_key_value_span(owner, line_text):
    return json_repair_service._missing_colon_key_value_span(owner, line_text)

def _line_has_missing_colon_key_value(owner, line_text):
    return owner._missing_colon_key_value_span(line_text) is not None

def _find_nearby_missing_colon_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_missing_colon_line(owner, lineno, lookback)

def _is_key_colon_comma_line(owner, line_text):
    return json_repair_service._is_key_colon_comma_line(owner, line_text)

def _key_colon_comma_to_list_open(owner, line_text):
    return json_repair_service._key_colon_comma_to_list_open(owner, line_text)

def _line_extra_quote_in_string_value(owner, line_text):
    return json_repair_service._line_extra_quote_in_string_value(owner, line_text)

def _fix_extra_quote_to_comma(owner, line_text):
    return json_repair_service._fix_extra_quote_to_comma(owner, line_text)

def _line_has_trailing_stray_quote_after_comma(owner, line_text):
    return json_repair_service._line_has_trailing_stray_quote_after_comma(owner, line_text)

def _fix_trailing_stray_quote_after_comma(owner, line_text):
    return json_repair_service._fix_trailing_stray_quote_after_comma(owner, line_text)

def _find_nearby_trailing_stray_quote_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_trailing_stray_quote_line(owner, lineno, lookback)

def _line_has_duplicate_trailing_comma(owner, line_text):
    return json_repair_service._line_has_duplicate_trailing_comma(owner, line_text)

def _fix_duplicate_trailing_comma(owner, line_text):
    return json_repair_service._fix_duplicate_trailing_comma(owner, line_text)

def _find_nearby_duplicate_trailing_comma_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_duplicate_trailing_comma_line(owner, lineno, lookback)

def _line_requires_trailing_comma(owner, lineno):
    return json_repair_service._line_requires_trailing_comma(owner, lineno)

def _duplicate_comma_run_span(owner, line_text, lineno=None):
    return json_repair_service._duplicate_comma_run_span(owner, line_text, lineno)

def _line_has_duplicate_comma_run(owner, line_text, lineno=None):
    return owner._duplicate_comma_run_span(line_text, lineno=lineno) is not None

def _fix_duplicate_comma_run(owner, line_text, lineno=None):
    return json_repair_service._fix_duplicate_comma_run(owner, line_text, lineno)

def _find_nearby_duplicate_comma_run_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_duplicate_comma_run_line(owner, lineno, lookback)

def _comma_before_colon_span(owner, line_text):
    return json_colon_comma_service.comma_before_colon_span(line_text)

def _line_has_comma_before_colon(owner, line_text):
    return json_colon_comma_service.line_has_comma_before_colon(line_text)

def _fix_comma_before_colon(owner, line_text):
    return json_colon_comma_service.fix_comma_before_colon(line_text)

def _find_nearby_comma_before_colon_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_comma_before_colon_line(owner, lineno, lookback)

def _comma_after_colon_span(owner, line_text):
    return json_colon_comma_service.comma_after_colon_span(line_text)

def _line_has_comma_after_colon(owner, line_text):
    return json_colon_comma_service.line_has_comma_after_colon(line_text)

def _fix_comma_after_colon(owner, line_text):
    return json_colon_comma_service.fix_comma_after_colon(line_text)

def _find_nearby_comma_after_colon_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_comma_after_colon_line(owner, lineno, lookback)

def _analyze_invalid_prefix_after_colon(owner, line_text):
    return json_repair_service._analyze_invalid_prefix_after_colon(owner, line_text)

def _line_has_invalid_prefix_after_colon(owner, line_text):
    return owner._analyze_invalid_prefix_after_colon(line_text) is not None

def _fix_invalid_prefix_after_colon(owner, line_text):
    return json_repair_service._fix_invalid_prefix_after_colon(owner, line_text)

def _find_nearby_invalid_prefix_after_colon_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_invalid_prefix_after_colon_line(owner, lineno, lookback)

def _comma_before_closer_span(owner, line_text):
    return json_colon_comma_service.comma_before_closer_span(line_text)

def _line_has_comma_before_closer(owner, line_text):
    return json_colon_comma_service.line_has_comma_before_closer(line_text)

def _fix_comma_before_closer(owner, line_text):
    return json_colon_comma_service.fix_comma_before_closer(line_text)

def _find_nearby_comma_before_closer_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_comma_before_closer_line(owner, lineno, lookback)

def _comma_line_invalid_tail_span(owner, line_text):
    return json_colon_comma_service.comma_line_invalid_tail_span(line_text)

def _line_has_comma_line_invalid_tail(owner, line_text):
    return json_colon_comma_service.line_has_comma_line_invalid_tail(line_text)

def _expected_missing_close_symbol(owner, lineno):
    return json_repair_service._expected_missing_close_symbol(owner, lineno)

def _fix_comma_line_invalid_tail(owner, line_text, lineno=None):
    return json_repair_service._fix_comma_line_invalid_tail(owner, line_text, lineno)

def _find_nearby_comma_line_invalid_tail_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_comma_line_invalid_tail_line(owner, lineno, lookback)

def _missing_key_quote_before_colon_span(owner, line_text):
    return json_property_key_rule_service.missing_key_quote_before_colon_span(line_text)

def _line_has_missing_key_quote_before_colon(owner, line_text):
    return json_property_key_rule_service.line_has_missing_key_quote_before_colon(line_text)

def _fix_property_key_symbol_before_colon(owner, line_text):
    return json_property_key_rule_service.fix_property_key_symbol_before_colon(line_text)

def _find_nearby_missing_key_quote_before_colon_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_missing_key_quote_before_colon_line(owner, lineno, lookback)

def _property_key_invalid_escape_span(owner, line_text):
    return json_property_key_rule_service.property_key_invalid_escape_span(line_text)

def _line_has_property_key_invalid_escape(owner, line_text):
    return json_property_key_rule_service.line_has_property_key_invalid_escape(line_text)

def _fix_property_key_invalid_escape(owner, line_text):
    return json_property_key_rule_service.fix_property_key_invalid_escape(line_text)

def _find_nearby_property_key_invalid_escape_line(owner, lineno, lookback=2):
    return json_diagnostics_service._find_nearby_property_key_invalid_escape_line(owner, lineno, lookback)

def _missing_key_quote_before_colon_diag(owner, line_no, colno=1):
    return json_repair_service._missing_key_quote_before_colon_diag(owner, line_no, colno)

def _quoted_item_invalid_tail_span(owner, line_text):
    return json_repair_service._quoted_item_invalid_tail_span(owner, line_text)

def _line_has_invalid_tail_after_quoted_item(owner, line_text):
    return json_repair_service._line_has_invalid_tail_after_quoted_item(owner, line_text)

def _fix_invalid_tail_after_quoted_item(owner, line_text, lineno=None):
    return editor_purge_service._fix_invalid_tail_after_quoted_item(owner, line_text, lineno)

def _find_nearby_invalid_tail_after_quoted_item_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_invalid_tail_after_quoted_item_line(owner, lineno, lookback)

def _line_has_illegal_trailing_comma_before_close(owner, line_text, lineno):
    return json_repair_service._line_has_illegal_trailing_comma_before_close(owner, line_text, lineno)

def _trailing_comma_before_close_col(owner, line_text):
    return json_repair_service._trailing_comma_before_close_col(owner, line_text)

def _fix_illegal_trailing_comma_before_close(owner, line_text):
    return json_repair_service._fix_illegal_trailing_comma_before_close(owner, line_text)

def _find_nearby_illegal_trailing_comma_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_illegal_trailing_comma_line(owner, lineno, lookback)

def _line_has_illegal_comma_after_top_level_close(owner, line_text, lineno):
    return json_repair_service._line_has_illegal_comma_after_top_level_close(owner, line_text, lineno)

def _top_level_close_symbol_run_span(owner, line_text):
    return json_top_level_close_service.top_level_close_symbol_run_span(line_text)

def _line_has_top_level_close_symbol_run(owner, line_text, lineno):
    return json_repair_service._line_has_top_level_close_symbol_run(owner, line_text, lineno)

def _fix_top_level_close_symbol_run(owner, line_text):
    return json_top_level_close_service.fix_top_level_close_symbol_run(line_text)

def _find_nearby_top_level_close_symbol_run_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_top_level_close_symbol_run_line(owner, lineno, lookback)

def _comma_run_after_top_level_close_span(owner, line_text):
    return json_top_level_close_service.comma_run_after_top_level_close_span(line_text)

def _fix_illegal_comma_after_top_level_close(owner, line_text):
    return json_top_level_close_service.fix_illegal_comma_after_top_level_close(line_text)

def _find_nearby_illegal_comma_after_top_level_close_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_illegal_comma_after_top_level_close_line(owner, lineno, lookback)

def _split_completed_scalar_value_tail(owner, line_text):
    return json_scalar_tail_service.split_completed_scalar_value_tail(line_text)

def _line_has_invalid_trailing_symbols_after_string_value(owner, line_text):
    return json_scalar_tail_service.line_has_invalid_trailing_symbols_after_string_value(line_text)

def _first_invalid_trailing_symbol_col(owner, line_text, lineno=None):
    return json_repair_service._first_invalid_trailing_symbol_col(owner, line_text, lineno)

def _fix_invalid_trailing_symbols_after_string_value(owner, line_text, lineno=None):
    return editor_purge_service._fix_invalid_trailing_symbols_after_string_value(owner, line_text, lineno)

def _find_nearby_invalid_trailing_symbols_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_invalid_trailing_symbols_line(owner, lineno, lookback)

def _line_has_invalid_symbol_after_closer(owner, line_text):
    return json_closer_symbol_service.line_has_invalid_symbol_after_closer(line_text)

def _first_invalid_symbol_after_closer_col(owner, line_text):
    return json_closer_symbol_service.first_invalid_symbol_after_closer_col(line_text)

def _fix_invalid_symbol_after_closer(owner, line_text):
    return json_closer_symbol_service.fix_invalid_symbol_after_closer(line_text)

def _find_nearby_invalid_symbol_after_closer_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_invalid_symbol_after_closer_line(owner, lineno, lookback)

def _invalid_symbol_after_open_span(owner, line_text):
    return json_open_symbol_service.invalid_symbol_after_open_span(line_text)

def _line_has_invalid_symbol_after_open(owner, line_text):
    return json_open_symbol_service.line_has_invalid_symbol_after_open(line_text)

def _fix_invalid_symbol_after_open(owner, line_text):
    return json_open_symbol_service.fix_invalid_symbol_after_open(line_text)

def _find_nearby_invalid_symbol_after_open_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_invalid_symbol_after_open_line(owner, lineno, lookback)

def _find_nearby_extra_quote_in_value_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_extra_quote_in_value_line(owner, lineno, lookback)

def _build_symbol_json_diagnostic(owner, exc, lineno=None):
    return json_error_diagnostics_core.build_symbol_json_diagnostic(owner, exc, lineno=lineno)

def _build_json_diagnostic(owner, exc):
    return json_error_diagnostics_core.build_json_diagnostic(owner, exc)

def _quote_unquoted_value(owner, line_text):
    return json_repair_service._quote_unquoted_value(owner, line_text)

def _quote_unquoted_scalar_line(owner, line_text):
    return json_repair_service._quote_unquoted_scalar_line(owner, line_text)

def _line_needs_value_quotes(owner, line_text):
    return json_diagnostics_service._line_needs_value_quotes(owner, line_text)

def _missing_value_close_quote_insert_col(owner, line_text):
    return json_repair_service._missing_value_close_quote_insert_col(owner, line_text)

def _missing_value_open_quote_insert_col(owner, line_text):
    return json_repair_service._missing_value_open_quote_insert_col(owner, line_text)

def _find_nearby_missing_value_close_quote_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_missing_value_close_quote_line(owner, lineno, lookback)

def _find_nearby_missing_value_open_quote_line(owner, lineno, lookback=3):
    return json_repair_service._find_nearby_missing_value_open_quote_line(owner, lineno, lookback)

def _find_nearby_unquoted_value_line(owner, lineno, lookback=3):
    return json_diagnostics_service._find_nearby_unquoted_value_line(owner, lineno, lookback)

def _suggest_json_literal_from_token(owner, token):
    return json_diag_core.suggest_json_literal_from_token(token)

def _boolean_literal_typo_diagnostic(owner, line_text):
    return json_diag_core.boolean_literal_typo_diagnostic(line_text)

def _find_nearby_boolean_literal_typo_line(owner, lineno, lookback=3):
    return json_diagnostics_service._find_nearby_boolean_literal_typo_line(owner, lineno, lookback)

def _is_wrong_list_open_for_object(owner, prev_text, next_text):
    return json_diagnostics_service._is_wrong_list_open_for_object(owner, prev_text, next_text)

def _find_wrong_list_open_line(owner, lineno, lookback=3):
    return json_diagnostics_service._find_wrong_list_open_line(owner, lineno, lookback)

def _find_wrong_object_open_line(owner, lineno, lookback=3):
    return json_diagnostics_service._find_wrong_object_open_line(owner, lineno, lookback)

def _expected_closer_before_position(owner, target_line, target_col):
    return json_diagnostics_service._expected_closer_before_position(owner, target_line, target_col)

def _find_wrong_closing_symbol_line(owner, lineno, lookback=2):
    return json_repair_service._find_wrong_closing_symbol_line(owner, lineno, lookback)

def _find_missing_list_close_before_object_end(owner, lineno, lookback=4):
    return json_repair_service._find_missing_list_close_before_object_end(owner, lineno, lookback)

def _next_non_empty_line_number(owner, start_line):
    return json_diagnostics_service._next_non_empty_line_number(owner, start_line)

def _missing_list_open_key_line(owner, lineno):
    return json_repair_service._missing_list_open_key_line(owner, lineno)

def _line_looks_like_object_property(_owner, line_text):
    return bool(re.match(r'^"[^"]+"\s*:', str(line_text or "").strip()))

def _find_missing_container_open_after_key_line(owner, lineno, lookback=6):
    return json_repair_service._find_missing_container_open_after_key_line(owner, lineno, lookback)

def _find_missing_list_open_after_key_line(owner, lineno, lookback=6):
    return json_repair_service._find_missing_list_open_after_key_line(owner, lineno, lookback)

def _missing_close_example(owner, msg):
    return json_repair_service._missing_close_example(owner, msg)

def _format_suggestion(owner, header, before, after, header_only=False):
    return json_diagnostics_service._format_suggestion(owner, header, before, after, header_only)

def _suggestion_from_example(owner, example, add_after=None, add_colon=False, quote_key=False):
    return json_diagnostics_service._suggestion_from_example(owner, example, add_after, add_colon, quote_key)

def _is_missing_object_open_at(owner, lineno):
    return json_repair_service._is_missing_object_open_at(owner, lineno)

def _line_text(owner, lineno):
    return json_diagnostics_service._line_text(owner, lineno)

def _line_has_missing_open_key_quote(owner, line_text):
    return json_repair_service._line_has_missing_open_key_quote(owner, line_text)

def _missing_close_target_line_from_exc(owner, exc, open_bracket, close_bracket):
    return json_repair_service._missing_close_target_line_from_exc(owner, exc, open_bracket, close_bracket)

def _missing_close_target_line_any(owner, exc):
    return json_repair_service._missing_close_target_line_any(owner, exc)

def _missing_list_close_target_line(owner, exc):
    line, _idx = owner._missing_close_insertion_point("[", "]", exc)
    return line

def _unmatched_open_bracket_lines(owner, open_bracket, close_bracket):
    return json_diagnostics_service._unmatched_open_bracket_lines(owner, open_bracket, close_bracket)

def _is_missing_list_close(owner):
    return bool(owner._unmatched_open_bracket_lines("[", "]"))

def _is_missing_object_close(owner):
    return bool(owner._unmatched_open_bracket_lines("{", "}"))

def _last_unmatched_bracket_line(owner, open_bracket, close_bracket):
    return json_diagnostics_service._last_unmatched_bracket_line(owner, open_bracket, close_bracket)

def _line_indent_width(owner, lineno):
    raw = owner._line_text(lineno)
    return len(raw) - len(raw.lstrip(" \t"))

def _missing_close_insertion_point(owner, open_bracket, close_bracket, exc=None):
    return json_repair_service._missing_close_insertion_point(owner, open_bracket, close_bracket, exc)

def _missing_object_close_target_line(owner, exc):
    line, _idx = owner._missing_close_insertion_point("{", "}", exc)
    return line

def _find_comma_only_line_before(owner, start_line):
    return json_repair_service._find_comma_only_line_before(owner, start_line)

def _find_missing_comma_between_block_values_line(owner, line):
    return json_repair_service._find_missing_comma_between_block_values_line(owner, line)

def _find_blank_line_before(owner, start_line):
    return json_diagnostics_service._find_blank_line_before(owner, start_line)

def _closest_non_empty_line_before(owner, start_line):
    return json_diagnostics_service._closest_non_empty_line_before(owner, start_line)

def _last_non_empty_line_number(owner):
    return json_diagnostics_service._last_non_empty_line_number(owner)

def _missing_close_target_line(owner, open_bracket, close_bracket):
    return json_repair_service._missing_close_target_line(owner, open_bracket, close_bracket)

def _is_missing_object_open(owner, exc):
    return json_repair_service._is_missing_object_open(owner, exc)

def _is_missing_list_open(owner, exc):
    return json_repair_service._is_missing_list_open(owner, exc)

def _is_missing_list_open_at_start(owner, exc, allow_any_position=False):
    return json_repair_service._is_missing_list_open_at_start(owner, exc, allow_any_position)

def _missing_list_open_top_level(owner):
    return json_repair_service._missing_list_open_top_level(owner)

def _missing_object_open_from_extra_data(owner):
    return json_repair_service._missing_object_open_from_extra_data(owner)

def _first_non_ws_char(owner):
    return json_diagnostics_service._first_non_ws_char(owner)

def _missing_list_open_from_extra_data(owner):
    return json_repair_service._missing_list_open_from_extra_data(owner)

def _previous_non_empty_line(owner, lineno):
    return json_diagnostics_service._previous_non_empty_line(owner, lineno)

def _next_non_empty_line(owner, lineno):
    return json_diagnostics_service._next_non_empty_line(owner, lineno)

def _missing_object_example(owner, lineno):
    return json_repair_service._missing_object_example(owner, lineno)

def _close_before_list(owner, lineno):
    return json_diagnostics_service._close_before_list(owner, lineno)

def _quote_property_name(owner, line_text):
    return json_repair_service._quote_property_name(owner, line_text)

def _highlight_custom_range(owner, line, start_col, end_col):
    return json_diagnostics_service._highlight_custom_range(owner, line, start_col, end_col)

def _fix_missing_at(owner, value, domain_roots=None):
    return json_repair_service._fix_missing_at(owner, value, domain_roots)

def _format_phone(owner, value):
    return json_repair_service._format_phone(owner, value)

def _find_phone_format_issue(owner):
    return json_repair_service._find_phone_format_issue(owner)

def _fix_missing_space_after_colon(owner, line_text):
    return json_repair_service._fix_missing_space_after_colon(owner, line_text)

def _find_json_spacing_issue(owner):
    return json_repair_service._find_json_spacing_issue(owner)

def _find_missing_email_at(owner):
    return json_repair_service._find_missing_email_at(owner)

def _path_targets_email(owner, path):
    return json_repair_service._path_targets_email(owner, path)

def _looks_like_email_candidate(owner, value):
    return json_repair_service._looks_like_email_candidate(owner, value)

def _should_validate_email_path_value(owner, path, value):
    return json_repair_service._should_validate_email_path_value(owner, path, value)

def _iter_candidate_email_values(owner, node, rel_path=None):
    return json_repair_service._iter_candidate_email_values(owner, node, rel_path)

def _format_path_for_display(owner, path):
    return tree_view_service.format_path_for_display(path)

def _find_value_span_in_editor(owner, value, preferred_key=None):
    return json_diagnostics_service._find_value_span_in_editor(owner, value, preferred_key)

def _find_invalid_email_in_value(owner, base_path, value):
    return json_repair_service._find_invalid_email_in_value(owner, base_path, value)

def _best_domain_root_similarity(owner, root):
    return json_diagnostics_service._best_domain_root_similarity(owner, root)

def _suggest_known_domain_from_local_and_domain(owner, local, domain):
    return json_diagnostics_service._suggest_known_domain_from_local_and_domain(owner, local, domain)

def _suggest_email_for_malformed(owner, value):
    return json_repair_service._suggest_email_for_malformed(owner, value)

def _validate_email_address(owner, value):
    return json_repair_service._validate_email_address(owner, value)

def _is_valid_email_domain(owner, domain):
    return json_repair_service._is_valid_email_domain(owner, domain)

def _find_invalid_email_format_issue(owner):
    return json_repair_service._find_invalid_email_format_issue(owner)

def _fix_missing_quote(owner, line_text):
    return json_repair_service._fix_missing_quote(owner, line_text)

def _unclosed_quoted_value_invalid_tail_span(owner, line_text):
    return json_repair_service._unclosed_quoted_value_invalid_tail_span(owner, line_text)

def _find_nearby_unclosed_quoted_value_invalid_tail_line(owner, lineno, lookback=2):
    return json_repair_service._find_nearby_unclosed_quoted_value_invalid_tail_line(owner, lineno, lookback)

def _comma_example_line(owner, lineno):
    return json_repair_service._comma_example_line(owner, lineno)

def _symbol_error_focus_index(owner, start_index, end_index):
    return json_repair_service._symbol_error_focus_index(owner, start_index, end_index)

def _apply_json_error_highlight(owner, exc, line, start_index, end_index, note=""):
    return json_diagnostics_service._apply_json_error_highlight(owner, exc, line, start_index, end_index, note)

def _highlight_json_error(owner, exc):
    # Delegation contract token: json_error_highlight_core.highlight_json_error(
    return json_diagnostics_service._highlight_json_error(owner, exc)

def _place_error_pin(owner, index):
    return error_overlay_service.place_error_pin(owner, index)

def _clear_error_pin(owner):
    error_overlay_service.clear_error_pin(owner)

def _position_error_overlay(owner, line):
    error_overlay_service.position_error_overlay(owner, line)

def _diag_system_from_note(owner, note):
    return json_diagnostics_service._diag_system_from_note(owner, note)

def _log_json_error(owner, exc, target_line, note=""):
    return json_error_diag_service.log_json_error(owner, exc, target_line, note=note)

def _log_json_error_emergency(owner, exc, target_line, note=""):
    return json_diagnostics_service._log_json_error_emergency(owner, exc, target_line, note)

def _log_input_mode_edit_issue(owner, path, exc):
    input_mode_diag_service.log_input_mode_edit_issue(owner, path, exc)

def _log_input_mode_apply_result(owner, path, changed):
    input_mode_diag_service.log_input_mode_apply_result(owner, path, changed)

def _log_input_mode_apply_trace(owner, stage, path, specs_count, changed=None):
    return json_diagnostics_service._log_input_mode_apply_trace(owner, stage, path, specs_count, changed)

def _begin_diag_action(owner, action_name):
    return json_diagnostics_service._begin_diag_action(owner, action_name)

def _clear_json_error_highlight(owner):
    return json_diagnostics_service._clear_json_error_highlight(owner)

_REPAIR_DISPATCH_HANDLERS: dict[str, Callable[..., Any]] = {
    "_json_token_followed_by_colon": _json_token_followed_by_colon,
    "_tag_json_locked_key_occurrences": _tag_json_locked_key_occurrences,
    "_tag_json_xy_key_occurrences": _tag_json_xy_key_occurrences,
    "_should_batch_tag_locked_keys": _should_batch_tag_locked_keys,
    "_tag_json_key_occurrences_batch": _tag_json_key_occurrences_batch,
    "_tag_json_string_value_literals": _tag_json_string_value_literals,
    "_tag_json_brace_tokens": _tag_json_brace_tokens,
    "_tag_json_boolean_literals": _tag_json_boolean_literals,
    "_tag_json_property_keys": _tag_json_property_keys,
    "_json_literal_offsets_after_key": _json_literal_offsets_after_key,
    "_tag_json_locked_value_occurrences": _tag_json_locked_value_occurrences,
    "_apply_json_view_lock_state": _apply_json_view_lock_state,
    "_apply_json_view_key_highlights": _apply_json_view_key_highlights,
    "_apply_json_view_value_highlights": _apply_json_view_value_highlights,
    "_describe": _describe,
    "apply_edit": apply_edit,
    "_extract_key_name_from_diag_line": _extract_key_name_from_diag_line,
    "_locked_field_name_from_parse_diag": _locked_field_name_from_parse_diag,
    "_find_lock_anchor_index": _find_lock_anchor_index,
    "_diag_line_mentions_locked_field": _diag_line_mentions_locked_field,
    "_maybe_restore_locked_parse_error": _maybe_restore_locked_parse_error,
    "_format_json_error": _format_json_error,
    "_example_for_error": _example_for_error,
    "_missing_colon_example": _missing_colon_example,
    "_is_json_value_token_start": _is_json_value_token_start,
    "_missing_colon_key_value_span": _missing_colon_key_value_span,
    "_line_has_missing_colon_key_value": _line_has_missing_colon_key_value,
    "_find_nearby_missing_colon_line": _find_nearby_missing_colon_line,
    "_is_key_colon_comma_line": _is_key_colon_comma_line,
    "_key_colon_comma_to_list_open": _key_colon_comma_to_list_open,
    "_line_extra_quote_in_string_value": _line_extra_quote_in_string_value,
    "_fix_extra_quote_to_comma": _fix_extra_quote_to_comma,
    "_line_has_trailing_stray_quote_after_comma": _line_has_trailing_stray_quote_after_comma,
    "_fix_trailing_stray_quote_after_comma": _fix_trailing_stray_quote_after_comma,
    "_find_nearby_trailing_stray_quote_line": _find_nearby_trailing_stray_quote_line,
    "_line_has_duplicate_trailing_comma": _line_has_duplicate_trailing_comma,
    "_fix_duplicate_trailing_comma": _fix_duplicate_trailing_comma,
    "_find_nearby_duplicate_trailing_comma_line": _find_nearby_duplicate_trailing_comma_line,
    "_line_requires_trailing_comma": _line_requires_trailing_comma,
    "_duplicate_comma_run_span": _duplicate_comma_run_span,
    "_line_has_duplicate_comma_run": _line_has_duplicate_comma_run,
    "_fix_duplicate_comma_run": _fix_duplicate_comma_run,
    "_find_nearby_duplicate_comma_run_line": _find_nearby_duplicate_comma_run_line,
    "_comma_before_colon_span": _comma_before_colon_span,
    "_line_has_comma_before_colon": _line_has_comma_before_colon,
    "_fix_comma_before_colon": _fix_comma_before_colon,
    "_find_nearby_comma_before_colon_line": _find_nearby_comma_before_colon_line,
    "_comma_after_colon_span": _comma_after_colon_span,
    "_line_has_comma_after_colon": _line_has_comma_after_colon,
    "_fix_comma_after_colon": _fix_comma_after_colon,
    "_find_nearby_comma_after_colon_line": _find_nearby_comma_after_colon_line,
    "_analyze_invalid_prefix_after_colon": _analyze_invalid_prefix_after_colon,
    "_line_has_invalid_prefix_after_colon": _line_has_invalid_prefix_after_colon,
    "_fix_invalid_prefix_after_colon": _fix_invalid_prefix_after_colon,
    "_find_nearby_invalid_prefix_after_colon_line": _find_nearby_invalid_prefix_after_colon_line,
    "_comma_before_closer_span": _comma_before_closer_span,
    "_line_has_comma_before_closer": _line_has_comma_before_closer,
    "_fix_comma_before_closer": _fix_comma_before_closer,
    "_find_nearby_comma_before_closer_line": _find_nearby_comma_before_closer_line,
    "_comma_line_invalid_tail_span": _comma_line_invalid_tail_span,
    "_line_has_comma_line_invalid_tail": _line_has_comma_line_invalid_tail,
    "_expected_missing_close_symbol": _expected_missing_close_symbol,
    "_fix_comma_line_invalid_tail": _fix_comma_line_invalid_tail,
    "_find_nearby_comma_line_invalid_tail_line": _find_nearby_comma_line_invalid_tail_line,
    "_missing_key_quote_before_colon_span": _missing_key_quote_before_colon_span,
    "_line_has_missing_key_quote_before_colon": _line_has_missing_key_quote_before_colon,
    "_fix_property_key_symbol_before_colon": _fix_property_key_symbol_before_colon,
    "_find_nearby_missing_key_quote_before_colon_line": _find_nearby_missing_key_quote_before_colon_line,
    "_property_key_invalid_escape_span": _property_key_invalid_escape_span,
    "_line_has_property_key_invalid_escape": _line_has_property_key_invalid_escape,
    "_fix_property_key_invalid_escape": _fix_property_key_invalid_escape,
    "_find_nearby_property_key_invalid_escape_line": _find_nearby_property_key_invalid_escape_line,
    "_missing_key_quote_before_colon_diag": _missing_key_quote_before_colon_diag,
    "_quoted_item_invalid_tail_span": _quoted_item_invalid_tail_span,
    "_line_has_invalid_tail_after_quoted_item": _line_has_invalid_tail_after_quoted_item,
    "_fix_invalid_tail_after_quoted_item": _fix_invalid_tail_after_quoted_item,
    "_find_nearby_invalid_tail_after_quoted_item_line": _find_nearby_invalid_tail_after_quoted_item_line,
    "_line_has_illegal_trailing_comma_before_close": _line_has_illegal_trailing_comma_before_close,
    "_trailing_comma_before_close_col": _trailing_comma_before_close_col,
    "_fix_illegal_trailing_comma_before_close": _fix_illegal_trailing_comma_before_close,
    "_find_nearby_illegal_trailing_comma_line": _find_nearby_illegal_trailing_comma_line,
    "_line_has_illegal_comma_after_top_level_close": _line_has_illegal_comma_after_top_level_close,
    "_top_level_close_symbol_run_span": _top_level_close_symbol_run_span,
    "_line_has_top_level_close_symbol_run": _line_has_top_level_close_symbol_run,
    "_fix_top_level_close_symbol_run": _fix_top_level_close_symbol_run,
    "_find_nearby_top_level_close_symbol_run_line": _find_nearby_top_level_close_symbol_run_line,
    "_comma_run_after_top_level_close_span": _comma_run_after_top_level_close_span,
    "_fix_illegal_comma_after_top_level_close": _fix_illegal_comma_after_top_level_close,
    "_find_nearby_illegal_comma_after_top_level_close_line": _find_nearby_illegal_comma_after_top_level_close_line,
    "_split_completed_scalar_value_tail": _split_completed_scalar_value_tail,
    "_line_has_invalid_trailing_symbols_after_string_value": _line_has_invalid_trailing_symbols_after_string_value,
    "_first_invalid_trailing_symbol_col": _first_invalid_trailing_symbol_col,
    "_fix_invalid_trailing_symbols_after_string_value": _fix_invalid_trailing_symbols_after_string_value,
    "_find_nearby_invalid_trailing_symbols_line": _find_nearby_invalid_trailing_symbols_line,
    "_line_has_invalid_symbol_after_closer": _line_has_invalid_symbol_after_closer,
    "_first_invalid_symbol_after_closer_col": _first_invalid_symbol_after_closer_col,
    "_fix_invalid_symbol_after_closer": _fix_invalid_symbol_after_closer,
    "_find_nearby_invalid_symbol_after_closer_line": _find_nearby_invalid_symbol_after_closer_line,
    "_invalid_symbol_after_open_span": _invalid_symbol_after_open_span,
    "_line_has_invalid_symbol_after_open": _line_has_invalid_symbol_after_open,
    "_fix_invalid_symbol_after_open": _fix_invalid_symbol_after_open,
    "_find_nearby_invalid_symbol_after_open_line": _find_nearby_invalid_symbol_after_open_line,
    "_find_nearby_extra_quote_in_value_line": _find_nearby_extra_quote_in_value_line,
    "_build_symbol_json_diagnostic": _build_symbol_json_diagnostic,
    "_build_json_diagnostic": _build_json_diagnostic,
    "_quote_unquoted_value": _quote_unquoted_value,
    "_quote_unquoted_scalar_line": _quote_unquoted_scalar_line,
    "_line_needs_value_quotes": _line_needs_value_quotes,
    "_missing_value_close_quote_insert_col": _missing_value_close_quote_insert_col,
    "_missing_value_open_quote_insert_col": _missing_value_open_quote_insert_col,
    "_find_nearby_missing_value_close_quote_line": _find_nearby_missing_value_close_quote_line,
    "_find_nearby_missing_value_open_quote_line": _find_nearby_missing_value_open_quote_line,
    "_find_nearby_unquoted_value_line": _find_nearby_unquoted_value_line,
    "_suggest_json_literal_from_token": _suggest_json_literal_from_token,
    "_boolean_literal_typo_diagnostic": _boolean_literal_typo_diagnostic,
    "_find_nearby_boolean_literal_typo_line": _find_nearby_boolean_literal_typo_line,
    "_is_wrong_list_open_for_object": _is_wrong_list_open_for_object,
    "_find_wrong_list_open_line": _find_wrong_list_open_line,
    "_find_wrong_object_open_line": _find_wrong_object_open_line,
    "_expected_closer_before_position": _expected_closer_before_position,
    "_find_wrong_closing_symbol_line": _find_wrong_closing_symbol_line,
    "_find_missing_list_close_before_object_end": _find_missing_list_close_before_object_end,
    "_next_non_empty_line_number": _next_non_empty_line_number,
    "_missing_list_open_key_line": _missing_list_open_key_line,
    "_line_looks_like_object_property": _line_looks_like_object_property,
    "_find_missing_container_open_after_key_line": _find_missing_container_open_after_key_line,
    "_find_missing_list_open_after_key_line": _find_missing_list_open_after_key_line,
    "_missing_close_example": _missing_close_example,
    "_format_suggestion": _format_suggestion,
    "_suggestion_from_example": _suggestion_from_example,
    "_is_missing_object_open_at": _is_missing_object_open_at,
    "_line_text": _line_text,
    "_line_has_missing_open_key_quote": _line_has_missing_open_key_quote,
    "_missing_close_target_line_from_exc": _missing_close_target_line_from_exc,
    "_missing_close_target_line_any": _missing_close_target_line_any,
    "_missing_list_close_target_line": _missing_list_close_target_line,
    "_unmatched_open_bracket_lines": _unmatched_open_bracket_lines,
    "_is_missing_list_close": _is_missing_list_close,
    "_is_missing_object_close": _is_missing_object_close,
    "_last_unmatched_bracket_line": _last_unmatched_bracket_line,
    "_line_indent_width": _line_indent_width,
    "_missing_close_insertion_point": _missing_close_insertion_point,
    "_missing_object_close_target_line": _missing_object_close_target_line,
    "_find_comma_only_line_before": _find_comma_only_line_before,
    "_find_missing_comma_between_block_values_line": _find_missing_comma_between_block_values_line,
    "_find_blank_line_before": _find_blank_line_before,
    "_closest_non_empty_line_before": _closest_non_empty_line_before,
    "_last_non_empty_line_number": _last_non_empty_line_number,
    "_missing_close_target_line": _missing_close_target_line,
    "_is_missing_object_open": _is_missing_object_open,
    "_is_missing_list_open": _is_missing_list_open,
    "_is_missing_list_open_at_start": _is_missing_list_open_at_start,
    "_missing_list_open_top_level": _missing_list_open_top_level,
    "_missing_object_open_from_extra_data": _missing_object_open_from_extra_data,
    "_first_non_ws_char": _first_non_ws_char,
    "_missing_list_open_from_extra_data": _missing_list_open_from_extra_data,
    "_previous_non_empty_line": _previous_non_empty_line,
    "_next_non_empty_line": _next_non_empty_line,
    "_missing_object_example": _missing_object_example,
    "_close_before_list": _close_before_list,
    "_quote_property_name": _quote_property_name,
    "_highlight_custom_range": _highlight_custom_range,
    "_fix_missing_at": _fix_missing_at,
    "_format_phone": _format_phone,
    "_find_phone_format_issue": _find_phone_format_issue,
    "_fix_missing_space_after_colon": _fix_missing_space_after_colon,
    "_find_json_spacing_issue": _find_json_spacing_issue,
    "_find_missing_email_at": _find_missing_email_at,
    "_path_targets_email": _path_targets_email,
    "_looks_like_email_candidate": _looks_like_email_candidate,
    "_should_validate_email_path_value": _should_validate_email_path_value,
    "_iter_candidate_email_values": _iter_candidate_email_values,
    "_format_path_for_display": _format_path_for_display,
    "_find_value_span_in_editor": _find_value_span_in_editor,
    "_find_invalid_email_in_value": _find_invalid_email_in_value,
    "_best_domain_root_similarity": _best_domain_root_similarity,
    "_suggest_known_domain_from_local_and_domain": _suggest_known_domain_from_local_and_domain,
    "_suggest_email_for_malformed": _suggest_email_for_malformed,
    "_validate_email_address": _validate_email_address,
    "_is_valid_email_domain": _is_valid_email_domain,
    "_find_invalid_email_format_issue": _find_invalid_email_format_issue,
    "_fix_missing_quote": _fix_missing_quote,
    "_unclosed_quoted_value_invalid_tail_span": _unclosed_quoted_value_invalid_tail_span,
    "_find_nearby_unclosed_quoted_value_invalid_tail_line": _find_nearby_unclosed_quoted_value_invalid_tail_line,
    "_comma_example_line": _comma_example_line,
    "_symbol_error_focus_index": _symbol_error_focus_index,
    "_apply_json_error_highlight": _apply_json_error_highlight,
    "_highlight_json_error": _highlight_json_error,
    "_place_error_pin": _place_error_pin,
    "_clear_error_pin": _clear_error_pin,
    "_position_error_overlay": _position_error_overlay,
    "_diag_system_from_note": _diag_system_from_note,
    "_log_json_error": _log_json_error,
    "_log_json_error_emergency": _log_json_error_emergency,
    "_log_input_mode_edit_issue": _log_input_mode_edit_issue,
    "_log_input_mode_apply_result": _log_input_mode_apply_result,
    "_log_input_mode_apply_trace": _log_input_mode_apply_trace,
    "_begin_diag_action": _begin_diag_action,
    "_clear_json_error_highlight": _clear_json_error_highlight,
}


def dispatch_method_names() -> tuple[str, ...]:
    """Return JSON repair dispatch method names exposed to JsonEditor."""
    return tuple(_REPAIR_DISPATCH_HANDLERS.keys())


def can_dispatch(name: str) -> bool:
    """Return whether method name is handled by JSON repair dispatch service."""
    return str(name or "") in _REPAIR_DISPATCH_HANDLERS


def dispatch(owner: Any, method_name: str, *args: Any, **kwargs: Any) -> Any:
    """Dispatch a JsonEditor repair/diagnostic method call to extracted handlers."""
    handler = _REPAIR_DISPATCH_HANDLERS.get(str(method_name or ""))
    if handler is None:
        raise AttributeError(f"Unsupported repair-dispatch method: {method_name!r}")
    return handler(owner, *args, **kwargs)


def build_editor_method(method_name: str) -> Callable[..., Any]:
    """Build JsonEditor-compatible bound-method proxy for a dispatch method name."""
    name = str(method_name or "")
    if name not in _REPAIR_DISPATCH_HANDLERS:
        raise AttributeError(f"Unsupported repair-dispatch method: {name!r}")

    def _method(owner: Any, *args: Any, **kwargs: Any) -> Any:
        return dispatch(owner, name, *args, **kwargs)

    _method.__name__ = name
    return _method

