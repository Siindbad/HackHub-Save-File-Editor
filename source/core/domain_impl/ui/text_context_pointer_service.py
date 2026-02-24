"""Text-context menu pointer/action resolution helpers."""
from typing import Any


def action_for_widget(widget: Any, widget_actions: Any, expected_errors: Any) -> Any:
    """Resolve context-menu action by walking widget->master chain."""
    current = widget
    while current is not None:
        action = widget_actions.get(current)
        if action:
            return action
        try:
            current = current.master
        except expected_errors:
            current = None
    return None


def action_for_pointer(
    popup: Any,
    root: Any,
    widget_actions: Any,
    widget_is_popup_child: Any,
    expected_errors: Any,
) -> Any:
    """Resolve action under pointer and whether pointer is inside popup."""
    if popup is None or root is None:
        return None, False
    try:
        pointer_x = root.winfo_pointerx()
        pointer_y = root.winfo_pointery()
        under_pointer = root.winfo_containing(pointer_x, pointer_y)
    except expected_errors:
        return None, False
    action = action_for_widget(under_pointer, widget_actions, expected_errors)
    if action:
        return action, True
    if not widget_is_popup_child(under_pointer, popup):
        return None, False
    return None, True
