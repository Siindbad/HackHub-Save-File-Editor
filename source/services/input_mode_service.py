import json


def is_input_scalar(value):
    # INPUT mode only renders direct scalar leaves as editable fields.
    return isinstance(value, (str, int, float, bool)) or value is None


def format_input_path_label(rel_path):
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


def collect_input_field_specs(value, base_path, max_fields=24):
    # Build a bounded list of editable scalar slots to keep INPUT view fast and stable.
    specs = []

    def add_spec(rel_path, initial):
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


def set_nested_value(container, rel_path, new_value):
    # Apply a coerced value back into a nested dict/list path.
    target = container
    for token in rel_path[:-1]:
        target = target[token]
    if rel_path:
        target[rel_path[-1]] = new_value
    else:
        return new_value
    return container


def strip_input_display_prefix(raw):
    # INPUT entries may include a visual left pad for alignment.
    value = str(raw)
    if value.startswith("  "):
        return value[2:]
    return value


def coerce_input_field_value(spec):
    # Convert StringVar input back to the original scalar type for safe write-back.
    expected_type = spec.get("type", str)
    var = spec.get("var")
    if var is None:
        return spec.get("initial")
    if expected_type is bool:
        raw = strip_input_display_prefix(var.get()).strip().lower()
        if raw in ("true", "1", "yes", "on"):
            return True
        if raw in ("false", "0", "no", "off"):
            return False
        raise ValueError("boolean must be true/false")
    raw = strip_input_display_prefix(var.get())
    if expected_type is int:
        return int(raw)
    if expected_type is float:
        return float(raw)
    if expected_type is type(None):
        return None if str(raw).strip() == "" else str(raw)
    return str(raw)


def deep_copy_json_compatible(value):
    # Avoid mutating live tree data while validating/applying INPUT edits.
    try:
        return json.loads(json.dumps(value, ensure_ascii=False))
    except Exception:
        return value
