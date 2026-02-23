"""Editor mode-switch helper policies.

Keeps JSON/INPUT mode refresh and tree-rebuild decisions isolated from UI wiring.
"""
from typing import Any


def mode_switch_requires_tree_rebuild(owner: Any, previous_mode: Any, next_mode: Any) -> Any:
    # Rebuild when mode-dependent visibility policy changes.
    # This includes root-hide lists and INPUT-only hidden Network subgroup buckets.
    prev_hidden = owner._hidden_root_tree_keys_for_mode(previous_mode)
    next_hidden = owner._hidden_root_tree_keys_for_mode(next_mode)
    if prev_hidden != next_hidden:
        return True

    prev_mode = str(previous_mode or "JSON").strip().upper()
    next_mode = str(next_mode or "JSON").strip().upper()
    prev_network_hidden = set(getattr(owner, "INPUT_MODE_NETWORK_HIDDEN_GROUP_KEYS", set())) if prev_mode == "INPUT" else set()
    next_network_hidden = set(getattr(owner, "INPUT_MODE_NETWORK_HIDDEN_GROUP_KEYS", set())) if next_mode == "INPUT" else set()
    return prev_network_hidden != next_network_hidden


def can_skip_input_mode_refresh(owner: Any, item_id: Any, target_path: Any) -> Any:
    # Skip refresh only when item/path are unchanged and no forced refresh is pending.
    if bool(getattr(owner, "_input_mode_force_refresh", False)):
        return False
    last_item = getattr(owner, "_input_mode_last_render_item", None)
    last_key = getattr(owner, "_input_mode_last_render_path_key", None)
    next_key = owner._input_mode_path_key(target_path)
    return bool(item_id and item_id == last_item and next_key == last_key)
