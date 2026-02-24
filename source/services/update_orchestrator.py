"""Update domain module."""

from core.domain_impl.infra import update_asset_service
from core.domain_impl.infra import update_checksum_service
from core.domain_impl.infra import update_diag_service
from core.domain_impl.infra import update_download_service
from core.domain_impl.infra import update_fallback_service
from core.domain_impl.infra import update_headers_service
from core.domain_impl.infra import update_orchestrator_service
from core.domain_impl.infra import update_release_info_service
from core.domain_impl.infra import update_service
from core.domain_impl.infra import update_signature_service
from core.domain_impl.infra import update_ui_service
from core.domain_impl.infra import update_url_service
from core.domain_impl.infra import update_version_service


class UpdateOrchestrator:
    update_asset_service = update_asset_service
    update_checksum_service = update_checksum_service
    update_diag_service = update_diag_service
    update_download_service = update_download_service
    update_fallback_service = update_fallback_service
    update_headers_service = update_headers_service
    update_orchestrator_service = update_orchestrator_service
    update_release_info_service = update_release_info_service
    update_service = update_service
    update_signature_service = update_signature_service
    update_ui_service = update_ui_service
    update_url_service = update_url_service
    update_version_service = update_version_service


UPDATE = UpdateOrchestrator()
