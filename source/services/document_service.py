"""Document and editor mode domain module."""

from core.domain_impl.json import document_io_service
from core.domain_impl.support import editor_mode_switch_service
from core.domain_impl.support import editor_purge_service


class DocumentService:
    document_io_service = document_io_service
    editor_mode_switch_service = editor_mode_switch_service
    editor_purge_service = editor_purge_service


DOCUMENT = DocumentService()
