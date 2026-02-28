"""JSON diagnostics and repair domain module."""

from core.domain_impl.json import json_io_core as json_apply_commit_service
from core.domain_impl.json import json_diagnostics_core as json_closer_symbol_service
from core.domain_impl.json import json_diagnostics_core as json_colon_comma_service
from core.domain_impl.json import json_diagnostics_core as json_diagnostics_service
from core.domain_impl.json import json_io_core as json_edit_flow_service
from core.domain_impl.json import json_diagnostics_core as json_error_diag_service
from core.domain_impl.json import json_view_core as json_error_highlight_render_service
from core.domain_impl.json import json_diagnostics_core as json_nearby_line_service
from core.domain_impl.json import json_diagnostics_core as json_open_symbol_service
from core.domain_impl.json import json_diagnostics_core as json_parse_feedback_service
from core.domain_impl.json import json_io_core as json_path_service
from core.domain_impl.json import json_diagnostics_core as json_property_key_rule_service
from core.domain_impl.json import json_diagnostics_core as json_quoted_item_tail_service
from core.domain_impl.json import json_diagnostics_core as json_repair_service
from core.domain_impl.json import json_diagnostics_core as json_scalar_tail_service
from core.domain_impl.json import json_diagnostics_core as json_top_level_close_service
from core.domain_impl.json import json_diagnostics_core as json_validation_feedback_service
from core.domain_impl.support import json_repair_dispatch_service


class JsonEngine:
    json_apply_commit_service = json_apply_commit_service
    json_closer_symbol_service = json_closer_symbol_service
    json_colon_comma_service = json_colon_comma_service
    json_diagnostics_service = json_diagnostics_service
    json_edit_flow_service = json_edit_flow_service
    json_error_diag_service = json_error_diag_service
    json_error_highlight_render_service = json_error_highlight_render_service
    json_nearby_line_service = json_nearby_line_service
    json_open_symbol_service = json_open_symbol_service
    json_parse_feedback_service = json_parse_feedback_service
    json_path_service = json_path_service
    json_property_key_rule_service = json_property_key_rule_service
    json_quoted_item_tail_service = json_quoted_item_tail_service
    json_repair_service = json_repair_service
    json_scalar_tail_service = json_scalar_tail_service
    json_top_level_close_service = json_top_level_close_service
    json_validation_feedback_service = json_validation_feedback_service
    repair_dispatch = json_repair_dispatch_service


JSON_ENGINE = JsonEngine()
