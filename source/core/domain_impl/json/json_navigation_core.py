"""Consolidated JSON domain pillar: json_navigation_core.

Contains merged logic from split JSON domain services.
"""


# --- Merged from json_find_service.py ---
"""JSON-mode find helpers for deterministic data-path matching."""
from typing import Any


def build_json_find_matches(owner: Any, query_lower: Any) -> Any:
    """Build deterministic JSON-mode path matches for Find Next traversal."""
    needle = str(query_lower or "").strip().casefold()
    if not needle:
        return []

    matches = []
    seen = set()
    hidden_keys = owner._hidden_root_tree_keys_for_mode("JSON")

    def _add(path):
        if not isinstance(path, list) or not path:
            return
        key = tuple(path)
        if key in seen:
            return
        seen.add(key)
        matches.append(path)

    def _walk(value, path):
        if isinstance(value, dict):
            keys = list(value.keys())
            if not path:
                keys = sorted(keys, key=lambda raw: str(owner._tree_display_label_for_key(raw)).casefold())
            for key in keys:
                if not path and owner._normalize_root_tree_key(key) in hidden_keys:
                    continue
                child_path = path + [key]
                key_text = f"{key} {owner._tree_display_label_for_key(key)}".casefold()
                if needle in key_text:
                    _add(child_path)
                _walk(value.get(key), child_path)
            return

        if isinstance(value, list):
            labeler = owner._list_labelers.get(tuple(path))
            for idx, item in enumerate(value):
                child_path = path + [idx]
                if labeler:
                    label = str(labeler(idx, item))
                elif owner._is_database_table_rows_path(path):
                    label = str(owner._database_table_row_label(idx, item))
                else:
                    label = f"[{idx}]"
                if needle in label.casefold():
                    _add(child_path)
                _walk(item, child_path)
            return

        value_text = str(value).casefold() if value is not None else "none"
        if needle in value_text:
            if len(path) > 1:
                _add(path[:-1])
            _add(path)

    _walk(owner.data, [])
    return matches


def filter_json_find_matches(owner: Any, prior_matches: Any, query_lower: Any) -> Any:
    """Narrow existing matches for extended queries without rebuilding full-tree scan."""
    needle = str(query_lower or "").strip().casefold()
    if not needle:
        return []
    if not isinstance(prior_matches, list) or not prior_matches:
        return []
    cache = getattr(owner, "_json_find_path_token_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        setattr(owner, "_json_find_path_token_cache", cache)

    matches = []
    seen = set()
    for path in prior_matches:
        # Group sentinels are kept only when query still matches group text metadata.
        if isinstance(path, tuple) and len(path) == 3 and path[0] == "__group__":
            group_text = f"{path[1]} {path[2]}".casefold()
            if needle in group_text and path not in seen:
                seen.add(path)
                matches.append(path)
            continue
        if not isinstance(path, list) or not path:
            continue
        key = tuple(path)
        token_text = cache.get(key)
        if token_text is None:
            token_text = _path_token_text(owner, path)
            cache[key] = token_text
        if needle in token_text and key not in seen:
            seen.add(key)
            matches.append(path)
    return matches


def _json_find_anchor_path(path: list[Any]) -> list[Any]:
    """Clamp navigation path to first subcategory depth under the root key."""
    if len(path) <= 2:
        return list(path)
    return list(path[:2])


def normalize_json_find_navigation_matches(matches: Any) -> list[Any]:
    """Collapse deep JSON find matches into unique first-subcategory navigation anchors."""
    if not isinstance(matches, list):
        return []

    normalized: list[Any] = []
    seen: set[Any] = set()
    for ref in matches:
        if isinstance(ref, tuple) and len(ref) == 3 and ref[0] == "__group__":
            key = ("__group__", tuple(ref[1]) if isinstance(ref[1], list) else ref[1], ref[2])
            if key in seen:
                continue
            seen.add(key)
            normalized.append(ref)
            continue
        if not isinstance(ref, list) or not ref:
            continue
        anchor = _json_find_anchor_path(ref)
        key = tuple(anchor)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(anchor)
    return normalized


def _ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _path_token_text(owner: Any, path: list[Any]) -> str:
    value = _resolve_path_value(getattr(owner, "data", None), path)
    if value is _PATH_MISSING:
        return ""

    tokens = []
    tail = path[-1]
    if isinstance(tail, str):
        display = str(getattr(owner, "_tree_display_label_for_key", lambda raw: raw)(tail))
        tokens.append(str(tail))
        tokens.append(display)
    elif isinstance(tail, int):
        parent_path = path[:-1]
        labeler = getattr(owner, "_list_labelers", {}).get(tuple(parent_path))
        if labeler:
            try:
                tokens.append(str(labeler(tail, value)))
            except (TypeError, ValueError):
                tokens.append(f"[{tail}]")
        elif bool(getattr(owner, "_is_database_table_rows_path", lambda _path: False)(parent_path)):
            tokens.append(str(getattr(owner, "_database_table_row_label", lambda i, _v: f"[{i}]")(tail, value)))
        else:
            tokens.append(f"[{tail}]")

    if isinstance(value, (dict, list)):
        summary_fn = getattr(owner, "_find_search_value_summary", None)
        if callable(summary_fn):
            tokens.append(str(summary_fn(value)))
    elif value is None:
        tokens.append("none")
    else:
        tokens.append(str(value))

    return " ".join(tok for tok in tokens if tok).casefold()


_PATH_MISSING = object()


def _resolve_path_value(root: Any, path: list[Any]) -> Any:
    cursor = root
    for part in path:
        if isinstance(cursor, dict) and isinstance(part, str):
            if part not in cursor:
                return _PATH_MISSING
            cursor = cursor.get(part)
            continue
        if isinstance(cursor, list) and isinstance(part, int):
            if part < 0 or part >= len(cursor):
                return _PATH_MISSING
            cursor = cursor[part]
            continue
        return _PATH_MISSING
    return cursor


# --- Merged from json_find_nav_service.py ---
"""JSON find-navigation helpers for cross-root tree traversal behavior."""
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def collapse_previous_find_root_if_category_changed(owner: Any, next_item_id: Any) -> Any:
    """Collapse previous root when Find Next jumps to a different top-level category."""
    tree_widget = getattr(owner, "tree", None)
    if tree_widget is None:
        return
    if not next_item_id:
        return
    try:
        if not tree_widget.winfo_exists():
            return
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return

    def _root_item(item_id):
        current = item_id
        if not current:
            return ""
        while True:
            try:
                parent = tree_widget.parent(current)
            except EXPECTED_ERRORS as exc:
                _LOG.debug('expected_error', exc_info=exc)
                return current
            if not parent:
                return current
            current = parent

    try:
        next_root = _root_item(next_item_id)
        previous_root = str(getattr(owner, "_find_last_root_item", "") or "")
        if previous_root and next_root and previous_root != next_root:
            tree_widget.item(previous_root, open=False)
        owner._find_last_root_item = next_root
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return


# --- Merged from json_text_find_service.py ---
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
        _refresh_visible_json_find_matches(owner, text_widget, needle, active_start=start, active_end=end)
        _configure_json_find_tags(owner, text_widget)
        try:
            text_widget.tag_raise("find_next_match")
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
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


def _json_find_palette(owner: Any) -> tuple[str, str, str, str]:
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD") or "SIINDBAD").upper()
    if variant == "GLITCH":
        return ("#3d6b4d", "#ecfff2", "#254232", "#def8e7")
    if variant == "KAMUE":
        return ("#4f3f71", "#f3ecff", "#34274b", "#ebe1ff")
    return ("#2a5279", "#edf7ff", "#1a3a5b", "#dcefff")


def _json_find_palette_key(owner: Any) -> tuple[str, str, str, str]:
    return _json_find_palette(owner)


def _json_find_active_bg(owner: Any) -> str:
    return _json_find_palette(owner)[0]


def _json_find_active_fg(owner: Any) -> str:
    return _json_find_palette(owner)[1]


def _json_find_window_bg(owner: Any) -> str:
    return _json_find_palette(owner)[2]


def _json_find_window_fg(owner: Any) -> str:
    return _json_find_palette(owner)[3]


def _refresh_visible_json_find_matches(
    owner: Any,
    text_widget: Any,
    needle: str,
    *,
    active_start: str,
    active_end: str,
) -> None:
    if not needle:
        _clear_json_find_tags(owner, text_widget, clear_active=False)
        return
    try:
        visible_start = text_widget.index("@0,0")
        height = int(text_widget.winfo_height() or 0)
        if height <= 0:
            return
        visible_end = text_widget.index(f"@0,{max(1, height)}")
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return
    _clear_window_find_tag(text_widget)

    match_count = 0
    cursor = str(visible_start)
    max_visible_matches = 120
    while match_count < max_visible_matches:
        hit = text_widget.search(needle, cursor, stopindex=visible_end, nocase=1)
        if not hit:
            break
        hit_start = str(hit)
        hit_end = f"{hit_start}+{len(needle)}c"
        if not _index_range_equal(text_widget, hit_start, hit_end, active_start, active_end):
            text_widget.tag_add("find_next_window_match", hit_start, hit_end)
            match_count += 1
        cursor = hit_end

    _configure_json_find_window_tag(owner, text_widget)
    try:
        text_widget.tag_raise("find_next_match")
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)


def _configure_json_find_tags(owner: Any, text_widget: Any) -> None:
    _configure_json_find_active_tag(owner, text_widget)
    _configure_json_find_window_tag(owner, text_widget)


def _configure_json_find_active_tag(owner: Any, text_widget: Any) -> None:
    palette_key = _json_find_palette_key(owner)
    widget_changed = getattr(owner, "_json_find_tag_widget", None) is not text_widget
    palette_changed = getattr(owner, "_json_find_active_palette_key", None) != palette_key
    if not widget_changed and not palette_changed:
        return
    text_widget.tag_config(
        "find_next_match",
        background=_json_find_active_bg(owner),
        foreground=_json_find_active_fg(owner),
    )
    owner._json_find_tag_widget = text_widget
    owner._json_find_active_palette_key = palette_key


def _configure_json_find_window_tag(owner: Any, text_widget: Any) -> None:
    palette_key = _json_find_palette_key(owner)
    widget_changed = getattr(owner, "_json_find_window_tag_widget", None) is not text_widget
    palette_changed = getattr(owner, "_json_find_window_palette_key", None) != palette_key
    if not widget_changed and not palette_changed:
        return
    text_widget.tag_config(
        "find_next_window_match",
        background=_json_find_window_bg(owner),
        foreground=_json_find_window_fg(owner),
    )
    owner._json_find_window_tag_widget = text_widget
    owner._json_find_window_palette_key = palette_key


def _index_range_equal(text_widget: Any, a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    try:
        return bool(
            str(text_widget.index(a_start)) == str(text_widget.index(b_start))
            and str(text_widget.index(a_end)) == str(text_widget.index(b_end))
        )
    except EXPECTED_ERRORS:
        return bool(str(a_start) == str(b_start) and str(a_end) == str(b_end))


def _clear_window_find_tag(text_widget: Any) -> None:
    try:
        text_widget.tag_remove("find_next_window_match", "1.0", "end")
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)


def _clear_json_find_tags(owner: Any, text_widget: Any, *, clear_active: bool = True) -> None:
    if clear_active:
        try:
            text_widget.tag_remove("find_next_match", "1.0", "end")
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
    _clear_window_find_tag(text_widget)
    if clear_active:
        owner._json_find_last_query = ""


def clear_json_find_highlight_on_nav(owner: Any, event: Any) -> None:
    text_widget = getattr(owner, "text", None)
    if text_widget is None:
        return
    try:
        if not text_widget.winfo_exists():
            return
        x = getattr(event, "x", None)
        y = getattr(event, "y", None)
        if x is None or y is None:
            return
        click_index = text_widget.index(f"@{x},{y}")
        if not _index_in_tag_ranges(text_widget, "find_next_match", click_index) and not _index_in_tag_ranges(
            text_widget, "find_next_window_match", click_index
        ):
            return
        _clear_json_find_tags(owner, text_widget, clear_active=True)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)


def _index_in_tag_ranges(text_widget: Any, tag_name: str, index: str) -> bool:
    try:
        ranges = list(text_widget.tag_ranges(tag_name))
    except EXPECTED_ERRORS:
        return False
    if len(ranges) < 2:
        return False
    for pos in range(0, len(ranges), 2):
        start = ranges[pos]
        end = ranges[pos + 1]
        try:
            in_start = bool(text_widget.compare(index, ">=", start))
            in_end = bool(text_widget.compare(index, "<", end))
            if in_start and in_end:
                return True
        except EXPECTED_ERRORS:
            if str(index) >= str(start) and str(index) < str(end):
                return True
    return False


# --- Merged from json_find_orchestrator_service.py ---
"""JSON-mode Find Next orchestration helpers."""

from typing import Any
from core.domain_impl.json import json_navigation_core as json_find_service


def find_next(owner: Any, *, expected_errors: Any) -> None:
    if str(getattr(owner, "_editor_mode", "JSON")).upper() == "INPUT":
        owner._find_next_input_mode()
        return
    query = owner.find_entry.get().strip()
    if not query:
        owner.set_status("Find: enter text to search")
        return

    query_lower = query.lower()
    if query_lower != owner.last_find_query:
        build_matches_fn = getattr(owner, "_build_json_find_matches", None)
        filter_matches_fn = getattr(owner, "_filter_json_find_matches", None)
        prior_raw_matches = getattr(owner, "_json_find_raw_matches", None)
        if not isinstance(prior_raw_matches, list) or not prior_raw_matches:
            fallback_matches = getattr(owner, "find_matches", None)
            prior_raw_matches = fallback_matches if isinstance(fallback_matches, list) else None
        can_narrow_prior = bool(
            owner.last_find_query
            and query_lower.startswith(str(owner.last_find_query))
            and isinstance(prior_raw_matches, list)
            and prior_raw_matches
        )
        raw_matches: list[Any]
        if can_narrow_prior:
            if callable(filter_matches_fn):
                raw_matches = _ensure_list(filter_matches_fn(prior_raw_matches, query_lower))
            else:
                raw_matches = _ensure_list(
                    json_find_service.filter_json_find_matches(
                        owner,
                        prior_raw_matches,
                        query_lower,
                    )
                )
        elif callable(build_matches_fn):
            raw_matches = _ensure_list(build_matches_fn(query_lower))
        else:
            # Backward-compatible fallback for lightweight test doubles.
            if not owner._find_search_entries:
                owner._find_search_entries = owner._build_find_search_index()
            raw_matches = [entry[0] for entry in owner._find_search_entries if query_lower in entry[1]]
        owner._json_find_raw_matches = raw_matches
        owner.find_matches = normalize_json_find_navigation_matches(raw_matches)
        owner.find_index = 0
        owner.last_find_query = query_lower

    matches = owner.find_matches if isinstance(owner.find_matches, list) else []
    owner.find_matches = matches
    if not matches:
        owner.set_status(f'Find: no matches for "{query}"')
        return

    item_id = None
    total_matches = len(matches)
    attempts = total_matches
    while attempts > 0:
        match_ref = matches[owner.find_index]
        owner.find_index = (owner.find_index + 1) % total_matches
        if isinstance(match_ref, tuple) and len(match_ref) == 3 and match_ref[0] == "__group__":
            item_id = owner._ensure_tree_group_item_loaded(match_ref[1], match_ref[2])
        else:
            item_id = owner._ensure_tree_item_for_path(match_ref)
        if item_id is not None:
            break
        attempts -= 1
    if item_id is None:
        owner.set_status(f'Find: no accessible matches for "{query}"')
        owner._reset_find_state()
        return
    if str(getattr(owner, "_editor_mode", "JSON")).upper() == "JSON":
        collapse_fn = getattr(owner, "_collapse_previous_find_root_if_category_changed", None)
        if callable(collapse_fn):
            collapse_fn(item_id)
    owner._open_to_item(item_id)
    tree_widget = getattr(owner, "tree", None)
    if tree_widget is not None:
        try:
            focus_fn = getattr(tree_widget, "focus", None)
            if callable(focus_fn):
                focus_fn(item_id)
        except expected_errors:
            pass
        try:
            select_fn = getattr(tree_widget, "selection_set", None)
            if callable(select_fn):
                select_fn(item_id)
        except expected_errors:
            pass
        try:
            see_fn = getattr(tree_widget, "see", None)
            if callable(see_fn):
                see_fn(item_id)
        except expected_errors:
            pass
    owner.on_select(None)
    focus_match_fn = getattr(owner, "_focus_json_find_match", None)
    if callable(focus_match_fn):
        root = getattr(owner, "root", None)
        schedule_after_idle = getattr(root, "after_idle", None)
        if callable(schedule_after_idle):
            prior_after_id = getattr(owner, "_json_find_focus_after_id", None)
            cancel_after = getattr(root, "after_cancel", None)
            if prior_after_id is not None and callable(cancel_after):
                try:
                    cancel_after(prior_after_id)
                except expected_errors:
                    pass

            def _apply_focus() -> None:
                owner._json_find_focus_after_id = None
                try:
                    focus_match_fn(query)
                except expected_errors:
                    return

            try:
                owner._json_find_focus_after_id = schedule_after_idle(_apply_focus)
            except expected_errors:
                focus_match_fn(query)
        else:
            focus_match_fn(query)
    owner.set_status(f'Find: {owner.find_index}/{len(matches)}')

__all__ = [name for name in globals() if not name.startswith("__")]
