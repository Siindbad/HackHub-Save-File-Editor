def resolve_siindbad_effective_style(
    style_focus,
    show_toolbar_variant_controls,
    app_theme_variant,
    style_map,
):
    focus = str(style_focus or "").upper()
    if focus in ("A", "B"):
        return focus
    if not bool(show_toolbar_variant_controls):
        return "B"
    theme_variant = str(app_theme_variant or "SIINDBAD").upper()
    use_map = style_map if isinstance(style_map, dict) else {"SIINDBAD": "B", "KAMUE": "B"}
    variant = str(use_map.get(theme_variant, "B")).upper()
    if variant not in ("A", "B"):
        variant = "B"
    return variant


def siindbad_toolbar_button_symbol(style, key):
    use_style = str(style or "").upper()
    sets = {
        "A": {
            "open": "\u27A4",
            "apply": "\u270E",
            "export": "\u2913",
            "find": "\u2315",
            "update": "\u21BB",
            "readme": "\u24D8",
        },
        "B": {
            "open": "\u25B8",
            "apply": "\u270E",
            "export": "\u21E9",
            "find": "\u2315",
            "update": "\u27F3",
            "readme": "\u2139",
        },
    }
    return sets.get(use_style, sets["A"]).get(str(key or ""), "")


def siindbad_toolbar_label_text(style, key, text):
    if str(style or "").upper() not in ("A", "B"):
        return str(text)
    labels = {
        "open": "OPEN",
        "apply": "APPLY EDIT",
        "export": "EXPORT .HHSAV",
        "find": "FIND NEXT",
        "update": "UPDATE",
        "readme": "README",
    }
    return labels.get(str(key or ""), str(text).upper())


def siindbad_toolbar_button_width(style, key, text):
    use_style = str(style or "").upper()
    if use_style == "A":
        widths = {
            "open": 92,
            "apply": 96,
            "export": 126,
            "find": 92,
            "update": 84,
            "readme": 84,
        }
    elif use_style == "B":
        widths = {
            "open": 10,
            "apply": 12,
            "export": 14,
            "find": 11,
            "update": 9,
            "readme": 9,
        }
    else:
        widths = {
            "open": 11,
            "apply": 13,
            "export": 15,
            "find": 12,
            "update": 10,
            "readme": 10,
        }
    use_key = str(key or "")
    if use_key in widths:
        return widths[use_key]
    return max(8, min(16, len(str(text)) + 2))
