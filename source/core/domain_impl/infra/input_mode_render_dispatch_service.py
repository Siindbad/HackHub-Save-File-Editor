"""INPUT-mode render routing orchestration helpers."""

from typing import Any


def is_database_input_style_path(path: Any) -> bool:
    """Return whether path targets a Database branch eligible for INPUT matrix/table rendering."""
    normalized = list(path or [])
    if not normalized:
        return False
    if str(normalized[0]) != "Database":
        return False
    # Root Database now shows subcategory selector; style render is subcategory-only.
    if len(normalized) == 1:
        return False
    # Support clicking a Database entry node (e.g., first item -> Grades matrix).
    if len(normalized) == 2 and isinstance(normalized[1], int):
        return True
    return len(normalized) >= 4 and str(normalized[2]) == "tables" and str(normalized[3]) == "Grades"


def is_input_database_locked_subcategory_path(owner: Any, path: Any) -> bool:
    """Return whether INPUT path points at a locked Database subcategory root row."""
    normalized = list(path or [])
    if len(normalized) != 2:
        return False
    if owner._input_mode_root_key_for_path(normalized) != "database":
        return False
    entry = owner._get_value(normalized)
    if not isinstance(entry, dict):
        return False
    tables = entry.get("tables")
    if not isinstance(tables, dict) or not tables:
        return False
    first_table = str(next(iter(tables.keys()))).strip().casefold()
    return first_table in {"grades", "users", "customers"}


def is_database_table_rows_path(path: Any) -> bool:
    """Return whether path points to Database tables rows collection."""
    if not isinstance(path, list):
        return False
    if len(path) < 4:
        return False
    return str(path[0]) == "Database" and str(path[2]) == "tables"


def refresh_input_mode_fields(
    owner: Any,
    path: Any,
    value: Any,
    *,
    tk_module: Any,
    input_database_style_service: Any,
    input_mode_service: Any,
    input_network_router_style_service: Any,
) -> None:
    host = getattr(owner, "_input_mode_fields_host", None)
    if host is None:
        return
    owner._cancel_pending_router_input_batches()
    owner._clear_router_virtual_state()
    owner._cancel_pending_input_mode_layout_finalize()
    owner._input_mode_render_token = int(getattr(owner, "_input_mode_render_token", 0) or 0) + 1
    owner._input_mode_field_specs = []
    owner._input_mode_current_path = list(path or [])
    owner._input_mode_no_fields_label = None
    theme = getattr(owner, "_theme", {})
    panel_bg = theme.get("panel", "#161b24")
    host.configure(bg=panel_bg)
    normalized_path = list(path or [])
    root_key = owner._input_mode_root_key_for_path(normalized_path)
    is_network_router_payload = owner._is_network_router_input_style_payload(normalized_path, value)
    is_network_bcc_domains_payload = owner._is_network_bcc_domains_input_style_payload(normalized_path, value)
    is_network_blue_table_payload = owner._is_network_blue_table_input_style_payload(normalized_path, value)
    is_network_interpol_payload = owner._is_network_interpol_input_style_payload(normalized_path, value)
    is_network_geoip_payload = owner._is_network_geoip_input_style_payload(normalized_path, value)
    is_network_device_payload = owner._is_network_device_input_style_payload(normalized_path, value)
    is_network_firewall_payload = owner._is_network_firewall_input_style_payload(normalized_path, value)
    database_grades_matrix = owner._database_grades_matrix_for_input_path(normalized_path, value)
    database_bcc_payload = owner._database_bcc_payload_for_input_path(normalized_path, value)
    database_interpol_payload = owner._database_interpol_payload_for_input_path(normalized_path, value)
    is_database_payload = bool(database_grades_matrix)
    if is_network_router_payload:
        input_network_router_style_service.prepare_router_render_host(
            owner,
            host,
            reset_pool=False,
        )
        keep_database_children = input_database_style_service.suspend_database_render_host(owner, host)
        pool_children = {
            row_slot.get("row_frame")
            for row_slot in list(getattr(owner, "_input_mode_router_row_pool", []) or [])
            if isinstance(row_slot, dict)
        }
        pool_children.update(input_network_router_style_service.router_pool_children(owner, host))
        for child in list(host.winfo_children()):
            if child in pool_children or child in keep_database_children:
                continue
            try:
                child.destroy()
            except (tk_module.TclError, RuntimeError, AttributeError):
                continue
    elif is_database_payload:
        keep_router_children = input_network_router_style_service.suspend_router_render_host(owner, host)
        keep_database_children = input_database_style_service.database_pool_children(owner, host)
        for child in host.winfo_children():
            if child in keep_router_children or child in keep_database_children:
                continue
            child.destroy()
    else:
        keep_router_children = input_network_router_style_service.suspend_router_render_host(owner, host)
        keep_database_children = input_database_style_service.suspend_database_render_host(owner, host)
        for child in host.winfo_children():
            if child in keep_router_children or child in keep_database_children:
                continue
            child.destroy()
    if owner._is_input_mode_category_disabled(normalized_path):
        input_mode_service.show_input_mode_notice(
            owner,
            host,
            panel_bg,
            owner.INPUT_MODE_DISABLED_CATEGORY_MESSAGE,
            font_size=11,
            tk_module=tk_module,
        )
        # Track disabled roots too; otherwise revisits can be incorrectly skipped.
        input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
        return
    if len(normalized_path) == 0:
        has_data = getattr(owner, "data", None) is not None
        message = (
            "No direct value fields here. Select a specific item node to edit."
            if has_data
            else "No File Loaded. Open A .HHSAV File Before Continuing."
        )
        input_mode_service.show_input_mode_notice(
            owner,
            host,
            panel_bg,
            message,
            font_size=9,
            tk_module=tk_module,
        )
        return
    if (
        len(normalized_path) == 1
        and root_key == "network"
    ):
        # Keep generic Network root placeholder, but allow custom subgroup payload renderers
        # (e.g., ROUTER/DEVICE/FIREWALL grouped selection routed through list_path) to proceed.
        if is_network_router_payload or is_network_device_payload or is_network_firewall_payload:
            pass
        else:
            input_mode_service.show_input_mode_notice(
                owner,
                host,
                panel_bg,
                "Select A Sub Category To View Input Fields",
                font_size=11,
                tk_module=tk_module,
            )
            input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
            return
    if len(normalized_path) == 1 and root_key == "database":
        input_mode_service.show_input_mode_notice(
            owner,
            host,
            panel_bg,
            "Select A Sub Category To View Input Fields",
            font_size=11,
            tk_module=tk_module,
        )
        input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
        return
    if owner._is_bank_input_style_path(normalized_path):
        bank_rows = owner._collect_bank_input_rows(value)
        if bank_rows:
            owner._render_bank_input_style_rows(host, normalized_path, bank_rows)
            owner._refresh_input_mode_bool_widget_colors()
            owner._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
            return
    if database_bcc_payload:
        owner._render_database_bcc_table(host, normalized_path, database_bcc_payload)
        owner._refresh_input_mode_bool_widget_colors()
        owner._schedule_input_mode_layout_finalize(reset_scroll=True)
        input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
        return
    if database_interpol_payload:
        owner._render_database_interpol_table(host, normalized_path, database_interpol_payload)
        owner._refresh_input_mode_bool_widget_colors()
        owner._schedule_input_mode_layout_finalize(reset_scroll=True)
        input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
        return
    if owner._is_database_input_style_path(normalized_path):
        if database_grades_matrix:
            owner._render_database_grades_input_matrix(host, normalized_path, database_grades_matrix)
            owner._refresh_input_mode_bool_widget_colors()
            owner._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
            return
    if owner._is_suspicion_input_style_path(normalized_path):
        if owner._render_suspicion_phone_input(host, normalized_path, value):
            owner._refresh_input_mode_bool_widget_colors()
            owner._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
            return
    if owner._is_phone_input_style_path(normalized_path):
        if owner._render_phone_preview_input(host, normalized_path, value):
            owner._refresh_input_mode_bool_widget_colors()
            owner._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
            return
    if owner._is_skypersky_input_style_path(normalized_path):
        if owner._render_skypersky_input(host, normalized_path, value):
            owner._refresh_input_mode_bool_widget_colors()
            owner._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
            return
    if is_network_router_payload:
        router_rows = owner._collect_network_router_input_rows(normalized_path, value)
        if router_rows:
            owner._render_network_router_input_rows(
                host,
                normalized_path,
                router_rows,
                start_index=0,
                finalize=True,
                total_rows=len(router_rows),
            )
            owner._clear_router_virtual_state()
            owner._refresh_input_mode_bool_widget_colors()
            owner._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
            return
    if is_network_firewall_payload:
        firewall_rows = owner._collect_network_firewall_input_rows(normalized_path, value)
        if firewall_rows:
            owner._render_network_firewall_input_rows(host, normalized_path, firewall_rows)
            owner._refresh_input_mode_bool_widget_colors()
            owner._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
            return
    if is_network_bcc_domains_payload:
        bcc_domains_payload = owner._collect_network_bcc_domains_payload(normalized_path, value)
        if bcc_domains_payload:
            owner._render_network_bcc_domains_input(host, normalized_path, bcc_domains_payload)
            owner._refresh_input_mode_bool_widget_colors()
            owner._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
            return
    if is_network_blue_table_payload:
        blue_table_payload = owner._collect_network_blue_table_payload(normalized_path, value)
        if blue_table_payload:
            owner._render_network_blue_table_input(host, normalized_path, blue_table_payload)
            owner._refresh_input_mode_bool_widget_colors()
            owner._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
            return
    if is_network_interpol_payload:
        interpol_payload = owner._collect_network_interpol_payload(normalized_path, value)
        if interpol_payload:
            owner._render_network_interpol_input(host, normalized_path, interpol_payload)
            owner._refresh_input_mode_bool_widget_colors()
            owner._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
            return
    if is_network_geoip_payload:
        geoip_payload = owner._collect_network_geoip_payload(normalized_path, value)
        if geoip_payload:
            owner._render_network_geoip_input(host, normalized_path, geoip_payload)
            owner._refresh_input_mode_bool_widget_colors()
            owner._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
            return
    if is_network_device_payload:
        input_mode_service.show_input_mode_notice(
            owner,
            host,
            panel_bg,
            "Selected A Sub Category",
            font_size=11,
            tk_module=tk_module,
        )
        input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
        return
    # Generic INPUT fallback rows are retired; unsupported paths should
    # consistently show the development template until a custom layout is added.
    input_mode_service.show_input_mode_notice(
        owner,
        host,
        panel_bg,
        owner.INPUT_MODE_DISABLED_CATEGORY_MESSAGE,
        font_size=11,
        tk_module=tk_module,
    )
    input_mode_service.mark_input_mode_render_complete(owner, normalized_path)
    return
