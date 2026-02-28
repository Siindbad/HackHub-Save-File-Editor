import json
from decimal import Decimal, InvalidOperation
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


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
