"""Presentation service facade for UI, theme, text context, and tree domains."""

from __future__ import annotations

from core.domain_impl.ui import asset_image_service
from core.domain_impl.ui import color_utility_service
from core.domain_impl.ui import footer_service
from core.domain_impl.ui import input_mode_paned_lock_service
from core.domain_impl.ui import loader_service
from core.domain_impl.ui import readme_ui_service
from core.domain_impl.ui import startup_loader_lifecycle_service
from core.domain_impl.ui import startup_loader_ui_service
from core.domain_impl.ui import text_context_action_service
from core.domain_impl.ui import text_context_menu_service
from core.domain_impl.ui import text_context_pointer_service
from core.domain_impl.ui import text_context_state_service
from core.domain_impl.ui import text_context_widget_service
from core.domain_impl.ui import theme_asset_service
from core.domain_impl.ui import theme_service
from core.domain_impl.ui import toolbar_service
from core.domain_impl.ui import tree_engine_service
from core.domain_impl.ui import tree_mode_service
from core.domain_impl.ui import tree_navigation_service
from core.domain_impl.ui import tree_policy_service
from core.domain_impl.ui import tree_view_service
from core.domain_impl.ui import ui_build_service
from core.domain_impl.ui import ui_dispatch_service
from core.domain_impl.ui import ui_factory_service
from core.domain_impl.ui import ui_timer_service


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
    ui_timer_service = ui_timer_service


class ThemeManager:
    color_utility_service = color_utility_service
    theme_asset_service = theme_asset_service
    theme_service = theme_service


class TextContextManager:
    text_context_action_service = text_context_action_service
    text_context_menu_service = text_context_menu_service
    text_context_pointer_service = text_context_pointer_service
    text_context_state_service = text_context_state_service
    text_context_widget_service = text_context_widget_service


class TreeManager:
    tree_engine_service = tree_engine_service
    tree_mode_service = tree_mode_service
    tree_navigation_service = tree_navigation_service
    tree_policy_service = tree_policy_service
    tree_view_service = tree_view_service


EDITOR_UI = EditorUICore()
THEME = ThemeManager()
TEXT_CONTEXT = TextContextManager()
TREE = TreeManager()


def _bind_singletons(
    *,
    editor_ui: EditorUICore,
    theme: ThemeManager,
    text_context: TextContextManager,
    tree: TreeManager,
) -> None:
    """Bind facade singleton aliases from the global service registry."""
    global EDITOR_UI
    global THEME
    global TEXT_CONTEXT
    global TREE
    EDITOR_UI = editor_ui
    THEME = theme
    TEXT_CONTEXT = text_context
    TREE = tree
