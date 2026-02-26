"""JSON-mode Find Next orchestration helpers."""

from typing import Any
from core.domain_impl.json import json_find_service


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
        can_narrow_prior = bool(
            owner.last_find_query
            and query_lower.startswith(str(owner.last_find_query))
            and isinstance(owner.find_matches, list)
            and owner.find_matches
        )
        if can_narrow_prior:
            if callable(filter_matches_fn):
                owner.find_matches = filter_matches_fn(owner.find_matches, query_lower)
            else:
                owner.find_matches = json_find_service.filter_json_find_matches(
                    owner,
                    owner.find_matches,
                    query_lower,
                )
        elif callable(build_matches_fn):
            owner.find_matches = build_matches_fn(query_lower)
        else:
            # Backward-compatible fallback for lightweight test doubles.
            if not owner._find_search_entries:
                owner._find_search_entries = owner._build_find_search_index()
            owner.find_matches = [entry[0] for entry in owner._find_search_entries if query_lower in entry[1]]
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
        focus_match_fn(query)
    owner.set_status(f'Find: {owner.find_index}/{len(matches)}')
