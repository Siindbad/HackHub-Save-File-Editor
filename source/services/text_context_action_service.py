"""Text-context menu action selection and dispatch helpers."""
from typing import Any


def first_enabled_action(states: Any, ordered_actions: Any=("undo", "redo", "copy", "paste", "autofix")) -> Any:
    """Return first enabled action from configured priority order."""
    state_map = states or {}
    for action in ordered_actions:
        if state_map.get(action):
            return action
    return None


def dispatch_click_action(action: Any, states: Any, hide_menu_fn: Any, handlers: Any) -> Any:
    """Run click action when enabled; always return Tk break token."""
    state_map = states or {}
    if not state_map.get(action):
        return "break"
    hide_menu_fn()
    handler = (handlers or {}).get(action)
    if callable(handler):
        handler()
    return "break"
