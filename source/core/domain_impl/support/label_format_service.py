from typing import Any

def _is_variant_b(tree_style_variant):
    # Tree Variant-B suppresses numeric prefixes for cleaner labels.
    return str(tree_style_variant or "B").upper() == "B"


def mail_account_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        full_name = item.get("fullName")
        if full_name:
            return str(full_name) if is_variant_b else f"[{idx}] {full_name}"
        if is_variant_b:
            email = item.get("email")
            if email:
                return str(email)
            provider = item.get("provider")
            if provider:
                return str(provider)
    if is_variant_b:
        return "Account"
    return f"[{idx}]"


def mails_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        from_value = item.get("from")
        if from_value:
            return str(from_value) if is_variant_b else f"[{idx}] {from_value}"
        if is_variant_b:
            to_value = item.get("to")
            if to_value:
                return str(to_value)
            msg_id = item.get("id")
            if msg_id:
                return str(msg_id)
    if is_variant_b:
        return "Mail"
    return f"[{idx}]"


def phone_messages_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        from_value = item.get("from")
        if from_value:
            return str(from_value) if is_variant_b else f"[{idx}] {from_value}"
        if is_variant_b:
            to_value = item.get("to")
            if to_value:
                return str(to_value)
            msg_id = item.get("id")
            if msg_id:
                return str(msg_id)
    if is_variant_b:
        return "Message"
    return f"[{idx}]"


def files_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        name = item.get("name")
        if name:
            return str(name) if is_variant_b else f"[{idx}] {name}"
        if is_variant_b:
            path = item.get("path")
            if path:
                return str(path)
            file_id = item.get("id")
            if file_id:
                return str(file_id)
    if is_variant_b:
        return "File"
    return f"[{idx}]"


def database_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        host = item.get("host")
        if host:
            return str(host) if is_variant_b else f"[{idx}] {host}"
        if is_variant_b:
            db_name = item.get("database") or item.get("name")
            if db_name:
                return str(db_name)
            db_id = item.get("id")
            if db_id:
                return str(db_id)
    if is_variant_b:
        return "Database"
    return f"[{idx}]"


def database_root_entry_label(
    idx: Any,
    item: Any,
    *,
    tree_style_variant: Any,
    editor_mode: Any,
) -> Any:
    """Return Database root row label with INPUT-mode subcategory aliases where applicable."""
    variant = str(tree_style_variant or "B")
    if str(editor_mode or "JSON").upper() != "INPUT":
        return database_label(idx, item, variant)
    if isinstance(item, dict):
        tables = item.get("tables")
        if isinstance(tables, dict) and tables:
            first_table = str(next(iter(tables.keys()))).strip().casefold()
            if first_table == "grades":
                return "Grades"
            if first_table == "users":
                return "BCC"
            if first_table == "customers":
                return "INTERPOL"
    return database_label(idx, item, variant)


def database_table_row_label(idx: Any, item: Any) -> Any:
    """Return Database row label preferring nested string values over numeric identifiers."""
    _ = idx
    if isinstance(item, dict):
        # Prefer first nested string value (email/name/etc.) before numeric ids.
        first_scalar = None
        for value_obj in item.values():
            if not isinstance(value_obj, dict):
                continue
            value = value_obj.get("value")
            if isinstance(value, str):
                text = value.strip()
                if text:
                    return text
            if first_scalar is None and isinstance(value, (int, float)) and not isinstance(value, bool):
                first_scalar = str(value)
        direct_value = item.get("value")
        if isinstance(direct_value, (str, int, float)) and str(direct_value).strip():
            return str(direct_value)
        if first_scalar is not None:
            return first_scalar
    return f"[{idx}]"


def twotter_user_label(idx: Any, item: Any) -> Any:
    _ = idx
    if isinstance(item, dict):
        name = item.get("name")
        if name:
            return str(name)
        username = item.get("username")
        if username:
            return str(username)
        user_id = item.get("id")
        if user_id:
            return str(user_id)
    return "User"


def twotter_post_label(idx: Any, item: Any) -> Any:
    _ = idx
    if isinstance(item, dict):
        locale = item.get("locale")
        if locale:
            return str(locale)
        post_id = item.get("id")
        if post_id:
            return str(post_id)
    if isinstance(item, str):
        text = item.strip()
        if text:
            return text
    return "Post"


def quests_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        name = item.get("name")
        if name:
            return str(name) if is_variant_b else f"[{idx}] {name}"
        if is_variant_b:
            quest_id = item.get("id")
            if quest_id:
                return str(quest_id)
    if is_variant_b:
        return "Quest"
    return f"[{idx}]"


def quest_objective_label(idx: Any, item: Any) -> Any:
    _ = idx
    if isinstance(item, str):
        text = item.strip()
        if text:
            return text
    if isinstance(item, (int, float)) and not isinstance(item, bool):
        return str(item)
    if isinstance(item, dict):
        objective = item.get("objective") or item.get("name") or item.get("id")
        if objective:
            return str(objective)
    return "Objective"


def quest_team_member_label(idx: Any, item: Any) -> Any:
    _ = idx
    if isinstance(item, dict):
        name = item.get("name")
        if name:
            return str(name)
        username = item.get("username")
        if username:
            return str(username)
        member_id = item.get("id")
        if member_id:
            return str(member_id)
    if isinstance(item, str):
        text = item.strip()
        if text:
            return text
    return "Team Member"


def stats_stat_label(idx: Any, item: Any) -> Any:
    _ = idx
    if isinstance(item, dict):
        stat = item.get("stat")
        if stat:
            return str(stat)
        name = item.get("name")
        if name:
            return str(name)
        stat_id = item.get("id")
        if stat_id:
            return str(stat_id)
    if isinstance(item, str):
        text = item.strip()
        if text:
            return text
    return "Stat"


def taskbar_item_label(idx: Any, item: Any) -> Any:
    _ = idx
    if isinstance(item, str):
        text = item.strip()
        if text:
            return text
    if isinstance(item, dict):
        name = item.get("name") or item.get("label") or item.get("id")
        if name:
            return str(name)
    if isinstance(item, (int, float)) and not isinstance(item, bool):
        return str(item)
    return "Taskbar Item"


def kisscord_friend_label(idx: Any, item: Any) -> Any:
    _ = idx
    if isinstance(item, dict):
        name = item.get("name")
        if name:
            return str(name)
        username = item.get("username")
        if username:
            return str(username)
        friend_id = item.get("id")
        if friend_id:
            return str(friend_id)
    return "Friend"


def website_templates_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        template = item.get("template")
        if template:
            return str(template) if is_variant_b else f"[{idx}] {template}"
        if is_variant_b:
            name = item.get("name")
            if name:
                return str(name)
            template_id = item.get("id")
            if template_id:
                return str(template_id)
    if is_variant_b:
        return "Template"
    return f"[{idx}]"


def terminal_package_label(idx: Any, item: Any) -> Any:
    _ = idx
    if isinstance(item, str):
        text = item.strip()
        if text:
            return text
    if isinstance(item, dict):
        pkg = item.get("pkg")
        if pkg:
            return str(pkg)
        name = item.get("name")
        if name:
            return str(name)
        package_id = item.get("id")
        if package_id:
            return str(package_id)
    return "Package"


def terminal_datalist_label(idx: Any, item: Any) -> Any:
    # Prefer command/name context over raw index for terminal data rows.
    if isinstance(item, dict):
        name = item.get("name") or item.get("command")
        input_value = item.get("input")
        if name or input_value:
            parts = []
            if name:
                parts.append(str(name))
            if input_value:
                parts.append(str(input_value))
            return " | ".join(parts)
    return f"[{idx}]"


def bookmarks_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, str):
        raw = item.strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
            raw = raw[1:-1].strip()
        else:
            # Prefer visible content inside quotes when source strings embed labels.
            for quote in ("'", '"'):
                start = raw.find(quote)
                end = raw.find(quote, start + 1) if start >= 0 else -1
                if start >= 0 and end > start + 1:
                    candidate = raw[start + 1 : end].strip()
                    if candidate:
                        raw = candidate
                        break
        if raw:
            return raw if is_variant_b else f"[{idx}] {raw}"
    if isinstance(item, dict):
        text = item.get("name") or item.get("title") or item.get("label") or item.get("url")
        if text:
            return str(text) if is_variant_b else f"[{idx}] {text}"
    return "Bookmark" if is_variant_b else f"[{idx}]"


def bcc_news_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        news_id = item.get("id")
        if news_id:
            return str(news_id) if is_variant_b else f"[{idx}] {news_id}"
        title = item.get("title")
        if title:
            return str(title) if is_variant_b else f"[{idx}] {title}"
    return "News" if is_variant_b else f"[{idx}]"


def process_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        name = item.get("name")
        if name:
            return str(name) if is_variant_b else f"[{idx}] {name}"
        proc_id = item.get("id")
        if proc_id:
            return str(proc_id) if is_variant_b else f"[{idx}] {proc_id}"
    return "Process" if is_variant_b else f"[{idx}]"


def typewriter_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        type_value = item.get("type")
        if type_value:
            return str(type_value) if is_variant_b else f"[{idx}] {type_value}"
        name = item.get("name")
        if name:
            return str(name) if is_variant_b else f"[{idx}] {name}"
    return "Typewriter" if is_variant_b else f"[{idx}]"


def bank_account_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        account_name = item.get("accountName")
        if account_name:
            return str(account_name) if is_variant_b else f"[{idx}] {account_name}"
        first = str(item.get("firstName") or "").strip()
        last = str(item.get("lastName") or "").strip()
        full_name = " ".join(part for part in (first, last) if part)
        if full_name:
            return full_name if is_variant_b else f"[{idx}] {full_name}"
        iban = item.get("IBAN")
        if iban:
            return str(iban) if is_variant_b else f"[{idx}] {iban}"
    return "Account" if is_variant_b else f"[{idx}]"


def bank_transaction_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        name = item.get("name")
        if name:
            return str(name) if is_variant_b else f"[{idx}] {name}"
        from_obj = item.get("from")
        if isinstance(from_obj, dict):
            from_name = from_obj.get("name")
            if from_name:
                return str(from_name) if is_variant_b else f"[{idx}] {from_name}"
        tx_id = item.get("id")
        if tx_id:
            return str(tx_id) if is_variant_b else f"[{idx}] {tx_id}"
    return "Transaction" if is_variant_b else f"[{idx}]"


def app_store_unlocked_item_label(idx: Any, item: Any, tree_style_variant: Any) -> Any:
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, str):
        value = item.strip()
        if value:
            return value if is_variant_b else f"[{idx}] {value}"
    if isinstance(item, dict):
        name = item.get("name")
        if name:
            return str(name) if is_variant_b else f"[{idx}] {name}"
    return "Item" if is_variant_b else f"[{idx}]"


def find_first_dict_key_change(old_value: Any, new_value: Any, current_path: Any=None) -> Any:
    # Detect first structural key mismatch to block unsafe key rename/remove edits.
    if current_path is None:
        current_path = []
    if isinstance(old_value, dict):
        if not isinstance(new_value, dict):
            return {
                "path": list(current_path),
                "missing": sorted(str(key) for key in old_value.keys()),
                "added": [],
                "type_changed": True,
            }
        old_keys = set(old_value.keys())
        new_keys = set(new_value.keys())
        if old_keys != new_keys:
            return {
                "path": list(current_path),
                "missing": sorted(str(key) for key in (old_keys - new_keys)),
                "added": sorted(str(key) for key in (new_keys - old_keys)),
                "type_changed": False,
            }
        for key in old_value.keys():
            issue = find_first_dict_key_change(
                old_value.get(key),
                new_value.get(key),
                list(current_path) + [key],
            )
            if issue:
                return issue
        return None
    if isinstance(old_value, list) and isinstance(new_value, list):
        max_len = min(len(old_value), len(new_value))
        for idx in range(max_len):
            issue = find_first_dict_key_change(
                old_value[idx],
                new_value[idx],
                list(current_path) + [idx],
            )
            if issue:
                return issue
    return None
