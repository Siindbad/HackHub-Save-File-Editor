"""Shared parse-error feedback helpers for JSON apply/live flows."""

from __future__ import annotations

import logging
from typing import Any
from core.exceptions import EXPECTED_ERRORS
_LOG = logging.getLogger(__name__)

_LOGGER = logging.getLogger(__name__)
_EXPECTED_PARSE_FEEDBACK_ERRORS = (
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    AttributeError,
    KeyError,
    IndexError,
    ImportError,
)


def _log_expected_dispatch_error(stage: str, exc: Exception) -> None:
    _LOGGER.debug(
        "json_parse_feedback.dispatch_expected_error",
        extra={"stage": stage, "error_type": type(exc).__name__},
        exc_info=exc,
    )


def handle_live_parse_error(owner: Any, exc: Exception, path: list[str]) -> None:
    """Render and log live-feedback parse errors with overlay/highlight updates."""
    # Live JSON feedback diagnostics: force one parse-entry marker so
    # overlay-only validation errors always reach the diagnostics log.
    owner._begin_diag_action("live_json_feedback")
    try:
        emergency_logger = getattr(owner, "_log_json_error_emergency", None)
        if callable(emergency_logger):
            emergency_logger(
                exc,
                getattr(exc, "lineno", None) or 1,
                note="overlay_parse_live_emergency",
            )
    except _EXPECTED_PARSE_FEEDBACK_ERRORS as dispatch_exc:
        _log_expected_dispatch_error("live_emergency_logger", dispatch_exc)
    try:
        owner._log_json_error(exc, getattr(exc, "lineno", None) or 1, note="overlay_parse_live_enter")
    except _EXPECTED_PARSE_FEEDBACK_ERRORS as dispatch_exc:
        _log_expected_dispatch_error("live_primary_logger", dispatch_exc)
    owner._error_visual_mode = "guide"
    owner._show_error_overlay("Invalid Entry", owner._format_json_error(exc))
    # Keep highlight-label colors active while JSON is temporarily invalid.
    owner._apply_json_view_lock_state(path)
    owner._highlight_json_error(exc)


def handle_apply_parse_error(owner: Any, exc: Exception, path: list[str]) -> None:
    """Render and log apply-flow parse errors with fallback diagnostic note."""
    # Hard guarantee: append at least one diagnostics entry for every
    # Apply Edit parse failure, even if normal logger flow is bypassed.
    try:
        emergency_logger = getattr(owner, "_log_json_error_emergency", None)
        if callable(emergency_logger):
            emergency_logger(
                exc,
                getattr(exc, "lineno", None) or 1,
                note="overlay_parse_apply_emergency",
            )
    except _EXPECTED_PARSE_FEEDBACK_ERRORS as dispatch_exc:
        _log_expected_dispatch_error("apply_emergency_logger", dispatch_exc)
    message = owner._format_json_error(exc)
    owner._error_visual_mode = "guide"
    owner._show_error_overlay("Invalid Entry", message)
    # Keep highlight-label colors active while JSON is temporarily invalid.
    owner._apply_json_view_lock_state(path)
    # Prefer one specific diagnostic note per apply cycle; use overlay_parse only as fallback.
    owner._last_error_highlight_note = ""
    owner._highlight_json_error(exc)
    highlight_note = str(getattr(owner, "_last_error_highlight_note", "") or "").strip()
    if not highlight_note or highlight_note == "highlight" or highlight_note.startswith("highlight_failed"):
        try:
            owner._log_json_error(exc, getattr(exc, "lineno", None) or 1, note="overlay_parse")
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            pass
