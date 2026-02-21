"""Mode-scoped tree policy helpers.

Keeps JSON and INPUT tree behavior split by policy while sharing one tree engine.
"""


def _normalize_mode(mode):
    return str(mode or "JSON").strip().upper()


def hidden_root_keys_for_mode(owner, mode=None):
    # JSON and INPUT can keep different hidden root lists without branching in UI code.
    use_mode = _normalize_mode(mode or getattr(owner, "_editor_mode", "JSON"))
    if use_mode == "INPUT":
        return set(getattr(owner, "HIDDEN_ROOT_TREE_KEYS_INPUT", set()))
    return set(getattr(owner, "HIDDEN_ROOT_TREE_KEYS_JSON", set()))


def is_input_mode_root_disabled(owner, path):
    # INPUT-only root disable list drives category-level lock messaging.
    if _normalize_mode(getattr(owner, "_editor_mode", "JSON")) != "INPUT":
        return False
    if not isinstance(path, list) or not path:
        return False
    root_key = owner._normalize_root_tree_key(path[0])
    return root_key in set(getattr(owner, "INPUT_MODE_DISABLED_ROOT_KEYS", set()))


def is_input_mode_tree_expand_blocked(owner, item_id):
    # INPUT-only no-expand list prevents expanding configured root categories.
    if _normalize_mode(getattr(owner, "_editor_mode", "JSON")) != "INPUT":
        return False
    path = getattr(owner, "item_to_path", {}).get(item_id)
    if not isinstance(path, list) or len(path) != 1:
        return False
    root_key = owner._normalize_root_tree_key(path[0])
    return root_key in set(getattr(owner, "INPUT_MODE_NO_EXPAND_ROOT_KEYS", set()))


def should_use_input_red_arrow_for_path(owner, path):
    # Red-arrow marker is INPUT-only; JSON always uses standard markers.
    if _normalize_mode(getattr(owner, "_editor_mode", "JSON")) != "INPUT":
        return False
    if not isinstance(path, list) or len(path) != 1:
        return False
    root_key = owner._normalize_root_tree_key(path[0])
    return root_key in set(getattr(owner, "INPUT_MODE_RED_ARROW_ROOT_KEYS", set()))
