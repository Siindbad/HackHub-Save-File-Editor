"""JSON text-view find helpers for in-buffer next-match traversal."""
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def find_next_json_text_match(owner: Any, query: Any) -> Any:
    """Cycle through visible JSON text matches with wrap-around behavior."""
    text_widget = getattr(owner, "text", None)
    if text_widget is None:
        return False
    needle = str(query or "").strip()
    if not needle:
        return False
    try:
        if not text_widget.winfo_exists():
            return False
        query_key = needle.casefold()
        last_query = str(getattr(owner, "_json_find_last_query", "") or "")
        start_index = "1.0"
        wrapped = False
        current_start = ""
        if last_query == query_key:
            ranges = list(text_widget.tag_ranges("find_next_match"))
            if len(ranges) >= 2:
                current_start = str(ranges[0])
                start_index = str(ranges[1])
            else:
                start_index = str(text_widget.index("insert +1c"))

        start = text_widget.search(needle, start_index, stopindex="end", nocase=1)
        if not start and start_index != "1.0":
            wrapped = True
            start = text_widget.search(needle, "1.0", stopindex=start_index, nocase=1)
        if not start:
            owner._json_find_last_query = query_key
            return False
        if wrapped and current_start:
            # Any wrap means this JSON view is exhausted for forward traversal.
            # Hand off to tree-level fallback so Find Next advances sections.
            owner._json_find_last_query = query_key
            return False

        end = f"{start}+{len(needle)}c"
        prior_ranges = list(text_widget.tag_ranges("find_next_match"))
        if len(prior_ranges) >= 2:
            text_widget.tag_remove("find_next_match", prior_ranges[0], prior_ranges[1])
        else:
            text_widget.tag_remove("find_next_match", "1.0", "end")
        text_widget.tag_add("find_next_match", start, end)
        # Configure the match tag once per live text widget instead of per keystroke hit.
        if getattr(owner, "_json_find_tag_widget", None) is not text_widget:
            text_widget.tag_config(
                "find_next_match",
                background="#214a6a",
                foreground="#e8f6ff",
            )
            owner._json_find_tag_widget = text_widget
        text_widget.mark_set("insert", end)
        text_widget.see(start)
        owner._json_find_last_query = query_key
        return True
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return False


def focus_json_find_match(owner: Any, query: Any) -> Any:
    """After tree-level Find Next picks a node, jump to text match in JSON editor."""
    owner._json_find_last_query = ""
    find_next_json_text_match(owner, query)
