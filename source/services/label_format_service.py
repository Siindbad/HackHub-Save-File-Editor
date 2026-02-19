def _is_variant_b(tree_style_variant):
    # Tree Variant-B suppresses numeric prefixes for cleaner labels.
    return str(tree_style_variant or "B").upper() == "B"


def mail_account_label(idx, item, tree_style_variant):
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


def mails_label(idx, item, tree_style_variant):
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


def phone_messages_label(idx, item, tree_style_variant):
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


def files_label(idx, item, tree_style_variant):
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


def database_label(idx, item, tree_style_variant):
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


def twotter_user_label(idx, item):
    if isinstance(item, dict):
        name = item.get("name")
        if name:
            return f"[{idx}] {name}"
    return f"[{idx}]"


def quests_label(idx, item, tree_style_variant):
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


def kisscord_friend_label(idx, item):
    if isinstance(item, dict):
        name = item.get("name")
        if name:
            return f"[{idx}] {name}"
    return f"[{idx}]"


def website_templates_label(idx, item, tree_style_variant):
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


def terminal_package_label(idx, item):
    if isinstance(item, dict):
        pkg = item.get("pkg")
        if pkg:
            return f"[{idx}] {pkg}"
    return f"[{idx}]"


def terminal_datalist_label(idx, item):
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


def bookmarks_label(idx, item, tree_style_variant):
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


def bcc_news_label(idx, item, tree_style_variant):
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        news_id = item.get("id")
        if news_id:
            return str(news_id) if is_variant_b else f"[{idx}] {news_id}"
        title = item.get("title")
        if title:
            return str(title) if is_variant_b else f"[{idx}] {title}"
    return "News" if is_variant_b else f"[{idx}]"


def process_label(idx, item, tree_style_variant):
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        name = item.get("name")
        if name:
            return str(name) if is_variant_b else f"[{idx}] {name}"
        proc_id = item.get("id")
        if proc_id:
            return str(proc_id) if is_variant_b else f"[{idx}] {proc_id}"
    return "Process" if is_variant_b else f"[{idx}]"


def typewriter_label(idx, item, tree_style_variant):
    is_variant_b = _is_variant_b(tree_style_variant)
    if isinstance(item, dict):
        type_value = item.get("type")
        if type_value:
            return str(type_value) if is_variant_b else f"[{idx}] {type_value}"
        name = item.get("name")
        if name:
            return str(name) if is_variant_b else f"[{idx}] {name}"
    return "Typewriter" if is_variant_b else f"[{idx}]"


def bank_account_label(idx, item, tree_style_variant):
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


def bank_transaction_label(idx, item, tree_style_variant):
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


def app_store_unlocked_item_label(idx, item, tree_style_variant):
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


def find_first_dict_key_change(old_value, new_value, current_path=None):
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
