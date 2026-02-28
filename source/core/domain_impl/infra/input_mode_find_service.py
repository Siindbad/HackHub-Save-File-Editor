"""INPUT-mode find helpers for widget indexing and viewport scrolling."""
from collections import deque
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def find_first_entry_descendant(root_widget: Any, tk_module: Any) -> Any:
    """Return first entry descendant under root widget breadth-first."""
    if root_widget is None:
        return None
    queue = deque([root_widget])
    while queue:
        current = queue.popleft()
        if isinstance(current, tk_module.Entry):
            return current
        try:
            queue.extend(list(current.winfo_children()))
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            continue
    return None


def build_input_mode_search_entries(owner: Any, tk_module: Any) -> Any:
    """Build searchable text entries from INPUT-mode widgets."""
    host = getattr(owner, "_input_mode_fields_host", None)
    if host is None:
        return []
    entries = []

    def _walk(widget):
        try:
            children = list(widget.winfo_children())
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            children = []
        for child in children:
            _add_entry(child)
            _walk(child)

    def _add_entry(widget):
        text = ""
        focus_widget = None
        try:
            if isinstance(widget, tk_module.Entry):
                text = str(widget.get() or "")
                focus_widget = widget
            elif isinstance(widget, tk_module.Label):
                text = str(widget.cget("text") or "")
                focus_widget = find_first_entry_descendant(getattr(widget, "master", None), tk_module)
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            return
        text = text.strip()
        if not text:
            return
        entries.append(({"widget": widget, "focus_widget": focus_widget}, text.casefold()))

    _walk(host)
    return entries


def scroll_input_widget_into_view(owner: Any, widget: Any) -> Any:
    """Scroll INPUT canvas so target widget appears near top-third of viewport."""
    canvas = getattr(owner, "_input_mode_canvas", None)
    host = getattr(owner, "_input_mode_fields_host", None)
    if canvas is None or host is None or widget is None:
        return
    try:
        canvas.update_idletasks()
        host.update_idletasks()
        total_height = max(1, int(host.winfo_height()))
        view_height = max(1, int(canvas.winfo_height()))
        y_in_host = int(widget.winfo_rooty() - host.winfo_rooty())
        target_y = max(0, y_in_host - int(view_height * 0.35))
        denom = max(1, total_height - view_height)
        fraction = max(0.0, min(1.0, float(target_y) / float(denom)))
        canvas.yview_moveto(fraction)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return


def find_next_input_mode(owner: Any, tk_module: Any) -> Any:
    """Run INPUT-mode Find Next traversal and focus behavior."""
    query = owner.find_entry.get().strip()
    if not query:
        owner.set_status("Find: enter text to search")
        return

    query_lower = query.lower()
    if (
        query_lower != owner.last_find_query
        or not owner.find_matches
        or not isinstance(owner.find_matches[0], dict)
        or "widget" not in owner.find_matches[0]
    ):
        entries = owner._build_input_mode_search_entries()
        owner.find_matches = [entry[0] for entry in entries if query_lower in entry[1]]
        owner.find_index = 0
        owner.last_find_query = query_lower

    if not owner.find_matches:
        owner.set_status(f'Find: no matches for "{query}"')
        return

    match = owner.find_matches[owner.find_index]
    owner.find_index = (owner.find_index + 1) % len(owner.find_matches)
    widget = match.get("widget")
    if widget is not None:
        owner._scroll_input_widget_into_view(widget)
        try:
            focus_target = match.get("focus_widget") or widget
            focus_target.focus_set()
            if isinstance(focus_target, tk_module.Entry):
                focus_target.selection_range(0, "end")
                focus_target.icursor("end")
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            pass
    owner.set_status(f"Find: {owner.find_index}/{len(owner.find_matches)}")
