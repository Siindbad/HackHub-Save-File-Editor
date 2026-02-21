"""Editor mode-switch helper policies.

Keeps JSON/INPUT mode refresh and tree-rebuild decisions isolated from UI wiring.
"""


def mode_switch_requires_tree_rebuild(owner, previous_mode, next_mode):
    # Rebuild only when mode root-hide policy changes to avoid unnecessary flicker.
    prev_hidden = owner._hidden_root_tree_keys_for_mode(previous_mode)
    next_hidden = owner._hidden_root_tree_keys_for_mode(next_mode)
    return prev_hidden != next_hidden


def can_skip_input_mode_refresh(owner, item_id, target_path):
    # Skip refresh only when item/path are unchanged and no forced refresh is pending.
    if bool(getattr(owner, "_input_mode_force_refresh", False)):
        return False
    last_item = getattr(owner, "_input_mode_last_render_item", None)
    last_key = getattr(owner, "_input_mode_last_render_path_key", None)
    next_key = owner._input_mode_path_key(target_path)
    return bool(item_id and item_id == last_item and next_key == last_key)
