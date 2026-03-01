"""JSON lifecycle facade combining document, JSON view, and validation domains."""

from __future__ import annotations

from typing import Any, Callable

from core.domain_impl.json import json_diagnostics_core as json_closer_symbol_service
from core.domain_impl.json import json_diagnostics_core as json_colon_comma_service
from core.domain_impl.json import json_diagnostics_core as json_diagnostics_service
from core.domain_impl.json import json_diagnostics_core as json_error_diag_service
from core.domain_impl.json import json_diagnostics_core as json_nearby_line_service
from core.domain_impl.json import json_diagnostics_core as json_open_symbol_service
from core.domain_impl.json import json_diagnostics_core as json_parse_feedback_service
from core.domain_impl.json import json_diagnostics_core as json_property_key_rule_service
from core.domain_impl.json import json_diagnostics_core as json_quoted_item_tail_service
from core.domain_impl.json import json_diagnostics_core as json_repair_service
from core.domain_impl.json import json_diagnostics_core as json_scalar_tail_service
from core.domain_impl.json import json_diagnostics_core as json_top_level_close_service
from core.domain_impl.json import json_diagnostics_core as json_validation_feedback_service
from core.domain_impl.json import json_io_core as document_io_service
from core.domain_impl.json import json_io_core as json_apply_commit_service
from core.domain_impl.json import json_io_core as json_edit_flow_service
from core.domain_impl.json import json_io_core as json_path_service
from core.domain_impl.json import json_io_core as validation_service
from core.domain_impl.json import json_navigation_core as json_find_nav_service
from core.domain_impl.json import json_navigation_core as json_find_orchestrator_service
from core.domain_impl.json import json_navigation_core as json_find_service
from core.domain_impl.json import json_navigation_core as json_text_find_service
from core.domain_impl.json import json_view_core as json_error_highlight_render_service
from core.domain_impl.json import json_view_core as json_view_render_service
from core.domain_impl.json import json_view_core as json_view_service
from core.domain_impl.support import editor_mode_switch_service
from core.domain_impl.support import editor_purge_service
from core.domain_impl.support import highlight_label_service
from core.domain_impl.support import json_repair_dispatch_service
from core.domain_impl.support import label_format_service
from core.domain_impl.support import version_format_service


def initialize_async_load_result(owner: Any, *, request_id: int, path: str) -> None:
    """Initialize shared async-load result payload for the active request."""
    owner._document_load_async_result = {
        "request_id": int(request_id),
        "path": str(path),
        "done": False,
        "payload": None,
        "error_text": "",
    }


def build_async_document_load_worker(
    owner: Any,
    *,
    request_id: int,
    path: str,
    json_module: Any,
) -> Callable[[], None]:
    """Build the worker callable that loads document payload in a background thread."""

    def _worker() -> None:
        payload: object | None = None
        error_text = ""
        try:
            payload = editor_purge_service.load_document_payload(path)
        except (OSError, UnicodeDecodeError, json_module.JSONDecodeError, ValueError, TypeError) as exc:
            error_text = str(exc)
        result = getattr(owner, "_document_load_async_result", None)
        if not isinstance(result, dict):
            return
        if int(result.get("request_id", 0) or 0) != int(request_id):
            return
        result["payload"] = payload
        result["error_text"] = error_text
        result["done"] = True

    return _worker


def apply_async_loaded_document(
    owner: Any,
    *,
    path: str,
    payload: object,
    error_text: str,
    messagebox_module: Any,
) -> None:
    """Apply async load result or surface a user-facing load error."""
    if bool(getattr(owner, "_shutdown_cleanup_done", False)):
        return
    if error_text:
        messagebox_module.showerror("Load failed", str(error_text))
        return
    editor_purge_service.apply_loaded_document(owner, path, payload)


def save(path: str, data: Any) -> None:
    """Save document data as pretty JSON text using JSON IO core formatting."""
    payload = str(document_io_service.build_pretty_json_payload(data))
    with open(str(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)


class DocumentService:
    document_io_service = document_io_service
    editor_mode_switch_service = editor_mode_switch_service
    editor_purge_service = editor_purge_service
    initialize_async_load_result = staticmethod(initialize_async_load_result)
    build_async_document_load_worker = staticmethod(build_async_document_load_worker)
    apply_async_loaded_document = staticmethod(apply_async_loaded_document)
    save = staticmethod(save)


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

    @staticmethod
    def load(path: Any) -> Any:
        """Load a JSON/.hhsav document through the JSON IO core pillar."""
        return json_apply_commit_service.load_document(path)


class JsonViewManager:
    json_find_nav_service = json_find_nav_service
    json_find_orchestrator_service = json_find_orchestrator_service
    json_find_service = json_find_service
    json_text_find_service = json_text_find_service
    json_view_render_service = json_view_render_service
    json_view_service = json_view_service


class ValidationEngine:
    highlight_label_service = highlight_label_service
    json_validation_feedback_service = json_validation_feedback_service
    label_format_service = label_format_service
    validation_service = validation_service
    version_format_service = version_format_service


class JsonLifecycleFacade:
    """Master facade grouping document, JSON engine/view, and validation domains."""

    document = DocumentService()
    json_engine = JsonEngine()
    json_view = JsonViewManager()
    validation = ValidationEngine()


JSON_LIFECYCLE = JsonLifecycleFacade()
DOCUMENT = JSON_LIFECYCLE.document
JSON_ENGINE = JSON_LIFECYCLE.json_engine
JSON_VIEW = JSON_LIFECYCLE.json_view
VALIDATION = JSON_LIFECYCLE.validation

