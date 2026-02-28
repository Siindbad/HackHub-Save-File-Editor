"""Text-context menu action selection and dispatch helpers."""
import re
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


def tick_text_context_menu_pulse(
    owner: Any,
    *,
    expected_errors: tuple[type[BaseException], ...],
) -> None:
    """Animate text-context border pulse while popup is visible."""
    owner._text_context_menu_pulse_after_id = None
    popup = getattr(owner, "_text_context_menu", None)
    if popup is None:
        return
    try:
        if not popup.winfo_exists() or not popup.winfo_ismapped():
            return
    except expected_errors:
        return
    palette = owner._text_context_menu_palette()
    hover_action = getattr(owner, "_text_context_menu_hover_action", None)
    if hover_action:
        root = getattr(owner, "root", None)
        if root is None:
            return
        try:
            owner._text_context_menu_pulse_after_id = root.after(140, owner._tick_text_context_menu_pulse)
        except expected_errors:
            owner._text_context_menu_pulse_after_id = None
        return

    cycle_steps = 28
    tick = int(getattr(owner, "_text_context_menu_pulse_tick", 0))
    half = cycle_steps / 2.0
    pos = float(tick % cycle_steps)
    if pos <= half:
        amount = pos / half
    else:
        amount = (cycle_steps - pos) / half
    border_base = palette.get("pulse_start_border", palette["border"])
    inset_base = palette.get("pulse_start_inset", palette["inset_border"])
    panel_base = palette.get("pulse_start_panel", palette["panel_border"])
    border_color = owner._blend_hex_color(border_base, palette["pulse_border"], amount)
    inset_color = owner._blend_hex_color(inset_base, palette["pulse_inset"], amount)
    panel_color = owner._blend_hex_color(panel_base, palette["pulse_inset"], amount * 0.75)
    owner._text_context_menu_pulse_tick = tick + 1

    anchor = getattr(owner, "_text_context_menu_anchor", None)
    frame = getattr(owner, "_text_context_menu_frame", None)
    panel = getattr(owner, "_text_context_menu_panel", None)
    if anchor is not None:
        try:
            anchor.configure(highlightbackground=border_color, highlightcolor=border_color)
        except expected_errors:
            pass
    if frame is not None:
        try:
            frame.configure(highlightbackground=inset_color, highlightcolor=inset_color)
        except expected_errors:
            pass
    if panel is not None:
        try:
            panel.configure(highlightbackground=panel_color, highlightcolor=panel_color)
        except expected_errors:
            pass
    root = getattr(owner, "root", None)
    if root is None:
        return
    try:
        owner._text_context_menu_pulse_after_id = root.after(100, owner._tick_text_context_menu_pulse)
    except expected_errors:
        owner._text_context_menu_pulse_after_id = None


def on_input_context_paste(
    owner: Any,
    *,
    clipboard_service: Any,
    validation_service: Any,
    expected_errors: tuple[type[BaseException], ...],
) -> None:
    """Paste into current INPUT widget with validation and readonly guards."""
    widget = getattr(owner, "_input_context_target_widget", None)
    if widget is None:
        return
    if not bool(getattr(owner, "_input_context_target_allow_paste", False)):
        return
    try:
        pasted = owner.root.clipboard_get()
    except expected_errors:
        return
    if pasted is None:
        return
    is_valid, safe_text, reason = clipboard_service.validate_clipboard_paste_payload(
        pasted,
        validation_service.validate_editor_text_payload,
    )
    if not is_valid:
        owner._show_error_overlay("Invalid Entry", reason)
        return
    try:
        state = str(widget.cget("state")).lower()
    except expected_errors:
        state = "normal"
    if state in ("readonly", "disabled"):
        return
    try:
        if owner._input_widget_has_selection(widget):
            widget.delete("sel.first", "sel.last")
    except expected_errors:
        pass
    try:
        widget.insert("insert", safe_text)
    except expected_errors:
        return


def apply_line_autofix(
    owner: Any,
    line_no: Any,
    before_text: Any,
    after_text: Any,
    *,
    expected_errors: tuple[type[BaseException], ...],
) -> bool:
    """Apply one-line autofix replacement while preserving cursor position."""
    if not line_no:
        return False
    raw_line = owner._line_text(int(line_no))
    if raw_line is None:
        return False
    indent_match = re.match(r"^\s*", raw_line) if raw_line else None
    indent = indent_match.group(0) if indent_match is not None else ""
    before = str(before_text) if before_text is not None else ""
    after = str(after_text or "")

    new_line = None
    caret_col = 0
    if before and before in raw_line:
        replace_at = raw_line.find(before)
        new_line = raw_line.replace(before, after, 1)
        caret_col = max(0, int(replace_at + len(after)))
    elif before and raw_line.strip() == before.strip():
        new_line = indent + after.lstrip()
        caret_col = max(0, len(new_line))
    elif not before:
        new_line = indent + after.lstrip()
        caret_col = max(0, len(new_line))
    else:
        stripped_raw = raw_line.strip()
        if stripped_raw:
            new_line = indent + after.lstrip()
            caret_col = max(0, len(new_line))
        else:
            new_line = after
            caret_col = max(0, len(new_line))
    if new_line is None:
        return False

    try:
        start_idx = f"{int(line_no)}.0"
        owner.text.delete(start_idx, f"{int(line_no)}.0 lineend")
        owner.text.insert(start_idx, new_line)
        caret_col = min(max(int(caret_col), 0), len(new_line))
        owner.text.mark_set("insert", f"{int(line_no)}.{caret_col}")
        owner.text.see(f"{int(line_no)}.{caret_col}")
        return True
    except expected_errors:
        return False
