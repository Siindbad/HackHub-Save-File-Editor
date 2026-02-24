"""JSON diagnostics and repair domain module."""

from core.domain_impl.json import json_apply_commit_service
from core.domain_impl.json import json_closer_symbol_service
from core.domain_impl.json import json_colon_comma_service
from core.domain_impl.json import json_diagnostics_service
from core.domain_impl.json import json_edit_flow_service
from core.domain_impl.json import json_error_diag_service
from core.domain_impl.json import json_error_highlight_render_service
from core.domain_impl.json import json_nearby_line_service
from core.domain_impl.json import json_open_symbol_service
from core.domain_impl.json import json_parse_feedback_service
from core.domain_impl.json import json_path_service
from core.domain_impl.json import json_property_key_rule_service
from core.domain_impl.json import json_quoted_item_tail_service
from core.domain_impl.json import json_repair_service
from core.domain_impl.json import json_scalar_tail_service
from core.domain_impl.json import json_top_level_close_service
from core.domain_impl.json import json_validation_feedback_service


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


JSON_ENGINE = JsonEngine()
