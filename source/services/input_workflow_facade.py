"""INPUT workflow facade for INPUT-mode and game-specific style domains."""

from core.domain_impl.infra import input_mode_diag_service
from core.domain_impl.infra import input_mode_find_service
from core.domain_impl.infra import input_mode_render_dispatch_service
from core.domain_impl.infra import input_mode_service
from core.domain_impl.support import input_bank_style_service
from core.domain_impl.support import input_database_bcc_style_service
from core.domain_impl.support import input_database_style_service
from core.domain_impl.support import input_network_device_bcc_style_service
from core.domain_impl.support import input_network_device_geoip_style_service
from core.domain_impl.support import input_network_firewall_style_service
from core.domain_impl.support import input_network_router_style_service
from core.domain_impl.support import input_suspicion_phone_style_service


class InputModeManager:
    input_mode_diag_service = input_mode_diag_service
    input_mode_find_service = input_mode_find_service
    input_mode_render_dispatch_service = input_mode_render_dispatch_service
    input_mode_service = input_mode_service


class InputWorkflowFacade:
    """Master INPUT facade exposing render/find/diag plus style orchestration."""

    input_mode_diag_service = input_mode_diag_service
    input_mode_find_service = input_mode_find_service
    input_mode_render_dispatch_service = input_mode_render_dispatch_service
    input_mode_service = input_mode_service
    input_bank_style_service = input_bank_style_service
    input_database_bcc_style_service = input_database_bcc_style_service
    input_database_style_service = input_database_style_service
    input_network_firewall_style_service = input_network_firewall_style_service
    input_network_device_bcc_style_service = input_network_device_bcc_style_service
    input_network_device_geoip_style_service = input_network_device_geoip_style_service
    input_network_router_style_service = input_network_router_style_service
    input_suspicion_phone_style_service = input_suspicion_phone_style_service


INPUT_MODE = InputModeManager()
INPUT_WORKFLOW = InputWorkflowFacade()

