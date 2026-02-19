import copy


def is_network_list(path, value, network_types_set):
    if path != ["Network"]:
        return False
    if not value:
        return False
    return all(
        isinstance(item, dict) and item.get("type") in network_types_set
        for item in value
    )


def network_context(path, value_getter, network_types_set):
    if len(path) < 2:
        return None
    if path[0] != "Network":
        return None
    idx = path[1]
    if not isinstance(idx, int):
        return None
    try:
        node = value_getter(["Network", idx])
    except Exception:
        return None
    if not isinstance(node, dict):
        return None
    node_type = node.get("type")
    if node_type in network_types_set:
        return {"type": node_type, "path": ["Network", idx]}
    return None


def edit_allowed_payload(path, current_value, new_value, find_first_dict_key_change, format_path_for_display):
    issue = find_first_dict_key_change(current_value, new_value, list(path or []))
    if not issue:
        return {"allowed": True}
    issue_path = issue.get("path") or []
    path_label = format_path_for_display(issue_path) if issue_path else "root"
    if issue.get("type_changed"):
        detail = "Object structure changed. Renaming/removing object keys is blocked for safety."
    else:
        missing = issue.get("missing") or []
        added = issue.get("added") or []
        parts = []
        if missing:
            parts.append(f"removed: {', '.join(missing[:4])}")
        if added:
            parts.append(f"added: {', '.join(added[:4])}")
        detail = "Key rename/change detected"
        if parts:
            detail = f"{detail} ({'; '.join(parts)})"
    return {
        "allowed": False,
        "path_label": path_label,
        "detail": detail,
    }


# Global JSON-lock policy registry:
# - add new category lockouts here
# - editor lock/highlight/restore logic automatically uses this table
LOCK_POLICY_REGISTRY = (
    {
        "id": "appstore_progression",
        "root_names": ("AppStore", "App.Store"),
        "locked_keys": ("unlockedMarketItems", "purchasedItems"),
        "detail_template": "`{field}` is locked in JSON view to protect core AppStore progression values.",
        "status_blocked": "Blocked: locked AppStore field cannot be edited in JSON mode.",
        "status_restored": "Auto-fixed: protected AppStore field restored.",
        # Keep subcategory JSON white; only root/object view shows orange key labels.
        "highlight_root_only": True,
    },
    {
        "id": "computer_identity",
        "root_names": ("Computer",),
        "locked_keys": (
            "id",
            "network",
            "credentials",
            "username",
            "password",
            "backgrounds",
            "lockScreen",
            "desktop",
            "terminal",
            "terminalBackgroundOpacity",
            "terminalBackground",
            "colors",
            "titlebar1",
            "titlebar2",
            "window",
            "controlbar",
            "desktopIcon",
            "taskbar",
            "theme",
            "vpn",
            "connection",
            "list",
            "configs",
            "connectedSubnetIp",
        ),
        "detail_template": "`{field}` is locked in JSON view to protect core Computer link values.",
        "status_blocked": "Blocked: locked Computer field cannot be edited in JSON mode.",
        "status_restored": "Auto-fixed: protected Computer field restored.",
        # Keep subcategory JSON white; only root/object view shows orange key labels.
        "highlight_root_only": True,
    },
    {
        "id": "bank_financial_core",
        "root_names": ("Bank",),
        "locked_keys": (
            "accounts",
            "creditCards",
            "disallowedTransactions",
            "possibleTransactions",
            "transactions",
            "id",
            "iban",
            "accountId",
            "accountName",
            "balance",
            "email",
            "firstName",
            "fullName",
            "isMine",
            "lastName",
            "password",
            "phone",
            "provider",
            "amount",
            "description",
            "from",
            "to",
            "transactionAt",
            "name",
        ),
        "detail_template": "`{field}` is locked in JSON view to protect core Bank data integrity.",
        "status_blocked": "Blocked: locked Bank field cannot be edited in JSON mode.",
        "status_restored": "Auto-fixed: protected Bank field restored.",
        # Keep subcategory JSON white; only root/object view shows orange key labels.
        "highlight_root_only": True,
    },
)


def _normalize_root_key(value):
    text = str(value or "").strip().casefold()
    if not text:
        return ""
    return "".join(ch for ch in text if ch.isalnum())


def _normalize_lookup_key(value):
    return str(value or "").strip().casefold()


def _compile_policy(raw):
    root_names = tuple(raw.get("root_names") or ())
    locked_keys = tuple(raw.get("locked_keys") or ())
    root_lookup = {_normalize_root_key(name): str(name) for name in root_names}
    locked_lookup = {_normalize_lookup_key(name): str(name) for name in locked_keys}
    return {
        "id": str(raw.get("id") or "").strip(),
        "root_names": root_names,
        "locked_keys": locked_keys,
        "root_lookup": root_lookup,
        "locked_lookup": locked_lookup,
        "detail_template": str(raw.get("detail_template") or "").strip(),
        "status_blocked": str(raw.get("status_blocked") or "").strip(),
        "status_restored": str(raw.get("status_restored") or "").strip(),
        "highlight_root_only": bool(raw.get("highlight_root_only", False)),
    }


_LOCK_POLICIES = tuple(_compile_policy(item) for item in LOCK_POLICY_REGISTRY)


def _policy_by_id(policy_id):
    target = str(policy_id or "").strip()
    for policy in _LOCK_POLICIES:
        if policy.get("id") == target:
            return policy
    return None


def _policy_for_root_value(root_value):
    key = _normalize_root_key(root_value)
    if not key:
        return None
    for policy in _LOCK_POLICIES:
        if key in policy.get("root_lookup", {}):
            return policy
    return None


def lock_policy_for_path(path):
    parts = list(path or [])
    if not parts:
        return None
    return _policy_for_root_value(parts[0])


def _canonical_locked_key_for_policy(policy, key_value):
    if not policy:
        return None
    return policy.get("locked_lookup", {}).get(_normalize_lookup_key(key_value))


def _locked_segment_for_parts(policy, parts):
    if not policy:
        return None, None
    segments = list(parts or [])
    if len(segments) < 2:
        return None, None
    # Prefer the most-specific segment nearest the edited node.
    for segment in reversed(segments[1:]):
        canonical = _canonical_locked_key_for_policy(policy, segment)
        if canonical is not None:
            return canonical, str(segment)
    return None, None


def is_locked_root_path(path):
    parts = list(path or [])
    if len(parts) != 1:
        return False
    return lock_policy_for_path(parts) is not None


def is_locked_field_path(path):
    parts = list(path or [])
    if len(parts) < 2:
        return False
    policy = lock_policy_for_path(parts)
    if policy is None:
        return False
    canonical, _matched = _locked_segment_for_parts(policy, parts)
    return canonical is not None


def locked_highlight_fields_for_path(path):
    parts = list(path or [])
    if not parts:
        return ()
    policy = lock_policy_for_path(parts)
    if policy is None:
        return ()
    if len(parts) == 1:
        return tuple(policy.get("locked_keys", ()))
    if is_locked_field_path(parts) and not policy.get("highlight_root_only", False):
        canonical = _canonical_locked_key_for_policy(policy, parts[1])
        if canonical:
            return (canonical,)
    return ()


def _dict_get_ignore_case(data, key_name):
    if not isinstance(data, dict):
        return False, None, None
    target = _normalize_lookup_key(key_name)
    for key, value in data.items():
        if _normalize_lookup_key(key) == target:
            return True, key, value
    return False, None, None


def _find_policy_container(data, policy):
    if not isinstance(data, dict) or not policy:
        return None, None
    root_lookup = policy.get("root_lookup", {})
    for key, value in data.items():
        if _normalize_root_key(key) in root_lookup and isinstance(value, dict):
            return key, value
    return None, None


def _copy_json_value(value):
    try:
        return copy.deepcopy(value)
    except Exception:
        return value


def _find_locked_change_for_policy(policy, path, current_value, new_value):
    parts = list(path or [])
    if policy is None:
        return None
    if parts:
        path_policy = lock_policy_for_path(parts)
        if path_policy is None or path_policy.get("id") != policy.get("id"):
            return None
        if len(parts) >= 2:
            canonical, matched = _locked_segment_for_parts(policy, parts)
            if canonical is None:
                return None
            if current_value != new_value:
                return {
                    "path": [parts[0], canonical],
                    "field": str(matched or canonical),
                    "policy": policy,
                }
            return None
        old_obj = current_value if isinstance(current_value, dict) else {}
        new_obj = new_value if isinstance(new_value, dict) else {}
        for field_name in policy.get("locked_keys", ()):
            old_found, old_key, old_field = _dict_get_ignore_case(old_obj, field_name)
            new_found, new_key, new_field = _dict_get_ignore_case(new_obj, field_name)
            if old_field != new_field:
                field_display = str(new_key if new_found else (old_key if old_found else field_name))
                return {
                    "path": [parts[0], field_name],
                    "field": field_display,
                    "policy": policy,
                }
        return None

    old_root_key, old_obj = _find_policy_container(current_value, policy)
    new_root_key, new_obj = _find_policy_container(new_value, policy)
    old_obj = old_obj if isinstance(old_obj, dict) else {}
    new_obj = new_obj if isinstance(new_obj, dict) else {}
    root_label = old_root_key if old_root_key is not None else (new_root_key or policy["root_names"][0])
    for field_name in policy.get("locked_keys", ()):
        old_found, old_key, old_field = _dict_get_ignore_case(old_obj, field_name)
        new_found, new_key, new_field = _dict_get_ignore_case(new_obj, field_name)
        if old_field != new_field:
            field_display = str(new_key if new_found else (old_key if old_found else field_name))
            return {
                "path": [root_label, field_name],
                "field": field_display,
                "policy": policy,
            }
    return None


def find_locked_json_change(path, current_value, new_value):
    for policy in _LOCK_POLICIES:
        issue = _find_locked_change_for_policy(policy, path, current_value, new_value)
        if issue:
            return issue
    return None


def _restore_locked_fields_for_policy_dict(policy, current_obj, edited_obj):
    if not isinstance(edited_obj, dict):
        return False, edited_obj
    fixed = _copy_json_value(edited_obj)
    changed = False
    old_obj = current_obj if isinstance(current_obj, dict) else {}
    for field_name in policy.get("locked_keys", ()):
        old_found, old_key, old_field = _dict_get_ignore_case(old_obj, field_name)
        new_found, new_key, new_field = _dict_get_ignore_case(fixed, field_name)
        if old_field == new_field:
            continue
        if old_found:
            target_key = new_key if new_found else (old_key if old_key is not None else field_name)
            fixed[target_key] = _copy_json_value(old_field)
            changed = True
    return changed, fixed


def restore_locked_json_edit(path, current_value, new_value):
    parts = list(path or [])
    if parts:
        policy = lock_policy_for_path(parts)
        if policy is None:
            return False, new_value
        if is_locked_field_path(parts):
            if current_value == new_value:
                return False, new_value
            return True, _copy_json_value(current_value)
        if len(parts) == 1:
            return _restore_locked_fields_for_policy_dict(policy, current_value, new_value)
        return False, new_value

    if not (isinstance(current_value, dict) and isinstance(new_value, dict)):
        return False, new_value
    fixed_root = _copy_json_value(new_value)
    changed_any = False
    for policy in _LOCK_POLICIES:
        old_root, old_obj = _find_policy_container(current_value, policy)
        new_root, new_obj = _find_policy_container(fixed_root, policy)
        if new_root is None or not isinstance(new_obj, dict):
            continue
        changed, fixed_obj = _restore_locked_fields_for_policy_dict(policy, old_obj, new_obj)
        if changed:
            fixed_root[new_root] = fixed_obj
            changed_any = True
    return changed_any, fixed_root


def locked_json_edit_payload(path, current_value, new_value, format_path_for_display):
    issue = find_locked_json_change(path, current_value, new_value)
    if not issue:
        return {"allowed": True}
    issue_path = issue.get("path") or []
    path_label = format_path_for_display(issue_path) if issue_path else "root"
    field_name = str(issue.get("field") or (issue_path[-1] if issue_path else "value"))
    policy = issue.get("policy") or {}
    detail_template = str(policy.get("detail_template") or "").strip()
    detail = detail_template.format(field=field_name, path=path_label) if detail_template else ""
    return {
        "allowed": False,
        "path_label": path_label,
        "field": field_name,
        "detail": detail,
        "policy_id": policy.get("id", ""),
        "status_blocked": str(policy.get("status_blocked") or "").strip(),
        "status_restored": str(policy.get("status_restored") or "").strip(),
    }


# Backwards-compatible wrappers for existing AppStore calls.
def is_appstore_root_path(path):
    policy = lock_policy_for_path(path)
    return bool(policy and policy.get("id") == "appstore_progression" and len(list(path or [])) == 1)


def is_appstore_locked_path(path):
    parts = list(path or [])
    policy = lock_policy_for_path(parts)
    if not (policy and policy.get("id") == "appstore_progression"):
        return False
    if len(parts) < 2:
        return False
    canonical, _matched = _locked_segment_for_parts(policy, parts)
    return canonical is not None


def find_locked_appstore_change(path, current_value, new_value):
    policy = _policy_by_id("appstore_progression")
    issue = _find_locked_change_for_policy(policy, path, current_value, new_value)
    if not issue:
        return None
    return {
        "path": issue.get("path") or [],
        "field": issue.get("field", ""),
    }
