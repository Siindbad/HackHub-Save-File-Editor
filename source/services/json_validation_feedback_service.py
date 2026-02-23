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
