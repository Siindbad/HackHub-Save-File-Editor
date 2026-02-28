"""Editor UI assembly domain module."""

from core.domain_impl.ui import asset_image_service
from core.domain_impl.ui import footer_service
from core.domain_impl.ui import input_mode_paned_lock_service
from core.domain_impl.ui import loader_service
from core.domain_impl.ui import readme_ui_service
from core.domain_impl.ui import startup_loader_lifecycle_service
from core.domain_impl.ui import startup_loader_ui_service
from core.domain_impl.ui import toolbar_service
from core.domain_impl.ui import ui_build_service
from core.domain_impl.ui import ui_dispatch_service
from core.domain_impl.ui import ui_factory_service


class EditorUICore:
    asset_image_service = asset_image_service
    footer_service = footer_service
    input_mode_paned_lock_service = input_mode_paned_lock_service
    loader_service = loader_service
    readme_ui_service = readme_ui_service
    startup_loader_lifecycle_service = startup_loader_lifecycle_service
    startup_loader_ui_service = startup_loader_ui_service
    toolbar_service = toolbar_service
    ui_build_service = ui_build_service
    ui_dispatch_service = ui_dispatch_service
    ui_factory_service = ui_factory_service


EDITOR_UI = EditorUICore()
