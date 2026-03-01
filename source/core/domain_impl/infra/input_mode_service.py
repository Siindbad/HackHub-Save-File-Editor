import json
import logging
import time
import tkinter as tk
from decimal import Decimal, InvalidOperation
from typing import Any

from core.domain_impl.support import input_bank_style_service
from core.domain_impl.support import input_database_bcc_style_service
from core.domain_impl.support import input_database_style_service
from core.domain_impl.support import input_network_device_bcc_style_service
from core.domain_impl.support import input_network_device_geoip_style_service
from core.domain_impl.support import input_network_firewall_style_service
from core.domain_impl.support import input_network_router_style_service
from core.domain_impl.ui import tree_navigation_service
from core.exceptions import EXPECTED_ERRORS

_LOG = logging.getLogger(__name__)
_EXPECTED_APP_ERRORS = EXPECTED_ERRORS


def is_input_scalar(value: Any) -> Any:
    # INPUT mode only renders direct scalar leaves as editable fields.
    return isinstance(value, (str, int, float, bool)) or value is None


def format_input_path_label(rel_path: Any) -> Any:
    # Human-readable path label for row captions (e.g. stats.level, mails[0].to).
    if not rel_path:
        return "(value)"
    parts = []
    for token in rel_path:
        if isinstance(token, int):
            parts.append(f"[{token}]")
        else:
            token_text = str(token)
            if parts:
                parts.append(f".{token_text}")
            else:
                parts.append(token_text)
    return "".join(parts)


def collect_database_grades_matrix(
    value: Any,
    *,
    max_rows: int = 40,
    input_database_style_service: Any,
) -> Any:
    """Collect bounded Database Grades matrix payload for INPUT-mode rendering."""
    return input_database_style_service.collect_database_grades_matrix(
        value,
        max_rows=max_rows,
    )


def collect_database_bcc_payload(
    value: Any,
    *,
    max_rows: int = 200,
    input_database_bcc_style_service: Any,
) -> Any:
    """Collect bounded Database BCC table payload for INPUT-mode rendering."""
    return input_database_bcc_style_service.collect_database_bcc_payload(
        value,
        max_rows=max_rows,
    )


def collect_database_interpol_payload(
    value: Any,
    *,
    max_rows: int = 200,
    input_database_bcc_style_service: Any,
) -> Any:
    """Collect bounded Database INTERPOL table payload for INPUT-mode rendering."""
    return input_database_bcc_style_service.collect_database_interpol_payload(
        value,
        max_rows=max_rows,
    )


def database_grades_matrix_for_input_path(
    path: Any,
    value: Any,
    *,
    input_database_style_service: Any,
) -> Any:
    """Resolve Database Grades payload only for matching INPUT-path scopes."""
    normalized = list(path or [])
    if not normalized:
        return None
    if str(normalized[0]) != "Database":
        return None
    if len(normalized) == 1:
        return None
    if len(normalized) == 2 and isinstance(normalized[1], int):
        return collect_database_grades_matrix(
            value,
            input_database_style_service=input_database_style_service,
        )
    if len(normalized) >= 4 and str(normalized[2]) == "tables" and str(normalized[3]) == "Grades":
        return collect_database_grades_matrix(
            value,
            input_database_style_service=input_database_style_service,
        )
    return None


def database_bcc_payload_for_input_path(
    path: Any,
    value: Any,
    *,
    input_database_bcc_style_service: Any,
) -> Any:
    """Resolve Database BCC payload only for matching INPUT-path scopes."""
    normalized = list(path or [])
    if not normalized:
        return None
    if str(normalized[0]) != "Database":
        return None
    if len(normalized) == 2 and isinstance(normalized[1], int):
        return collect_database_bcc_payload(
            value,
            input_database_bcc_style_service=input_database_bcc_style_service,
        )
    if len(normalized) >= 4 and str(normalized[2]) == "tables" and str(normalized[3]).casefold() == "users":
        return collect_database_bcc_payload(
            value,
            input_database_bcc_style_service=input_database_bcc_style_service,
        )
    return None


def database_interpol_payload_for_input_path(
    path: Any,
    value: Any,
    *,
    input_database_bcc_style_service: Any,
) -> Any:
    """Resolve Database INTERPOL payload only for matching INPUT-path scopes."""
    normalized = list(path or [])
    if not normalized:
        return None
    if str(normalized[0]) != "Database":
        return None
    if len(normalized) == 2 and isinstance(normalized[1], int):
        return collect_database_interpol_payload(
            value,
            input_database_bcc_style_service=input_database_bcc_style_service,
        )
    if len(normalized) >= 4 and str(normalized[2]) == "tables" and str(normalized[3]).casefold() == "customers":
        return collect_database_interpol_payload(
            value,
            input_database_bcc_style_service=input_database_bcc_style_service,
        )
    return None


def is_network_router_input_style_payload(
    owner: Any,
    path: Any,
    value: Any,
    *,
    input_network_router_style_service: Any,
) -> bool:
    """Return whether payload matches the grouped Network ROUTER INPUT shape."""
    return bool(input_network_router_style_service.is_network_router_group_payload(owner, path, value))


def is_network_device_input_style_payload(owner: Any, path: Any, value: Any) -> bool:
    """Return whether payload is the root Network DEVICE collection for INPUT rendering."""
    normalized = list(path or [])
    if len(normalized) != 1:
        return False
    if owner._input_mode_root_key_for_path(normalized) != "network":
        return False
    if not isinstance(value, list) or not value:
        return False
    return all(isinstance(item, dict) and str(item.get("type", "")).upper() == "DEVICE" for item in value)


def is_network_firewall_input_style_payload(
    owner: Any,
    path: Any,
    value: Any,
    *,
    input_network_firewall_style_service: Any,
) -> bool:
    """Return whether payload matches grouped Network FIREWALL INPUT shape."""
    return bool(input_network_firewall_style_service.is_network_firewall_group_payload(owner, path, value))


def is_network_geoip_input_style_payload(
    owner: Any,
    path: Any,
    value: Any,
    *,
    input_network_device_geoip_style_service: Any,
) -> bool:
    """Return whether payload maps to Network DEVICE GEO IP INPUT shape."""
    return bool(input_network_device_geoip_style_service.is_network_geoip_payload(owner, path, value))


def is_network_bcc_domains_input_style_payload(
    owner: Any,
    path: Any,
    value: Any,
    *,
    input_network_device_bcc_style_service: Any,
) -> bool:
    """Return whether payload maps to locked Network BCC DOMAINS INPUT shape."""
    return bool(input_network_device_bcc_style_service.is_network_bcc_domains_payload(owner, path, value))


def is_network_blue_table_input_style_payload(
    owner: Any,
    path: Any,
    value: Any,
    *,
    input_network_device_bcc_style_service: Any,
) -> bool:
    """Return whether payload maps to locked Network BLUE TABLE INPUT shape."""
    return bool(input_network_device_bcc_style_service.is_network_blue_table_payload(owner, path, value))


def is_network_interpol_input_style_payload(
    owner: Any,
    path: Any,
    value: Any,
    *,
    input_network_device_bcc_style_service: Any,
) -> bool:
    """Return whether payload maps to locked Network INTERPOL INPUT shape."""
    return bool(input_network_device_bcc_style_service.is_network_interpol_payload(owner, path, value))


def collect_input_field_specs(value: Any, base_path: Any, max_fields: Any=24) -> Any:
    # Build a bounded list of editable scalar slots to keep INPUT view fast and stable.
    specs = []

    def add_spec(rel_path: Any, initial: Any) -> Any:
        if len(specs) >= max_fields:
            return
        specs.append(
            {
                "rel_path": list(rel_path),
                "abs_path": list(base_path) + list(rel_path),
                "initial": initial,
                "type": type(initial),
            }
        )

    if is_input_scalar(value):
        add_spec([], value)
        return specs

    if isinstance(value, dict):
        for key, child in value.items():
            if is_input_scalar(child):
                add_spec([key], child)
            elif isinstance(child, dict):
                for subkey, subval in child.items():
                    if is_input_scalar(subval):
                        add_spec([key, subkey], subval)
            elif isinstance(child, list) and child and isinstance(child[0], dict):
                for subkey, subval in child[0].items():
                    if is_input_scalar(subval):
                        add_spec([key, 0, subkey], subval)
        return specs

    if isinstance(value, list):
        if value and isinstance(value[0], dict):
            for subkey, subval in value[0].items():
                if is_input_scalar(subval):
                    add_spec([0, subkey], subval)
                elif isinstance(subval, dict):
                    for leaf_key, leaf_val in subval.items():
                        if is_input_scalar(leaf_val):
                            add_spec([0, subkey, leaf_key], leaf_val)
        elif value and is_input_scalar(value[0]):
            add_spec([0], value[0])
        return specs

    return specs


def set_nested_value(container: Any, rel_path: Any, new_value: Any) -> Any:
    # Apply a coerced value back into a nested dict/list path.
    # Raise ValueError for stale/invalid paths so INPUT Apply can show a safe warning.
    if not rel_path:
        return new_value

    target = container
    walked = []
    for idx, token in enumerate(rel_path[:-1]):
        walked.append(token)
        if isinstance(target, dict):
            if token not in target:
                raise ValueError(f"path not found at {walked!r}")
            target = target[token]
            continue
        if isinstance(target, list):
            if not isinstance(token, int) or token < 0:
                raise ValueError(f"list index out of range at {walked!r}")
            if token >= len(target):
                # INPUT-mode convenience: allow creating missing nested list slots
                # for child collections (for example empty ports -> ports[0].* fields).
                # Do not auto-grow at root-level list access to avoid stale-path writes.
                if idx == 0:
                    raise ValueError(f"list index out of range at {walked!r}")
                next_token = rel_path[idx + 1] if idx + 1 < len(rel_path) else None
                fill_value = {} if isinstance(next_token, str) else []
                while len(target) <= token:
                    target.append(fill_value.copy() if isinstance(fill_value, dict) else list(fill_value))
            target = target[token]
            continue
        raise ValueError(f"path type mismatch at {walked!r}")

    leaf = rel_path[-1]
    if isinstance(target, dict):
        # Dict leafs are allowed to be created on apply (e.g. missing ROUTER version).
        target[leaf] = new_value
        return container
    if isinstance(target, list):
        if not isinstance(leaf, int) or leaf < 0:
            raise ValueError(f"list index out of range at {list(rel_path)!r}")
        if leaf >= len(target):
            while len(target) <= leaf:
                target.append(None)
        target[leaf] = new_value
        return container
    raise ValueError(f"path type mismatch at {list(rel_path)!r}")


def strip_input_display_prefix(raw: Any) -> Any:
    # INPUT entries may include a visual left pad for alignment.
    value = str(raw)
    if value.startswith("  "):
        return value[2:]
    return value


def _normalize_numeric_text(raw: Any) -> str:
    # Accept common finance-style entry patterns (currency, grouping separators).
    text = str(raw).strip()
    if not text:
        return text
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    text = text.replace("$", "")
    if text.upper().startswith("USD"):
        text = text[3:]
    text = text.replace(",", "")
    text = text.replace(" ", "")
    return text.strip()


def _coerce_int_text(raw: Any) -> int:
    text = _normalize_numeric_text(raw)
    if text == "":
        raise ValueError("integer value is required")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid integer value: {raw!r}") from exc
    integral = value.to_integral_value()
    if value != integral:
        raise ValueError("integer value cannot include a fractional component")
    return int(integral)


def _coerce_float_text(raw: Any) -> float:
    text = _normalize_numeric_text(raw)
    if text == "":
        raise ValueError("numeric value is required")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid numeric value: {raw!r}") from exc
    return float(value)


def coerce_input_field_value(spec: Any) -> Any:
    # Convert StringVar input back to the original scalar type for safe write-back.
    expected_type = spec.get("type", str)
    var = spec.get("var")
    if var is None:
        return spec.get("initial")
    raw_display = strip_input_display_prefix(var.get())
    placeholder = spec.get("display_placeholder")
    if spec.get("placeholder_as_empty") and placeholder is not None:
        if str(raw_display).strip() == str(placeholder):
            raw_display = ""
    if expected_type is bool:
        raw = str(raw_display).strip().lower()
        if raw in ("true", "1", "yes", "on"):
            return True
        if raw in ("false", "0", "no", "off"):
            return False
        raise ValueError("boolean must be true/false")
    raw = raw_display
    if expected_type is int:
        return _coerce_int_text(raw)
    if expected_type is float:
        return _coerce_float_text(raw)
    if expected_type is type(None):
        return None if str(raw).strip() == "" else str(raw)
    return str(raw)


def deep_copy_json_compatible(value: Any) -> Any:
    # Avoid mutating live tree data while validating/applying INPUT edits.
    try:
        return json.loads(json.dumps(value, ensure_ascii=False))
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return value


def input_notice_fg(owner: Any) -> str:
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    return "#cdb6f7" if variant == "KAMUE" else "#9dc2e2"


def mark_input_mode_render_complete(owner: Any, normalized_path: Any) -> None:
    owner._input_mode_last_render_path_key = owner._input_mode_path_key(normalized_path)
    owner._input_mode_last_render_item = owner.tree.focus() if getattr(owner, "tree", None) is not None else None
    owner._input_mode_force_refresh = False


def show_input_mode_notice(
    owner: Any,
    host: Any,
    panel_bg: str,
    message: str,
    *,
    font_size: int,
    tk_module: Any,
):
    label = tk_module.Label(
        host,
        text=message,
        bg=panel_bg,
        fg=input_notice_fg(owner),
        anchor="w",
        justify="left",
        padx=12,
        pady=12,
        font=(owner._credit_name_font()[0], owner._input_mode_font_size(font_size, min_size=8, max_size=20), "bold"),
    )
    label.pack(fill="x", expand=False)
    owner._input_mode_no_fields_label = label
    return label


def _complete_input_render(owner: Any, normalized_path: Any) -> None:
    owner._refresh_input_mode_bool_widget_colors()
    owner._schedule_input_mode_layout_finalize(reset_scroll=True)
    mark_input_mode_render_complete(owner, normalized_path)


def _build_input_render_context(owner: Any, normalized_path: Any, value: Any) -> dict[str, Any]:
    database_grades_matrix = owner._database_grades_matrix_for_input_path(normalized_path, value)
    return {
        "root_key": owner._input_mode_root_key_for_path(normalized_path),
        "database_grades_matrix": database_grades_matrix,
        "database_bcc_payload": owner._database_bcc_payload_for_input_path(normalized_path, value),
        "database_interpol_payload": owner._database_interpol_payload_for_input_path(normalized_path, value),
        "is_database_payload": bool(database_grades_matrix),
        "is_network_router_payload": owner._is_network_router_input_style_payload(normalized_path, value),
        "is_network_bcc_domains_payload": owner._is_network_bcc_domains_input_style_payload(normalized_path, value),
        "is_network_blue_table_payload": owner._is_network_blue_table_input_style_payload(normalized_path, value),
        "is_network_interpol_payload": owner._is_network_interpol_input_style_payload(normalized_path, value),
        "is_network_geoip_payload": owner._is_network_geoip_input_style_payload(normalized_path, value),
        "is_network_device_payload": owner._is_network_device_input_style_payload(normalized_path, value),
        "is_network_firewall_payload": owner._is_network_firewall_input_style_payload(normalized_path, value),
    }


def _render_bank_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    value: Any,
    _context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    if not owner._is_bank_input_style_path(normalized_path):
        return False
    bank_rows = owner._collect_bank_input_rows(value)
    if not bank_rows:
        return False
    owner._render_bank_input_style_rows(host, normalized_path, bank_rows)
    _complete_input_render(owner, normalized_path)
    return True


def _render_database_bcc_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    _value: Any,
    context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    payload = context.get("database_bcc_payload")
    if not payload:
        return False
    owner._render_database_bcc_table(host, normalized_path, payload)
    _complete_input_render(owner, normalized_path)
    return True


def _render_database_interpol_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    _value: Any,
    context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    payload = context.get("database_interpol_payload")
    if not payload:
        return False
    owner._render_database_interpol_table(host, normalized_path, payload)
    _complete_input_render(owner, normalized_path)
    return True


def _render_database_grades_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    _value: Any,
    context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    if not owner._is_database_input_style_path(normalized_path):
        return False
    matrix_payload = context.get("database_grades_matrix")
    if not matrix_payload:
        return False
    owner._render_database_grades_input_matrix(host, normalized_path, matrix_payload)
    _complete_input_render(owner, normalized_path)
    return True


def _render_suspicion_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    value: Any,
    _context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    if not owner._is_suspicion_input_style_path(normalized_path):
        return False
    if not owner._render_suspicion_phone_input(host, normalized_path, value):
        return False
    _complete_input_render(owner, normalized_path)
    return True


def _render_phone_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    value: Any,
    _context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    if not owner._is_phone_input_style_path(normalized_path):
        return False
    if not owner._render_phone_preview_input(host, normalized_path, value):
        return False
    _complete_input_render(owner, normalized_path)
    return True


def _render_skypersky_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    value: Any,
    _context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    if not owner._is_skypersky_input_style_path(normalized_path):
        return False
    if not owner._render_skypersky_input(host, normalized_path, value):
        return False
    _complete_input_render(owner, normalized_path)
    return True


def _render_network_router_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    value: Any,
    context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    if not bool(context.get("is_network_router_payload")):
        return False
    router_rows = owner._collect_network_router_input_rows(normalized_path, value)
    if not router_rows:
        return False
    owner._render_network_router_input_rows(
        host,
        normalized_path,
        router_rows,
        start_index=0,
        finalize=True,
        total_rows=len(router_rows),
    )
    owner._clear_router_virtual_state()
    _complete_input_render(owner, normalized_path)
    return True


def _render_network_firewall_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    value: Any,
    context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    if not bool(context.get("is_network_firewall_payload")):
        return False
    firewall_rows = owner._collect_network_firewall_input_rows(normalized_path, value)
    if not firewall_rows:
        return False
    owner._render_network_firewall_input_rows(host, normalized_path, firewall_rows)
    _complete_input_render(owner, normalized_path)
    return True


def _render_network_bcc_domains_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    value: Any,
    context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    if not bool(context.get("is_network_bcc_domains_payload")):
        return False
    payload = owner._collect_network_bcc_domains_payload(normalized_path, value)
    if not payload:
        return False
    owner._render_network_bcc_domains_input(host, normalized_path, payload)
    _complete_input_render(owner, normalized_path)
    return True


def _render_network_blue_table_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    value: Any,
    context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    if not bool(context.get("is_network_blue_table_payload")):
        return False
    payload = owner._collect_network_blue_table_payload(normalized_path, value)
    if not payload:
        return False
    owner._render_network_blue_table_input(host, normalized_path, payload)
    _complete_input_render(owner, normalized_path)
    return True


def _render_network_interpol_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    value: Any,
    context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    if not bool(context.get("is_network_interpol_payload")):
        return False
    payload = owner._collect_network_interpol_payload(normalized_path, value)
    if not payload:
        return False
    owner._render_network_interpol_input(host, normalized_path, payload)
    _complete_input_render(owner, normalized_path)
    return True


def _render_network_geoip_payload(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    value: Any,
    context: dict[str, Any],
    _panel_bg: str,
    _tk_module: Any,
) -> bool:
    if not bool(context.get("is_network_geoip_payload")):
        return False
    payload = owner._collect_network_geoip_payload(normalized_path, value)
    if not payload:
        return False
    owner._render_network_geoip_input(host, normalized_path, payload)
    _complete_input_render(owner, normalized_path)
    return True


def _render_network_device_placeholder(
    owner: Any,
    host: Any,
    normalized_path: list[Any],
    _value: Any,
    context: dict[str, Any],
    panel_bg: str,
    tk_module: Any,
) -> bool:
    if not bool(context.get("is_network_device_payload")):
        return False
    show_input_mode_notice(
        owner,
        host,
        panel_bg,
        "Selected A Sub Category",
        font_size=11,
        tk_module=tk_module,
    )
    mark_input_mode_render_complete(owner, normalized_path)
    return True


_INPUT_RENDER_REGISTRY: dict[str, Any] = {
    "bank": _render_bank_payload,
    "database_bcc": _render_database_bcc_payload,
    "database_interpol": _render_database_interpol_payload,
    "database_grades": _render_database_grades_payload,
    "suspicion": _render_suspicion_payload,
    "phone": _render_phone_payload,
    "skypersky": _render_skypersky_payload,
    "network_router": _render_network_router_payload,
    "network_firewall": _render_network_firewall_payload,
    "network_bcc_domains": _render_network_bcc_domains_payload,
    "network_blue_table": _render_network_blue_table_payload,
    "network_interpol": _render_network_interpol_payload,
    "network_geoip": _render_network_geoip_payload,
    "network_device_placeholder": _render_network_device_placeholder,
}


def render_payload(
    owner: Any,
    path: Any,
    value: Any,
    *,
    host: Any = None,
    panel_bg: str | None = None,
    tk_module: Any = None,
) -> bool:
    normalized_path = list(path or [])
    target_host = host if host is not None else getattr(owner, "_input_mode_fields_host", None)
    if target_host is None:
        return False
    if panel_bg is None:
        theme = getattr(owner, "_theme", {}) or {}
        panel_bg = str(theme.get("panel", "#161b24"))
    if tk_module is None:
        tk_module = tk

    context = _build_input_render_context(owner, normalized_path, value)
    root_key = str(context.get("root_key", ""))
    if owner._is_input_mode_category_disabled(normalized_path):
        show_input_mode_notice(
            owner,
            target_host,
            panel_bg,
            owner.INPUT_MODE_DISABLED_CATEGORY_MESSAGE,
            font_size=11,
            tk_module=tk_module,
        )
        mark_input_mode_render_complete(owner, normalized_path)
        return True
    if len(normalized_path) == 0:
        has_data = getattr(owner, "data", None) is not None
        message = (
            "No direct value fields here. Select a specific item node to edit."
            if has_data
            else "No File Loaded. Open A .HHSAV File Before Continuing."
        )
        show_input_mode_notice(
            owner,
            target_host,
            panel_bg,
            message,
            font_size=9,
            tk_module=tk_module,
        )
        return True
    if len(normalized_path) == 1 and root_key == "network":
        has_custom_network_payload = any(
            bool(context.get(flag))
            for flag in ("is_network_router_payload", "is_network_device_payload", "is_network_firewall_payload")
        )
        if not has_custom_network_payload:
            show_input_mode_notice(
                owner,
                target_host,
                panel_bg,
                "Select A Sub Category To View Input Fields",
                font_size=11,
                tk_module=tk_module,
            )
            mark_input_mode_render_complete(owner, normalized_path)
            return True
    if len(normalized_path) == 1 and root_key == "database":
        show_input_mode_notice(
            owner,
            target_host,
            panel_bg,
            "Select A Sub Category To View Input Fields",
            font_size=11,
            tk_module=tk_module,
        )
        mark_input_mode_render_complete(owner, normalized_path)
        return True

    for handler in _INPUT_RENDER_REGISTRY.values():
        if handler(owner, target_host, normalized_path, value, context, panel_bg, tk_module):
            return True
    show_input_mode_notice(
        owner,
        target_host,
        panel_bg,
        owner.INPUT_MODE_DISABLED_CATEGORY_MESSAGE,
        font_size=11,
        tk_module=tk_module,
    )
    mark_input_mode_render_complete(owner, normalized_path)
    return True


def _is_bank_input_style_path(self, path):
    normalized = list(path or [])
    if len(normalized) != 1:
        return False
    return self._input_mode_root_key_for_path(normalized) == "bank"

def _render_bank_input_style_rows(self, host, normalized_path, row_defs):
    input_bank_style_service.render_bank_input_style_rows(
        self,
        host,
        normalized_path,
        row_defs,
    )

def _render_database_grades_input_matrix(self, host, normalized_path, matrix_payload):
    input_database_style_service.render_database_grades_matrix(
        self,
        host,
        normalized_path,
        matrix_payload,
    )

def _render_database_bcc_table(self, host, normalized_path, payload):
    input_database_bcc_style_service.render_database_bcc_table(
        self,
        host,
        normalized_path,
        payload,
    )

def _render_database_interpol_table(self, host, normalized_path, payload):
    input_database_bcc_style_service.render_database_interpol_table(
        self,
        host,
        normalized_path,
        payload,
    )

def _render_network_bcc_domains_input(self, host, normalized_path, payload):
    input_network_device_bcc_style_service.render_bcc_domains_input(self, host, normalized_path, payload)

def _render_network_blue_table_input(self, host, normalized_path, payload):
    input_network_device_bcc_style_service.render_blue_table_input(self, host, normalized_path, payload)

def _render_network_interpol_input(self, host, normalized_path, payload):
    input_network_device_bcc_style_service.render_interpol_input(self, host, normalized_path, payload)

def _render_network_geoip_input(self, host, normalized_path, payload):
    input_network_device_geoip_style_service.render_geoip_input(self, host, normalized_path, payload)

def _render_network_firewall_input_rows(self, host, normalized_path, row_defs):
    input_network_firewall_style_service.render_firewall_input_rows(
        self,
        host,
        normalized_path,
        row_defs,
    )

def _render_network_router_input_rows(
    self,
    host,
    normalized_path,
    row_defs,
    *,
    start_index=0,
    finalize=False,
    total_rows=None,
):
    input_network_router_style_service.render_router_input_rows(
        self,
        host,
        normalized_path,
        row_defs,
        start_index=start_index,
        finalize=bool(finalize),
        total_rows=total_rows,
    )

def _run_router_input_prewarm(self):
    self._input_mode_router_prewarm_after_id = None
    if str(getattr(self, "_editor_mode", "JSON")).upper() == "INPUT":
        return
    if bool(self._is_document_load_cooldown_active()):
        root = getattr(self, "root", None)
        if root is not None:
            try:
                delay_ms = max(120, int(getattr(self, "_router_input_prewarm_delay_ms", 180) or 180))
                self._input_mode_router_prewarm_after_id = root.after(delay_ms, self._run_router_input_prewarm)
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                self._input_mode_router_prewarm_after_id = None
        return
    try:
        self._prewarm_input_mode_assets()
    except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
        pass
    host = getattr(self, "_input_mode_fields_host", None)
    if host is None:
        return
    data = getattr(self, "data", None)
    if not isinstance(data, dict):
        return
    network = data.get("Network")
    if not isinstance(network, list) or not network:
        return
    routers = [
        item for item in network
        if isinstance(item, dict) and str(item.get("type", "")).upper() == "ROUTER"
    ]
    if not routers:
        return
    max_rows = max(1, int(getattr(self, "_router_input_max_rows", 60) or 60))
    rows = self._collect_network_router_input_rows(["Network"], routers, max_rows=max_rows)
    if not rows:
        return
    # Prewarm enough pooled rows to keep first ROUTER open smooth without scroll-time injection.
    prewarm_limit = max(
        1,
        min(
            len(rows),
            int(getattr(self, "_router_input_prewarm_row_limit_cap", max_rows) or max_rows),
            int(getattr(self, "_router_input_prewarm_row_limit", max_rows) or max_rows),
        ),
    )
    prewarm_rows = list(rows[:prewarm_limit])
    if not prewarm_rows:
        return
    input_network_router_style_service.prepare_router_render_host(self, host, reset_pool=True)
    self._render_network_router_input_rows(
        host,
        ["Network"],
        prewarm_rows,
        start_index=0,
        finalize=True,
        total_rows=len(prewarm_rows),
    )
    input_network_router_style_service.suspend_router_render_host(self, host)
    self._input_mode_field_specs = []
    self._input_mode_router_virtual_rows = []
    self._input_mode_router_virtual_next_index = 0
    self._input_mode_router_virtual_total_rows = 0

def _schedule_router_input_prewarm(self):
    self._cancel_pending_router_input_prewarm()
    if str(getattr(self, "_editor_mode", "JSON")).upper() == "INPUT":
        return
    root = getattr(self, "root", None)
    if root is None:
        self._run_router_input_prewarm()
        return
    try:
        # Defer prewarm so open-file flow returns before non-critical cache work.
        delay_ms = max(100, int(getattr(self, "_router_input_prewarm_delay_ms", 180) or 180))
        self._input_mode_router_prewarm_after_id = root.after(delay_ms, self._run_router_input_prewarm)
    except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
        self._input_mode_router_prewarm_after_id = None

def _run_router_settle_barrier(self):
    self._input_mode_router_settle_after_id = None
    if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
        return
    start_time = time.perf_counter()
    budget_seconds = 0.12
    while (time.perf_counter() - start_time) < budget_seconds:
        progressed = self._maybe_render_more_router_rows(force_prefetch=True, origin="settle")
        if not progressed:
            break
    if int(getattr(self, "_input_mode_router_virtual_next_index", 0) or 0) < int(
        getattr(self, "_input_mode_router_virtual_total_rows", 0) or 0
    ):
        self._schedule_router_virtual_check(delay_ms=20)

def _maybe_render_more_router_rows(self, force_prefetch=False, origin="idle"):
    self._input_mode_router_virtual_after_id = None
    if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
        return False
    host = getattr(self, "_input_mode_fields_host", None)
    canvas = getattr(self, "_input_mode_canvas", None)
    if host is None or canvas is None:
        return False
    rows = list(getattr(self, "_input_mode_router_virtual_rows", []) or [])
    next_index = int(getattr(self, "_input_mode_router_virtual_next_index", 0) or 0)
    total_rows = int(getattr(self, "_input_mode_router_virtual_total_rows", 0) or 0)
    if not rows or next_index >= total_rows:
        return False
    try:
        _y0, y1 = canvas.yview()
    except (tk.TclError, RuntimeError, ValueError, TypeError, AttributeError):
        y1 = 1.0
    # Keep a prefetch band so wheel/drag scroll does not outrun row materialization.
    if y1 < self._router_virtual_prefetch_threshold(force_prefetch=bool(force_prefetch)):
        return False
    backlog = max(0, total_rows - next_index)
    chunk_size = self._router_virtual_chunk_size(backlog)
    chunk = rows[next_index : next_index + chunk_size]
    if not chunk:
        return False
    final_index = next_index + len(chunk)
    self._render_network_router_input_rows(
        host,
        self._input_mode_current_path,
        chunk,
        start_index=next_index,
        finalize=final_index >= total_rows,
        total_rows=total_rows,
    )
    self._schedule_input_mode_layout_finalize(reset_scroll=False)
    self._input_mode_router_virtual_next_index = final_index
    if final_index < total_rows:
        next_delay = 12 if bool(getattr(self, "_input_mode_scroll_drag_active", False)) else 24
        if str(origin).lower() == "settle":
            next_delay = 8
        self._schedule_router_virtual_check(delay_ms=next_delay)
        return True
    self._clear_router_virtual_state()
    return True

def _schedule_router_input_render_batches(
    self,
    host,
    normalized_path,
    pending_rows,
    render_token,
    chunk_size=10,
    start_index=0,
    total_rows=None,
):
    if not pending_rows:
        return
    root = getattr(self, "root", None)
    if root is None:
        return

    def _run_next_batch():
        self._input_mode_router_batch_after_id = None
        if render_token != int(getattr(self, "_input_mode_render_token", 0) or 0):
            return
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
            return
        rows = list(pending_rows or [])
        if not rows:
            return
        chunk = rows[:chunk_size]
        rest = rows[chunk_size:]
        self._render_network_router_input_rows(
            host,
            normalized_path,
            chunk,
            start_index=start_index,
            finalize=not bool(rest),
            total_rows=total_rows,
        )
        if rest and render_token == int(getattr(self, "_input_mode_render_token", 0) or 0):
            self._schedule_router_input_render_batches(
                host,
                normalized_path,
                rest,
                render_token,
                chunk_size=chunk_size,
                start_index=start_index + len(chunk),
                total_rows=total_rows,
            )
            return
        # Finalize once at the end to avoid repeated full-host relayout cost.
        self._refresh_input_mode_bool_widget_colors()
        self._schedule_input_mode_layout_finalize(reset_scroll=False)

    try:
        self._input_mode_router_batch_after_id = root.after_idle(_run_next_batch)
    except (tk.TclError, RuntimeError, AttributeError):
        self._input_mode_router_batch_after_id = None

def _refresh_editor_mode_view(self):
    text = getattr(self, "text", None)
    text_scroll = getattr(self, "_text_scroll", None)
    input_container = getattr(self, "_input_mode_container", None)
    if text is None or input_container is None or text_scroll is None:
        return
    mode = str(getattr(self, "_editor_mode", "JSON")).upper()
    self._sync_input_mode_paned_sash_lock(mode)
    self._apply_tree_mode_style(mode)
    show_input = (mode == "INPUT")
    editor_mode_top_inset = 24
    if show_input:
        # Enforce INPUT no-expand policy on mode entry so JSON-expanded branches
        # (for example Bank children opened via Find Next) do not remain visible.
        self._enforce_input_tree_expand_locks()
        try:
            text.pack_forget()
            text_scroll.pack_forget()
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        if not input_container.winfo_ismapped():
            input_container.pack(fill="both", expand=True, side="left", pady=(editor_mode_top_inset, 0))
        item_id = self.tree.focus() if getattr(self, "tree", None) is not None else None
        self._schedule_input_mode_refresh(item_id=item_id, immediate=True)
        return

    try:
        self._cancel_pending_input_mode_refresh()
        self._cancel_pending_router_input_batches()
        self._clear_router_virtual_state()
        self._cancel_pending_input_mode_layout_finalize()
        input_container.pack_forget()
    except (tk.TclError, RuntimeError, AttributeError):
        pass
    if not text.winfo_ismapped():
        text.pack(fill="both", expand=True, side="left", pady=(editor_mode_top_inset, 0))
    if not text_scroll.winfo_ismapped():
        text_scroll.pack(fill="y", side="right", pady=(editor_mode_top_inset, 0))
    if getattr(self, "data", None) is None:
        self._show_json_no_file_message()

def _network_group_for_list_index(self, list_path, row_index):
    TREE_NAV = getattr(self, "TREE_NAV", None)
    if TREE_NAV is None:
        TREE_NAV = tree_navigation_service.bind(
            self,
            expected_errors=_EXPECTED_APP_ERRORS,
        )
        self.TREE_NAV = TREE_NAV
    return TREE_NAV.get_group_for_index(list_path, row_index)
