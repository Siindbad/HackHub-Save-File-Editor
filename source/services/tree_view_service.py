def normalize_root_tree_key(value):
    return str(value).strip().casefold()


def tree_display_label_for_key(key, tree_style_variant, safe_display_labels):
    text = str(key)
    if str(tree_style_variant or "").upper() != "B":
        return text
    labels = safe_display_labels if isinstance(safe_display_labels, dict) else {}
    return labels.get(text, text)


def selected_tree_path_text(item_id, item_to_path):
    path = None
    try:
        path = item_to_path.get(item_id, None)
    except Exception:
        path = None
    if path is None:
        return "unknown"
    try:
        return repr(path)
    except Exception:
        return "unknown"


def format_path_for_display(path):
    parts = []
    for token in path:
        if isinstance(token, int):
            parts.append(f"[{token}]")
        else:
            if parts:
                parts.append(".")
            parts.append(str(token))
    return "".join(parts) if parts else "<value>"


def tree_item_can_toggle_from_value(path, value):
    if isinstance(path, tuple) and path and path[0] == "__group__":
        return False
    return isinstance(value, (dict, list)) and len(value) > 0
