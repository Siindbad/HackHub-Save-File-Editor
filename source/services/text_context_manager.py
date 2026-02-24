"""Text context domain module."""

from core.domain_impl.ui import text_context_action_service
from core.domain_impl.ui import text_context_menu_service
from core.domain_impl.ui import text_context_pointer_service
from core.domain_impl.ui import text_context_state_service
from core.domain_impl.ui import text_context_widget_service


class TextContextManager:
    text_context_action_service = text_context_action_service
    text_context_menu_service = text_context_menu_service
    text_context_pointer_service = text_context_pointer_service
    text_context_state_service = text_context_state_service
    text_context_widget_service = text_context_widget_service


TEXT_CONTEXT = TextContextManager()
