"""Mode-scoped tree policy helpers.

Keeps JSON and INPUT tree behavior split by policy while sharing one tree engine.
"""
from typing import Any
from core.exceptions import EXPECTED_ERRORS


def _normalize_mode(mode):
    return str(mode or "JSON").strip().upper()


def _device_domain_name(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    name = value.get("name")
    if not name:
        domain = value.get("domain")
        if isinstance(domain, dict):
            name = domain.get("name")
    return str(name or "")


def _network_device_blue_and_interpol_anchor_indices(owner: Any, root_token: Any) -> tuple[int | None, int | None]:
    try:
        network = owner._get_value([root_token])
    except EXPECTED_ERRORS:
        return None, None
    if not isinstance(network, list):
        return None, None
    first_subdomain_index: int | None = None
    blue_anchor_index: int | None = None
    for idx, item in enumerate(network):
        if not isinstance(item, dict):
            continue
        if str(item.get("type", "")).strip().upper() != "DEVICE":
            continue
        row_domain = _device_domain_name(item).strip().casefold()
        if row_domain == "thebluetable.com":
            blue_anchor_index = idx
            break
        if first_subdomain_index is None and row_domain.endswith(".thebluetable.com"):
            first_subdomain_index = idx
    if blue_anchor_index is None:
        blue_anchor_index = first_subdomain_index
    interpol_anchor_index: int | None = None
    if blue_anchor_index is not None:
        for idx in range(int(blue_anchor_index) + 1, len(network)):
            item = network[idx]
            if not isinstance(item, dict):
                continue
            if str(item.get("type", "")).strip().upper() == "DEVICE":
                interpol_anchor_index = idx
                break
    return blue_anchor_index, interpol_anchor_index


def _is_input_bcc_domains_locked_subcategory_path(owner: Any, path: Any) -> bool:
    if _normalize_mode(getattr(owner, "_editor_mode", "JSON")) != "INPUT":
        return False
    if not isinstance(path, list) or len(path) != 2:
        return False
    if owner._normalize_root_tree_key(path[0]) != "network":
        return False
    if not isinstance(path[1], int):
        return False
    try:
        value = owner._get_value(path)
    except EXPECTED_ERRORS:
        return False
    if not isinstance(value, dict):
        return False
    if str(value.get("type", "")).strip().upper() != "DEVICE":
        return False
    ip = str(value.get("ip", "") or "").strip()
    if ip != "193.8.64.214":
        return False
    return _device_domain_name(value).strip().casefold() == "bcc.com"


def _is_input_blue_table_locked_subcategory_path(owner: Any, path: Any) -> bool:
    if _normalize_mode(getattr(owner, "_editor_mode", "JSON")) != "INPUT":
        return False
    if not isinstance(path, list) or len(path) != 2:
        return False
    if owner._normalize_root_tree_key(path[0]) != "network":
        return False
    if not isinstance(path[1], int):
        return False
    try:
        value = owner._get_value(path)
    except EXPECTED_ERRORS:
        return False
    if not isinstance(value, dict):
        return False
    if str(value.get("type", "")).strip().upper() != "DEVICE":
        return False
    domain_name = _device_domain_name(value).strip().casefold()
    if not domain_name or (domain_name != "thebluetable.com" and not domain_name.endswith(".thebluetable.com")):
        return False
    anchor_index, _interpol_anchor = _network_device_blue_and_interpol_anchor_indices(owner, path[0])
    return anchor_index is not None and int(path[1]) == int(anchor_index)


def _is_input_interpol_locked_subcategory_path(owner: Any, path: Any) -> bool:
    if _normalize_mode(getattr(owner, "_editor_mode", "JSON")) != "INPUT":
        return False
    if not isinstance(path, list) or len(path) != 2:
        return False
    if owner._normalize_root_tree_key(path[0]) != "network":
        return False
    if not isinstance(path[1], int):
        return False
    try:
        value = owner._get_value(path)
    except EXPECTED_ERRORS:
        return False
    if not isinstance(value, dict):
        return False
    if str(value.get("type", "")).strip().upper() != "DEVICE":
        return False
    _blue_anchor, interpol_anchor = _network_device_blue_and_interpol_anchor_indices(owner, path[0])
    return interpol_anchor is not None and int(path[1]) == int(interpol_anchor)


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
    if isinstance(path, list) and len(path) == 2:
        is_locked_database_subcategory = getattr(owner, "_is_input_database_locked_subcategory_path", None)
        if callable(is_locked_database_subcategory):
            if bool(is_locked_database_subcategory(path)):
                return True
        if _is_input_bcc_domains_locked_subcategory_path(owner, path):
            return True
        if _is_input_blue_table_locked_subcategory_path(owner, path):
            return True
        if _is_input_interpol_locked_subcategory_path(owner, path):
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
    if isinstance(path, list) and len(path) == 2:
        is_locked_database_subcategory = getattr(owner, "_is_input_database_locked_subcategory_path", None)
        if callable(is_locked_database_subcategory):
            if bool(is_locked_database_subcategory(path)):
                return True
        if _is_input_bcc_domains_locked_subcategory_path(owner, path):
            return True
        if _is_input_blue_table_locked_subcategory_path(owner, path):
            return True
        if _is_input_interpol_locked_subcategory_path(owner, path):
            return True
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
