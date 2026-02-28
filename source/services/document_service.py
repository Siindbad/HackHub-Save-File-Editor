"""Document and editor mode domain module."""

from __future__ import annotations

from typing import Any, Callable

from core.domain_impl.json import document_io_service
from core.domain_impl.support import editor_mode_switch_service
from core.domain_impl.support import editor_purge_service


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


class DocumentService:
    document_io_service = document_io_service
    editor_mode_switch_service = editor_mode_switch_service
    editor_purge_service = editor_purge_service
    initialize_async_load_result = staticmethod(initialize_async_load_result)
    build_async_document_load_worker = staticmethod(build_async_document_load_worker)
    apply_async_loaded_document = staticmethod(apply_async_loaded_document)


DOCUMENT = DocumentService()
