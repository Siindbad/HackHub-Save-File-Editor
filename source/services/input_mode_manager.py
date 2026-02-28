"""INPUT mode domain module."""

from core.domain_impl.infra import input_mode_diag_service
from core.domain_impl.infra import input_mode_find_service
from core.domain_impl.infra import input_mode_render_dispatch_service
from core.domain_impl.infra import input_mode_service


class InputModeManager:
    input_mode_diag_service = input_mode_diag_service
    input_mode_find_service = input_mode_find_service
    input_mode_render_dispatch_service = input_mode_render_dispatch_service
    input_mode_service = input_mode_service


INPUT_MODE = InputModeManager()
