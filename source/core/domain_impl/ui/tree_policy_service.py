"""Mode-scoped tree policy helpers.

Keeps JSON and INPUT tree behavior split by policy while sharing one tree engine.
"""
from typing import Any


def _normalize_mode(mode):
    return str(mode or "JSON").strip().upper()


def hidden_root_keys_for_mode(owner: Any, mode: Any=None) -> Any:
    # JSON and INPUT can keep different hidden root lists without branching in UI code.
    use_mode = _normalize_mode(mode or getattr(owner, "_editor_mode", "JSON"))
    match use_mode:
        case "INPUT":
            return set(getattr(owner, "HIDDEN_ROOT_TREE_KEYS_INPUT", set()))
        case _:
            return set(getattr(owner, "HIDDEN_ROOT_TREE_KEYS_JSON", set()))


def is_input_mode_root_disabled(owner: Any, path: Any) -> Any:
    # INPUT-only root disable list drives category-level lock messaging.
    if _normalize_mode(getattr(owner, "_editor_mode", "JSON")) != "INPUT":
        return False
    if not isinstance(path, list) or not path:
        return False
    root_key = owner._normalize_root_tree_key(path[0])
    return root_key in set(getattr(owner, "INPUT_MODE_DISABLED_ROOT_KEYS", set()))


def is_input_mode_tree_expand_blocked(owner: Any, item_id: Any) -> Any:
    # INPUT-only no-expand policy:
    # - configured root categories stay collapsed
    # - configured Network subgroup buckets stay collapsed
    if _normalize_mode(getattr(owner, "_editor_mode", "JSON")) != "INPUT":
        return False
    path = getattr(owner, "item_to_path", {}).get(item_id)
    if isinstance(path, list) and len(path) == 1:
        root_key = owner._normalize_root_tree_key(path[0])
        if root_key in set(getattr(owner, "INPUT_MODE_NO_EXPAND_ROOT_KEYS", set())):
            return True
    if isinstance(path, tuple) and len(path) == 3 and path[0] == "__group__":
        list_path = path[1] if isinstance(path[1], list) else []
        group_name = str(path[2] or "").strip().casefold()
        if list_path and owner._normalize_root_tree_key(list_path[0]) == "network":
            return group_name in set(getattr(owner, "INPUT_MODE_NETWORK_NO_EXPAND_GROUP_KEYS", set()))
    return False


def should_use_input_red_arrow_for_path(owner: Any, path: Any) -> Any:
    # Red-arrow marker is INPUT-only; JSON always uses standard markers.
    if _normalize_mode(getattr(owner, "_editor_mode", "JSON")) != "INPUT":
        return False
    if isinstance(path, list) and len(path) == 1:
        root_key = owner._normalize_root_tree_key(path[0])
        return root_key in set(getattr(owner, "INPUT_MODE_RED_ARROW_ROOT_KEYS", set()))
    if isinstance(path, tuple) and len(path) == 3 and path[0] == "__group__":
        list_path = path[1] if isinstance(path[1], list) else []
        group_name = str(path[2] or "").strip().casefold()
        if list_path and owner._normalize_root_tree_key(list_path[0]) == "network":
            return group_name in set(getattr(owner, "INPUT_MODE_RED_ARROW_NETWORK_GROUP_KEYS", set()))
    return False


def is_network_group_hidden_for_mode(owner: Any, list_path: Any, group_name: Any, mode: Any=None) -> Any:
    # INPUT-only hide policy for Network subgroup buckets.
    use_mode = _normalize_mode(mode or getattr(owner, "_editor_mode", "JSON"))
    if use_mode != "INPUT":
        return False
    root_path = list_path if isinstance(list_path, list) else []
    if not root_path or owner._normalize_root_tree_key(root_path[0]) != "network":
        return False
    group_key = str(group_name or "").strip().casefold()
    return group_key in set(getattr(owner, "INPUT_MODE_NETWORK_HIDDEN_GROUP_KEYS", set()))
