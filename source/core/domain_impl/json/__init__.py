"""JSON domain package exports and legacy module aliases."""

from __future__ import annotations

import sys

from . import json_diagnostics_core
from . import json_io_core
from . import json_navigation_core
from . import json_view_core

_JSON_LEGACY_MODULES = {
    # IO pillar
    "document_io_service": json_io_core,
    "json_apply_commit_service": json_io_core,
    "json_edit_flow_service": json_io_core,
    "json_path_service": json_io_core,
    "validation_service": json_io_core,
    # Diagnostics pillar
    "json_closer_symbol_service": json_diagnostics_core,
    "json_colon_comma_service": json_diagnostics_core,
    "json_diagnostics_service": json_diagnostics_core,
    "json_error_diag_service": json_diagnostics_core,
    "json_nearby_line_service": json_diagnostics_core,
    "json_open_symbol_service": json_diagnostics_core,
    "json_parse_feedback_service": json_diagnostics_core,
    "json_property_key_rule_service": json_diagnostics_core,
    "json_quoted_item_tail_service": json_diagnostics_core,
    "json_repair_service": json_diagnostics_core,
    "json_scalar_tail_service": json_diagnostics_core,
    "json_top_level_close_service": json_diagnostics_core,
    "json_validation_feedback_service": json_diagnostics_core,
    # Navigation pillar
    "json_find_nav_service": json_navigation_core,
    "json_find_orchestrator_service": json_navigation_core,
    "json_find_service": json_navigation_core,
    "json_text_find_service": json_navigation_core,
    # View pillar
    "json_error_highlight_render_service": json_view_core,
    "json_view_render_service": json_view_core,
    "json_view_service": json_view_core,
}

for _name, _module in _JSON_LEGACY_MODULES.items():
    sys.modules[f"{__name__}.{_name}"] = _module
    globals()[_name] = _module

__all__ = [
    "json_io_core",
    "json_diagnostics_core",
    "json_navigation_core",
    "json_view_core",
]
