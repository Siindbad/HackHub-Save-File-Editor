import copy
import difflib


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
    missing = issue.get("missing") or []
    added = issue.get("added") or []
    path_label = format_path_for_display(issue_path) if issue_path else "root"
    recommended_name = ""
    if missing:
        recommended_name = str(missing[0] or "").strip()
    if not recommended_name and issue_path:
        tail = issue_path[-1]
        if isinstance(tail, str):
            recommended_name = str(tail).strip()
    if not recommended_name and added:
        recommended_name = str(added[0] or "").strip()
    if issue.get("type_changed"):
        detail = "Object structure changed. Renaming/removing object keys is blocked for safety."
    else:
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
        "recommended_name": recommended_name,
        "entered_name": str(added[0] or "").strip() if added else "",
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
    {
        "id": "bcc_news_core",
        "root_names": ("BCC.News",),
        "locked_keys": (
            "id",
            "title",
            "locale",
            "data",
            "editor",
            "hotel",
            "content",
            "image",
        ),
        # Display-only root highlights (orange) that should not imply edit blocking.
        "highlight_keys": (
            "id",
            "title",
            "locale",
            "data",
            "editor",
            "hotel",
            "content",
            "image",
            "news",
        ),
        "detail_template": "`{field}` is locked in JSON view to protect core BCC.News values.",
        "status_blocked": "Blocked: locked BCC.News field cannot be edited in JSON mode.",
        "status_restored": "Auto-fixed: protected BCC.News field restored.",
        # Only treat direct child keys under BCC.News as lock-match candidates.
        "direct_child_lock_only": True,
        # Keep subcategory JSON white; only root/object view shows orange key labels.
        "highlight_root_only": True,
    },
    {
        "id": "browser_session_identity",
        "root_names": ("Browser.Session",),
        "locked_keys": (
            "twotter",
            "id",
            "name",
            "surname",
            "username",
            "avatar",
            "banner",
            "joinedAt",
            "followers",
            "following",
            "password",
            "isMine",
            "lcb",
            "gomail",
            "fullName",
            "email",
            "phone",
            "provider",
        ),
        "detail_template": "`{field}` is locked in JSON view to protect core Browser.Session values.",
        "status_blocked": "Blocked: locked Browser.Session field cannot be edited in JSON mode.",
        "status_restored": "Auto-fixed: protected Browser.Session field restored.",
        # Keep subcategory JSON white; only root/object view shows orange key labels.
        "highlight_root_only": True,
    },
    {
        "id": "database_core_records",
        "root_names": ("Database",),
        "locked_keys": (
            "id",
            "host",
            "user",
            "password",
            "tables",
            "users",
            "customers",
            "Grades",
            "student",
            "value",
            "type",
            "Maths",
            "Physics",
            "editable",
            "Chemistry",
            "OOP",
            "History",
            "Geography",
            "Calculus",
            "name",
            "email",
            "job",
        ),
        # Optional value-lock rules for non-key-level protection:
        # if current value matches one of these literals, edits are blocked/restored.
        "locked_value_rules": (
            {"field": "type", "values": ("string", "number")},
        ),
        "detail_template": "`{field}` is locked in JSON view to protect core Database values.",
        "status_blocked": "Blocked: locked Database field cannot be edited in JSON mode.",
        "status_restored": "Auto-fixed: protected Database field restored.",
        # Keep subcategory JSON white; only root/object view shows orange key labels.
        "highlight_root_only": True,
    },
    {
        "id": "esc_menu_visibility",
        "root_names": ("Esc.Menu",),
        "locked_keys": (
            "visible",
        ),
        "detail_template": "`{field}` is locked in JSON view to protect Esc.Menu visibility behavior.",
        "status_blocked": "Blocked: locked Esc.Menu field cannot be edited in JSON mode.",
        "status_restored": "Auto-fixed: protected Esc.Menu field restored.",
        # Keep subcategory JSON white; only root/object view shows orange key labels.
        "highlight_root_only": True,
    },
    {
        "id": "files_category_core",
        "root_names": ("Files",),
        "locked_keys": (
            "id",
            "name",
            "isFolder",
            "root",
            "position",
            "open",
            "shortcut",
            "parent",
            "remote",
            "locked",
            "hashed",
            "data",
            "size",
            "type",
            "description",
            "date",
            "codex",
            "extension",
            "wordCount",
            "kId",
            "credential_harvester",
            "cmd",
            "Room",
            "Firstname",
            "Lastname",
            "locale",
            "password",
            "ip",
            "targetIp",
            "targetPort",
            "fromIp",
            "user",
            "online",
            "username",
            "t",
            "lastConnectionLogId",
            "deletable",
            "email",
            "address",
            "acceptReverseTCP",
            "readonly",
        ),
        "detail_template": "`{field}` is locked in JSON view to protect core Files category values.",
        "status_blocked": "Blocked: locked Files field cannot be edited in JSON mode.",
        "status_restored": "Auto-fixed: protected Files field restored.",
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


def _compile_locked_value_rule(raw_rule):
    if not isinstance(raw_rule, dict):
        return None
    field_name = str(raw_rule.get("field") or "").strip()
    if not field_name:
        return None
    values = tuple(raw_rule.get("values") or ())
    if not values:
        return None
    return {
        "field": field_name,
        "field_lookup": _normalize_lookup_key(field_name),
        "values": values,
        # Default strict string matching; set ignore_case=True per rule if needed.
        "ignore_case": bool(raw_rule.get("ignore_case", False)),
    }


def _compile_locked_value_rules(raw_rules):
    compiled = []
    for raw_rule in tuple(raw_rules or ()):
        item = _compile_locked_value_rule(raw_rule)
        if item:
            compiled.append(item)
    return tuple(compiled)


def _value_matches_locked_rule(rule, value):
    if rule is None:
        return False
    values = tuple(rule.get("values") or ())
    if not values:
        return False
    ignore_case = bool(rule.get("ignore_case", False))
    if isinstance(value, str):
        if ignore_case:
            want = _normalize_lookup_key(value)
            return any(isinstance(item, str) and _normalize_lookup_key(item) == want for item in values)
        return any(isinstance(item, str) and item == value for item in values)
    return any(item == value for item in values)


def _locked_value_rule_for_parts(policy, parts):
    if not policy:
        return None, None
    rules = tuple(policy.get("locked_value_rules") or ())
    if not rules:
        return None, None
    segments = list(parts or [])
    if len(segments) < 2:
        return None, None
    for segment in reversed(segments[1:]):
        lookup = _normalize_lookup_key(segment)
        for rule in rules:
            if lookup == rule.get("field_lookup", ""):
                return rule, str(segment)
    return None, None


def _compile_policy(raw):
    root_names = tuple(raw.get("root_names") or ())
    locked_keys = tuple(raw.get("locked_keys") or ())
    # Highlight keys may include display-only root labels that are not enforced locks.
    highlight_keys = tuple(raw.get("highlight_keys") or locked_keys)
    root_lookup = {_normalize_root_key(name): str(name) for name in root_names}
    locked_lookup = {_normalize_lookup_key(name): str(name) for name in locked_keys}
    return {
        "id": str(raw.get("id") or "").strip(),
        "root_names": root_names,
        "locked_keys": locked_keys,
        "highlight_keys": highlight_keys,
        "root_lookup": root_lookup,
        "locked_lookup": locked_lookup,
        "locked_value_rules": _compile_locked_value_rules(raw.get("locked_value_rules")),
        "detail_template": str(raw.get("detail_template") or "").strip(),
        "status_blocked": str(raw.get("status_blocked") or "").strip(),
        "status_restored": str(raw.get("status_restored") or "").strip(),
        # 0/1 policy toggle: when enabled, only first child under root is lock-matched.
        "direct_child_lock_only": bool(raw.get("direct_child_lock_only", False)),
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
    if policy.get("direct_child_lock_only", False):
        # Direct-child lock scope: only the first child under the selected category root
        # is treated as lock-bound for edit blocking in JSON mode.
        segment = segments[1]
        canonical = _canonical_locked_key_for_policy(policy, segment)
        if canonical is not None:
            return canonical, str(segment)
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
        return tuple(policy.get("highlight_keys", ()))
    if is_locked_field_path(parts) and not policy.get("highlight_root_only", False):
        canonical = _canonical_locked_key_for_policy(policy, parts[1])
        if canonical:
            return (canonical,)
    return ()


def locked_highlight_value_rules_for_path(path):
    parts = list(path or [])
    if not parts:
        return ()
    policy = lock_policy_for_path(parts)
    if policy is None:
        return ()
    rules = tuple(policy.get("locked_value_rules", ()))
    if not rules:
        return ()
    if len(parts) == 1:
        return rules
    if not policy.get("highlight_root_only", False):
        rule, _matched = _locked_value_rule_for_parts(policy, parts)
        if rule is not None:
            return (rule,)
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


def _replace_key_preserve_order(data, old_key, new_key, new_value):
    # Keep restored locked keys anchored to their edited location instead of appending to dict tail.
    if not isinstance(data, dict):
        return data
    if old_key not in data:
        data[new_key] = new_value
        return data
    replaced = {}
    for key, value in data.items():
        if key == old_key:
            replaced[new_key] = new_value
        else:
            replaced[key] = value
    data.clear()
    data.update(replaced)
    return data


def _find_renamed_locked_key_candidate(old_obj, edited_obj, field_name, old_key):
    # Rename-recovery helper: when a protected key is typo-renamed, remove that typo key on restore.
    if not isinstance(old_obj, dict) or not isinstance(edited_obj, dict):
        return None
    old_lookup = {_normalize_lookup_key(key) for key in old_obj.keys()}
    target_name = str(old_key if old_key is not None else field_name)
    target_lookup = _normalize_lookup_key(target_name)
    if not target_lookup:
        return None

    best_key = None
    best_score = 0.0
    for key in edited_obj.keys():
        key_text = str(key)
        key_lookup = _normalize_lookup_key(key_text)
        if not key_lookup or key_lookup == target_lookup:
            continue
        # Only consider new/renamed keys, not keys that already existed in the original object.
        if key_lookup in old_lookup:
            continue
        score = difflib.SequenceMatcher(a=target_lookup, b=key_lookup).ratio()
        if score > best_score:
            best_key = key
            best_score = score
    # Keep threshold conservative so unrelated new keys remain untouched.
    if best_key is not None and best_score >= 0.78:
        return best_key
    return None


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
                value_rule, value_field = _locked_value_rule_for_parts(policy, parts)
                if value_rule is None:
                    return None
                if current_value != new_value and _value_matches_locked_rule(value_rule, current_value):
                    field_display = str(value_field or value_rule.get("field") or "value")
                    return {
                        "path": [parts[0], str(value_rule.get("field") or field_display)],
                        "field": field_display,
                        "policy": policy,
                    }
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
        for rule in policy.get("locked_value_rules", ()):
            field_name = str(rule.get("field") or "").strip()
            if not field_name:
                continue
            old_found, old_key, old_field = _dict_get_ignore_case(old_obj, field_name)
            new_found, new_key, new_field = _dict_get_ignore_case(new_obj, field_name)
            if old_field == new_field:
                continue
            if old_found and _value_matches_locked_rule(rule, old_field):
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
    for rule in policy.get("locked_value_rules", ()):
        field_name = str(rule.get("field") or "").strip()
        if not field_name:
            continue
        old_found, old_key, old_field = _dict_get_ignore_case(old_obj, field_name)
        new_found, new_key, new_field = _dict_get_ignore_case(new_obj, field_name)
        if old_field == new_field:
            continue
        if old_found and _value_matches_locked_rule(rule, old_field):
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
            placed_via_rename = False
            if not new_found:
                renamed_key = _find_renamed_locked_key_candidate(old_obj, fixed, field_name, old_key)
                if renamed_key is not None and renamed_key in fixed:
                    target_key = old_key if old_key is not None else field_name
                    _replace_key_preserve_order(
                        fixed,
                        renamed_key,
                        target_key,
                        _copy_json_value(old_field),
                    )
                    placed_via_rename = True
            if placed_via_rename:
                changed = True
                continue
            target_key = new_key if new_found else (old_key if old_key is not None else field_name)
            fixed[target_key] = _copy_json_value(old_field)
            changed = True
    for rule in policy.get("locked_value_rules", ()):
        field_name = str(rule.get("field") or "").strip()
        if not field_name:
            continue
        old_found, old_key, old_field = _dict_get_ignore_case(old_obj, field_name)
        new_found, new_key, new_field = _dict_get_ignore_case(fixed, field_name)
        if old_field == new_field:
            continue
        if old_found and _value_matches_locked_rule(rule, old_field):
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
