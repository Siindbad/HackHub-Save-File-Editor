"""Shared tree engine helpers used by JSON and INPUT modes."""

from services import tree_view_service


def populate_children(owner, item_id):
    path = owner.item_to_path.get(item_id)
    if isinstance(path, tuple) and path[0] == "__group__":
        return
    value = owner._get_value(path)
    if not isinstance(value, (dict, list)):
        return

    # Clear existing children.
    for child in owner.tree.get_children(item_id):
        owner.tree.delete(child)

    if isinstance(value, dict):
        hidden_keys_getter = getattr(owner, "_hidden_root_tree_keys_for_mode", None)
        hidden_keys = (
            hidden_keys_getter() if callable(hidden_keys_getter) else set(getattr(owner, "HIDDEN_ROOT_TREE_KEYS", set()))
        )
        keys = list(value.keys())
        if isinstance(path, list) and len(path) == 0:
            # UI-only ordering for top-level categories; does not mutate save data.
            keys = sorted(
                keys,
                key=lambda raw: str(owner._tree_display_label_for_key(raw)).casefold(),
            )
        for key in keys:
            if (
                isinstance(path, list)
                and not path
                and owner._normalize_root_tree_key(key) in hidden_keys
            ):
                continue
            level_tag = "tree-main-level" if isinstance(path, list) and len(path) == 0 else "tree-sub-level"
            child_text = owner._tree_display_label_for_key(key)
            if tuple(path or []) in (("Typewriter",),):
                entry_value = value.get(key)
                if isinstance(entry_value, dict):
                    type_value = entry_value.get("type")
                    if type_value:
                        child_text = str(type_value)
            child_id = owner.tree.insert(
                item_id,
                "end",
                text=child_text,
                tags=(level_tag,),
            )
            owner.item_to_path[child_id] = path + [key]
            owner._add_placeholder_if_container(child_id, value[key])
    elif isinstance(value, list) and owner._is_network_list(path, value):
        groups = {}
        for idx, item in enumerate(value):
            group = item.get("type") if isinstance(item, dict) else "UNKNOWN"
            groups.setdefault(group, []).append((idx, item))

        ordered_groups = [t for t in owner.network_types if t in groups]
        for group in sorted(g for g in groups.keys() if g not in owner.network_types_set):
            ordered_groups.append(group)

        for group in ordered_groups:
            items = groups[group]
            group_id = owner.tree.insert(
                item_id,
                "end",
                text=f"{group} ({len(items)})",
                tags=("tree-sub-level",),
            )
            owner.item_to_path[group_id] = ("__group__", path, group)
            for idx, item in items:
                # Network subgroup rows use descriptive labels only; hide raw [index] prefixes.
                label = ""
                if isinstance(item, dict):
                    if group in ("ROUTER", "DEVICE", "FIREWALL", "SPLITTER"):
                        ip = item.get("ip")
                        if group == "SPLITTER":
                            name = None
                        elif group == "FIREWALL":
                            name = None
                            users = item.get("users")
                            if isinstance(users, list) and users:
                                user0 = users[0]
                                if isinstance(user0, dict):
                                    name = user0.get("id")
                        else:
                            name = item.get("name")
                            if not name:
                                domain = item.get("domain")
                                if isinstance(domain, dict):
                                    name = domain.get("name")
                            if not name:
                                users = item.get("users")
                                if isinstance(users, list) and users:
                                    user0 = users[0]
                                    if isinstance(user0, dict):
                                        name = user0.get("firstName") or user0.get("name")
                            if not name and group in ("ROUTER", "DEVICE"):
                                name = item.get("type")
                        if ip is not None or name is not None:
                            ip_str = "" if ip is None else str(ip)
                            name_str = "" if name is None else str(name)
                            label = f"{ip_str} | {name_str}".strip(" |")
                        else:
                            extra = []
                            if "id" in item:
                                extra.append(f"id={item['id']}")
                            if "ip" in item:
                                extra.append(f"ip={item['ip']}")
                            if extra:
                                label = " ".join(extra)
                    else:
                        extra = []
                        if "id" in item:
                            extra.append(f"id={item['id']}")
                        if "ip" in item:
                            extra.append(f"ip={item['ip']}")
                        if extra:
                            label = " ".join(extra)
                if not label:
                    label = f"Item {idx + 1}"
                child_id = owner.tree.insert(group_id, "end", text=label, tags=("tree-sub-level",))
                owner.item_to_path[child_id] = path + [idx]
                owner._add_placeholder_if_container(child_id, item)
    elif isinstance(value, list):
        labeler = owner._list_labelers.get(tuple(path))
        for idx, item in enumerate(value):
            if labeler:
                label = labeler(idx, item)
            elif owner._is_database_table_rows_path(path):
                label = owner._database_table_row_label(idx, item)
            else:
                label = f"[{idx}]"
            child_id = owner.tree.insert(item_id, "end", text=label, tags=("tree-sub-level",))
            owner.item_to_path[child_id] = path + [idx]
            owner._add_placeholder_if_container(child_id, item)
    refresh_tree_item_markers(owner)


def refresh_tree_item_markers(owner):
    tree = getattr(owner, "tree", None)
    if tree is None:
        return
    if str(getattr(owner, "_tree_style_variant", "B")).upper() != "B":
        try:
            for item_id in owner.item_to_path.keys():
                if tree.exists(item_id):
                    tree.item(item_id, image="")
        except Exception:
            pass
        return
    try:
        selected = set(tree.selection())
    except Exception:
        selected = set()
    for item_id, path in owner.item_to_path.items():
        try:
            if not tree.exists(item_id):
                continue
            is_group = isinstance(path, tuple) and path and path[0] == "__group__"
            depth = 0 if is_group else (len(path) if isinstance(path, list) else 0)
            has_children = bool(tree.get_children(item_id))
            is_expanded = bool(tree.item(item_id, "open")) if has_children else False
            if depth <= 1:
                if owner._is_input_red_arrow_root_path(path):
                    icon = owner._load_input_bank_red_arrow_icon(
                        expandable=has_children,
                        expanded=is_expanded,
                    )
                else:
                    icon = owner._load_tree_marker_icon(
                        "main",
                        selected=False,
                        expandable=has_children,
                        expanded=is_expanded,
                    )
            else:
                icon = owner._load_tree_marker_icon(
                    "sub",
                    selected=(item_id in selected),
                    expandable=has_children,
                    expanded=is_expanded,
                )
            tree.item(item_id, image=icon if icon is not None else "")
        except Exception:
            continue


def refresh_tree_marker_for_item(owner, item_id, selected=False):
    tree = getattr(owner, "tree", None)
    if tree is None or not item_id:
        return
    if str(getattr(owner, "_tree_style_variant", "B")).upper() != "B":
        return
    try:
        if not tree.exists(item_id):
            return
        path = owner.item_to_path.get(item_id)
        is_group = isinstance(path, tuple) and path and path[0] == "__group__"
        depth = 0 if is_group else (len(path) if isinstance(path, list) else 0)
        has_children = bool(tree.get_children(item_id))
        is_expanded = bool(tree.item(item_id, "open")) if has_children else False
        if depth <= 1:
            if owner._is_input_red_arrow_root_path(path):
                icon = owner._load_input_bank_red_arrow_icon(
                    expandable=has_children,
                    expanded=is_expanded,
                )
            else:
                icon = owner._load_tree_marker_icon(
                    "main",
                    selected=False,
                    expandable=has_children,
                    expanded=is_expanded,
                )
        else:
            icon = owner._load_tree_marker_icon(
                "sub",
                selected=bool(selected),
                expandable=has_children,
                expanded=is_expanded,
            )
        tree.item(item_id, image=icon if icon is not None else "")
    except Exception:
        return


def tree_item_can_toggle(owner, item_id):
    if not item_id:
        return False
    if owner._is_input_tree_expand_blocked(item_id):
        return False
    try:
        if owner.tree.get_children(item_id):
            return True
    except Exception:
        pass
    path = owner.item_to_path.get(item_id)
    try:
        value = owner._get_value(path)
        return tree_view_service.tree_item_can_toggle_from_value(path, value)
    except Exception:
        return False


def on_tree_click_toggle(owner, event):
    tree = owner.tree
    item_id = tree.identify_row(event.y)
    if not item_id:
        return None
    if not tree_item_can_toggle(owner, item_id):
        return None
    # Only intercept clicks in the tree/icon gutter (arrow+marker area).
    try:
        bbox = tree.bbox(item_id, "#0")
    except Exception:
        bbox = None
    if not bbox:
        return None
    x, _y, _w, _h = bbox
    local_x = int(event.x - x)
    if local_x < 0 or local_x > 14:
        return None

    try:
        tree.focus(item_id)
        tree.selection_set(item_id)
        currently_open = bool(tree.item(item_id, "open"))
        tree.item(item_id, open=not currently_open)
        if not currently_open:
            # Ensure lazy tree children are materialized on first single-click expand.
            populate_children(owner, item_id)
        refresh_tree_item_markers(owner)
    except Exception:
        return None
    return "break"


def on_tree_double_click_guard(owner, event):
    tree = owner.tree
    item_id = tree.identify_row(event.y)
    if not item_id:
        return None
    if not owner._is_input_tree_expand_blocked(item_id):
        return None
    try:
        tree.focus(item_id)
        tree.selection_set(item_id)
        tree.item(item_id, open=False)
        owner.root.after_idle(lambda iid=item_id: owner.tree.item(iid, open=False))
    except Exception:
        return "break"
    owner.set_status("INPUT mode: Bank subcategories are disabled.")
    return "break"
