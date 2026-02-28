"""Infra domain package exports and legacy module aliases."""

from __future__ import annotations

import sys

from . import update_engine_core

_UPDATE_LEGACY_MODULES = (
    "update_asset_service",
    "update_checksum_service",
    "update_diag_service",
    "update_download_service",
    "update_fallback_service",
    "update_headers_service",
    "update_orchestrator_service",
    "update_release_info_service",
    "update_service",
    "update_signature_service",
    "update_ui_service",
    "update_url_service",
    "update_version_service",
)

for _name in _UPDATE_LEGACY_MODULES:
    sys.modules[f"{__name__}.{_name}"] = update_engine_core
    globals()[_name] = update_engine_core

__all__ = [
    "update_engine_core",
]
