"""Theme and INPUT style domain module."""

from core.domain_impl.support import input_bank_style_service
from core.domain_impl.support import input_database_style_service
from core.domain_impl.support import input_network_firewall_style_service
from core.domain_impl.support import input_network_router_style_service
from core.domain_impl.support import input_suspicion_phone_style_service
from core.domain_impl.ui import theme_asset_service
from core.domain_impl.ui import theme_service


class ThemeManager:
    input_bank_style_service = input_bank_style_service
    input_database_style_service = input_database_style_service
    input_network_firewall_style_service = input_network_firewall_style_service
    input_network_router_style_service = input_network_router_style_service
    input_suspicion_phone_style_service = input_suspicion_phone_style_service
    theme_asset_service = theme_asset_service
    theme_service = theme_service


THEME = ThemeManager()
