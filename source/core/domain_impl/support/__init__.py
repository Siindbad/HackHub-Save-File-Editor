"""Support domain package exports and legacy module aliases."""

from __future__ import annotations

import sys

from . import telemetry_core

_TELEMETRY_LEGACY_MODULES = (
    "bug_report_browser_service",
    "bug_report_context_service",
    "bug_report_cooldown_service",
    "bug_report_service",
    "bug_report_submission_service",
    "bug_report_ui_service",
    "crash_logging_service",
    "crash_offer_service",
    "crash_report_service",
)

for _name in _TELEMETRY_LEGACY_MODULES:
    sys.modules[f"{__name__}.{_name}"] = telemetry_core
    globals()[_name] = telemetry_core

__all__ = [
    "telemetry_core",
]
