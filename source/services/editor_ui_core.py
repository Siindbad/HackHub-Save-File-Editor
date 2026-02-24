"""Editor UI assembly domain module."""

from core.domain_impl.ui import footer_service
from core.domain_impl.ui import loader_service
from core.domain_impl.ui import startup_loader_ui_service
from core.domain_impl.ui import toolbar_service
from core.domain_impl.ui import ui_build_service
from core.domain_impl.ui import ui_dispatch_service


class EditorUICore:
    footer_service = footer_service
    loader_service = loader_service
    startup_loader_ui_service = startup_loader_ui_service
    toolbar_service = toolbar_service
    ui_build_service = ui_build_service
    ui_dispatch_service = ui_dispatch_service


EDITOR_UI = EditorUICore()
