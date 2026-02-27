"""Shared tree engine helpers used by JSON and INPUT modes."""

import importlib
import os
from core.domain_impl.ui import tree_policy_service
from core.domain_impl.ui import tree_view_service
from core.domain_impl.support import label_format_service
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def _tree_style_variant(owner: Any) -> str:
    return str(getattr(owner, "_tree_style_variant", "B"))


def _owner_or_fallback(owner: Any, attr_name: str, fallback: Any) -> Any:
    candidate = getattr(owner, attr_name, None)
    if callable(candidate):
        return candidate
    return fallback


def default_list_labelers(owner: Any) -> dict[tuple[Any, ...], Any]:
    variant = _tree_style_variant(owner)
    return {
        ("MailAccounts",): lambda idx, item: label_format_service.mail_account_label(idx, item, variant),
        ("Mails",): lambda idx, item: label_format_service.mails_label(idx, item, variant),
        ("PhoneMessages",): lambda idx, item: label_format_service.phone_messages_label(idx, item, variant),
        ("Files",): lambda idx, item: label_format_service.files_label(idx, item, variant),
        ("Database",): lambda idx, item: label_format_service.database_label(idx, item, variant),
        ("Bookmarks",): lambda idx, item: label_format_service.bookmarks_label(idx, item, variant),
        ("BCCNews",): lambda idx, item: label_format_service.bcc_news_label(idx, item, variant),
        ("BCC.News",): lambda idx, item: label_format_service.bcc_news_label(idx, item, variant),
        ("BCCNews", "news"): lambda idx, item: label_format_service.bcc_news_label(idx, item, variant),
        ("BCC.News", "news"): lambda idx, item: label_format_service.bcc_news_label(idx, item, variant),
        ("Process",): lambda idx, item: label_format_service.process_label(idx, item, variant),
        ("Processes",): lambda idx, item: label_format_service.process_label(idx, item, variant),
        ("Typewriter",): lambda idx, item: label_format_service.typewriter_label(idx, item, variant),
        ("Bank", "accounts"): lambda idx, item: label_format_service.bank_account_label(idx, item, variant),
        ("Bank", "Accounts"): lambda idx, item: label_format_service.bank_account_label(idx, item, variant),
        ("Bank", "transactions"): lambda idx, item: label_format_service.bank_transaction_label(idx, item, variant),
        ("Bank", "Transactions"): lambda idx, item: label_format_service.bank_transaction_label(idx, item, variant),
        ("AppStore", "unlockedMarketItems"): lambda idx, item: label_format_service.app_store_unlocked_item_label(
            idx, item, variant
        ),
        ("App.Store", "unlockedMarketItems"): lambda idx, item: label_format_service.app_store_unlocked_item_label(
            idx, item, variant
        ),
        ("AppStore", "purchasedItems"): lambda idx, item: label_format_service.app_store_unlocked_item_label(
            idx, item, variant
        ),
        ("App.Store", "purchasedItems"): lambda idx, item: label_format_service.app_store_unlocked_item_label(
            idx, item, variant
        ),
        ("Twotter", "users"): label_format_service.twotter_user_label,
        ("Twotter", "posts"): label_format_service.twotter_post_label,
        ("Quests",): lambda idx, item: label_format_service.quests_label(idx, item, variant),
        ("Kisscord", "friends"): label_format_service.kisscord_friend_label,
        ("Stats", "global"): label_format_service.stats_stat_label,
        ("Stats", "Global"): label_format_service.stats_stat_label,
        ("Stats", "my"): label_format_service.stats_stat_label,
        ("Stats", "My"): label_format_service.stats_stat_label,
        ("stats", "global"): label_format_service.stats_stat_label,
        ("stats", "my"): label_format_service.stats_stat_label,
        ("WebsiteTemplates",): lambda idx, item: label_format_service.website_templates_label(idx, item, variant),
        ("Terminal", "installedPackages"): label_format_service.terminal_package_label,
        ("Terminal", "datalist"): label_format_service.terminal_datalist_label,
        ("Terminal", "dataList"): label_format_service.terminal_datalist_label,
    }


def resolve_list_labeler(owner: Any, path: Any) -> Any:
    use_path = list(path or [])
    labelers = getattr(owner, "_list_labelers", {})
    labeler = labelers.get(tuple(use_path)) if isinstance(labelers, dict) else None
    if labeler:
        return labeler
    if (
        len(use_path) == 2
        and str(use_path[0]).casefold() == "twotter"
        and str(use_path[1]).casefold() == "posts"
    ):
        return _owner_or_fallback(owner, "_twotter_post_label", label_format_service.twotter_post_label)
    if len(use_path) >= 2 and str(use_path[0]).casefold() == "taskbar":
        return _owner_or_fallback(owner, "_taskbar_item_label", label_format_service.taskbar_item_label)
    if (
        len(use_path) == 2
        and str(use_path[0]).casefold() == "stats"
        and str(use_path[1]).casefold() in {"global", "my"}
    ):
        return _owner_or_fallback(owner, "_stats_stat_label", label_format_service.stats_stat_label)
    if (
        len(use_path) == 3
        and str(use_path[0]) == "Quests"
        and isinstance(use_path[1], int)
        and str(use_path[2]).casefold() in {"objective", "objectives"}
    ):
        return _owner_or_fallback(owner, "_quest_objective_label", label_format_service.quest_objective_label)
    if (
        len(use_path) == 4
        and str(use_path[0]) == "Quests"
        and isinstance(use_path[1], int)
        and str(use_path[2]).casefold() == "data"
        and str(use_path[3]).casefold() == "teammembers"
    ):
        return _owner_or_fallback(owner, "_quest_team_member_label", label_format_service.quest_team_member_label)
    return None


def _is_input_network_device_row(owner: Any, path: Any) -> bool:
    if str(getattr(owner, "_editor_mode", "JSON")).upper() != "INPUT":
        return False
    if not isinstance(path, list) or len(path) < 2:
        return False
    if str(path[0] or "").strip().casefold() != "network":
        return False
    if not isinstance(path[1], int):
        return False
    try:
        value = owner._get_value(path)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return False
    if not (isinstance(value, dict) and str(value.get("type", "")).strip().upper() == "DEVICE"):
        return False
    try:
        network_value = owner._get_value([path[0]])
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return False
    if not isinstance(network_value, list):
        return False
    first_device_index = None
    for idx, item in enumerate(network_value):
        if isinstance(item, dict) and str(item.get("type", "")).strip().upper() == "DEVICE":
            first_device_index = idx
            break
    return first_device_index is not None and int(path[1]) == int(first_device_index)


def _network_row_display_name(item: dict[str, Any], group: str) -> Any:
    if group == "FIREWALL":
        users = item.get("users")
        if isinstance(users, list) and users:
            user0 = users[0]
            if isinstance(user0, dict):
                return user0.get("id")
        return None
    if group in ("SPLITTER",):
        return None
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
    return name


def _is_input_network_bcc_domains_item(owner: Any, group: Any, item: Any) -> bool:
    if str(getattr(owner, "_editor_mode", "JSON")).upper() != "INPUT":
        return False
    if str(group or "").strip().upper() != "DEVICE":
        return False
    if not isinstance(item, dict):
        return False
    ip = str(item.get("ip", "") or "").strip()
    if ip != "193.8.64.214":
        return False
    name = _network_row_display_name(item, "DEVICE")
    return str(name or "").strip().casefold() == "bcc.com"


def _is_input_network_bcc_subdomain_item(owner: Any, group: Any, item: Any) -> bool:
    if str(getattr(owner, "_editor_mode", "JSON")).upper() != "INPUT":
        return False
    if str(group or "").strip().upper() != "DEVICE":
        return False
    if not isinstance(item, dict):
        return False
    name = str(_network_row_display_name(item, "DEVICE") or "").strip().casefold()
    return bool(name) and name.endswith(".bcc.com")


def _is_input_network_device_item_hidden(owner: Any, group: Any, pos: int, item: Any) -> bool:
    """Hide interim DEVICE subcategories in INPUT mode until their concepts are implemented."""
    if str(getattr(owner, "_editor_mode", "JSON")).upper() != "INPUT":
        return False
    if str(group or "").strip().upper() != "DEVICE":
        return False
    is_primary_geoip = int(pos) == 0
    is_bcc_domains = _is_input_network_bcc_domains_item(owner, group, item)
    return not (is_primary_geoip or is_bcc_domains)


def load_tree_marker_icon(
    owner: Any,
    kind: Any,
    *,
    selected: bool = False,
    expandable: bool = False,
    expanded: bool = False,
    expected_errors: Any,
) -> Any:
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    key = (variant, str(kind), bool(selected), bool(expandable), bool(expanded))
    cache = getattr(owner, "_tree_marker_icon_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        owner._tree_marker_icon_cache = cache
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        image_module = importlib.import_module("PIL.Image")
        draw_module = importlib.import_module("PIL.ImageDraw")
        palette = owner._tree_marker_palette(variant)
        style_variant = str(getattr(owner, "_tree_style_variant", "B")).upper()
        if style_variant == "B":
            owner._check_tree_marker_integrity()
            theme_slug = "kamue" if variant == "KAMUE" else "siindbad"
            arrow_state = "leaf"
            if expandable:
                arrow_state = "expanded" if expanded else "collapsed"
            if str(kind) == "main":
                icon_name = f"b2-main-{arrow_state}-{theme_slug}.png"
            else:
                sel = "on" if selected else "off"
                icon_name = f"b2-sub-{sel}-{arrow_state}-{theme_slug}.png"
            icon_path = os.path.join(owner._resource_base_dir(), "assets", "buttons", "tree-b2", icon_name)
            if os.path.isfile(icon_path):
                with image_module.open(icon_path) as icon_file:
                    icon = icon_file.convert("RGBA")
                if str(kind) == "main":
                    icon = owner._nudge_marker_image_y(icon, delta_y=-1)
                else:
                    icon = owner._nudge_marker_image_y(icon, delta_y=-0.5)
                photo = owner._pil_to_photo(icon)
                owner._bounded_cache_put(cache, key, photo, max_items=128)
                return photo

        if str(kind) == "main":
            icon_name = owner.TREE_MAIN_MARKER_FILES.get(variant, owner.TREE_MAIN_MARKER_FILES["SIINDBAD"])
            icon_path = os.path.join(owner._resource_base_dir(), "assets", "buttons", icon_name)
            owner._check_tree_marker_integrity()
            if os.path.isfile(icon_path):
                with image_module.open(icon_path) as icon_file:
                    icon = icon_file.convert("RGBA")
                if style_variant == "B":
                    icon = owner._nudge_marker_image_y(icon, delta_y=-1)
                photo = owner._pil_to_photo(icon)
                owner._bounded_cache_put(cache, key, photo, max_items=64)
                return photo
            owner._bounded_cache_put(cache, key, None, max_items=64)
            return None
        canvas = image_module.new("RGBA", (10, 10), (0, 0, 0, 0))
        draw = draw_module.Draw(canvas)
        fill = palette["sub_fill"] if selected else None
        draw.ellipse(
            (1, 1, 8, 8),
            fill=fill,
            outline=palette["sub_edge"],
            width=1,
        )
        if style_variant == "B":
            canvas = owner._nudge_marker_image_y(canvas, delta_y=-0.5)
        photo = owner._pil_to_photo(canvas)
        owner._bounded_cache_put(cache, key, photo, max_items=64)
        return photo
    except expected_errors:
        owner._bounded_cache_put(cache, key, None, max_items=64)
        return None


def populate_children(owner: Any, item_id: Any) -> Any:
    path = owner.item_to_path.get(item_id)
    if isinstance(path, tuple) and path[0] == "__group__":
        return
    value = owner._get_value(path)
    if not isinstance(value, (dict, list)):
        return

    for child in owner.tree.get_children(item_id):
        owner.tree.delete(child)

    if isinstance(value, dict):
        hidden_keys_getter = getattr(owner, "_hidden_root_tree_keys_for_mode", None)
        hidden_keys = (
            hidden_keys_getter() if callable(hidden_keys_getter) else set(getattr(owner, "HIDDEN_ROOT_TREE_KEYS", set()))
        )
        keys = list(value.keys())
        if isinstance(path, list) and len(path) == 0:
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
            owner.item_to_path[child_id] = (list(path) if isinstance(path, list) else []) + [key]
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
            if tree_policy_service.is_network_group_hidden_for_mode(owner, path, group):
                continue
            items = groups[group]
            is_input_device_group = (
                str(getattr(owner, "_editor_mode", "JSON")).upper() == "INPUT"
                and bool(path)
                and str(path[0] or "").strip().casefold() == "network"
                and str(group or "").strip().casefold() == "device"
            )
            visible_items = (
                [
                    pair
                    for pos, pair in enumerate(items)
                    if not _is_input_network_device_item_hidden(owner, group, pos, pair[1])
                ]
                if is_input_device_group
                else items
            )
            group_id = owner.tree.insert(
                item_id,
                "end",
                text=f"{group} ({len(visible_items)})",
                tags=("tree-sub-level",),
            )
            owner.item_to_path[group_id] = ("__group__", path, group)
            for pos, (idx, item) in enumerate(items):
                if _is_input_network_device_item_hidden(owner, group, pos, item):
                    continue
                label = ""
                is_input_device_primary = is_input_device_group and pos == 0
                is_input_device_bcc_domains = _is_input_network_bcc_domains_item(owner, group, item)
                if is_input_device_primary:
                    label = "GEO IP"
                elif is_input_device_bcc_domains:
                    label = "BCC DOMAINS"
                if isinstance(item, dict) and not (is_input_device_primary or is_input_device_bcc_domains):
                    if group in ("ROUTER", "DEVICE", "FIREWALL", "SPLITTER"):
                        ip = item.get("ip")
                        match group:
                            case "SPLITTER":
                                name = None
                            case "FIREWALL":
                                name = _network_row_display_name(item, "FIREWALL")
                            case _:
                                name = _network_row_display_name(item, str(group))
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
                owner.item_to_path[child_id] = (list(path) if isinstance(path, list) else []) + [idx]
                if not (is_input_device_primary or is_input_device_bcc_domains):
                    owner._add_placeholder_if_container(child_id, item)
    elif isinstance(value, list):
        labeler = resolve_list_labeler(owner, path)
        for idx, item in enumerate(value):
            if labeler:
                label = labeler(idx, item)
            elif owner._is_database_table_rows_path(path):
                label = owner._database_table_row_label(idx, item)
            else:
                label = f"[{idx}]"
            child_id = owner.tree.insert(item_id, "end", text=label, tags=("tree-sub-level",))
            owner.item_to_path[child_id] = (list(path) if isinstance(path, list) else []) + [idx]
            owner._add_placeholder_if_container(child_id, item)
    refresh_tree_item_markers(owner)


def refresh_tree_item_markers(owner: Any) -> Any:
    tree = getattr(owner, "tree", None)
    if tree is None:
        return
    if str(getattr(owner, "_tree_style_variant", "B")).upper() != "B":
        try:
            for item_id in owner.item_to_path.keys():
                if tree.exists(item_id):
                    tree.item(item_id, image="")
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            pass
        return
    try:
        selected = set(tree.selection())
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        selected = set()
    for item_id, path in owner.item_to_path.items():
        try:
            if not tree.exists(item_id):
                continue
            is_group = isinstance(path, tuple) and path and path[0] == "__group__"
            depth = 0 if is_group else (len(path) if isinstance(path, list) else 0)
            has_children = bool(tree.get_children(item_id))
            is_expanded = bool(tree.item(item_id, "open")) if has_children else False
            if owner._is_input_red_arrow_root_path(path) or _is_input_network_device_row(owner, path):
                icon = owner._load_input_bank_red_arrow_icon(
                    expandable=has_children,
                    expanded=is_expanded,
                )
            elif depth <= 1:
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
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            continue


def refresh_tree_marker_for_item(owner: Any, item_id: Any, selected: Any=False) -> Any:
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
        if owner._is_input_red_arrow_root_path(path) or _is_input_network_device_row(owner, path):
            icon = owner._load_input_bank_red_arrow_icon(
                expandable=has_children,
                expanded=is_expanded,
            )
        elif depth <= 1:
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
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return


def tree_item_can_toggle(owner: Any, item_id: Any) -> Any:
    if not item_id:
        return False
    if owner._is_input_tree_expand_blocked(item_id):
        return False
    try:
        if owner.tree.get_children(item_id):
            return True
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        pass
    path = owner.item_to_path.get(item_id)
    if _is_input_network_device_row(owner, path):
        return False
    try:
        value = owner._get_value(path)
        return tree_view_service.tree_item_can_toggle_from_value(path, value)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return False


def on_tree_click_toggle(owner: Any, event: Any) -> Any:
    tree = owner.tree
    item_id = tree.identify_row(event.y)
    if not item_id:
        return None
    if not tree_item_can_toggle(owner, item_id):
        return None
    # Only intercept clicks in the tree/icon gutter (arrow+marker area).
    try:
        bbox = tree.bbox(item_id, "#0")
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
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
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return None
    return "break"


def on_tree_double_click_guard(owner: Any, event: Any) -> Any:
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
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return "break"
    owner.set_status("INPUT mode: selected subcategory is locked.")
    return "break"
