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
    is_network_router_payload = owner._is_network_router_input_style_payload(normalized_path, value)
    is_database_payload = bool(owner._database_grades_matrix_for_input_path(normalized_path, value))
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
    input_mode_service.render_payload(
        owner,
        normalized_path,
        value,
        host=host,
        panel_bg=panel_bg,
        tk_module=tk_module,
    )
