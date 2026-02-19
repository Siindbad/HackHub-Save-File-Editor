def parse_suggestion_before_after(message):
    before = None
    after = None
    for raw_line in str(message or "").splitlines():
        line = raw_line.strip()
        if line.startswith("- Before:"):
            before = line.split(":", 1)[1].strip()
        elif line.startswith("- After:"):
            after = line.split(":", 1)[1].strip()
    return before, after


def build_overlay_suggestion_payload(has_overlay, message, line_no):
    if not has_overlay:
        return None
    msg = str(message or "")
    if not msg:
        return None
    before, after = parse_suggestion_before_after(msg)
    if after is None:
        return None
    if not line_no:
        return None
    return {"line": int(line_no), "before": before, "after": after}


def error_symbol_notes():
    return {
        "invalid_symbol_after_open",
        "invalid_trailing_symbol_after_closer",
        "invalid_trailing_symbol_after_value",
        "illegal_trailing_comma_before_close",
        "illegal_comma_after_top_level_close",
        "wrong_object_open_symbol",
        "wrong_list_open_for_object",
    }


def is_symbol_error_note(note):
    return str(note or "").startswith("symbol_") or str(note or "") in error_symbol_notes()


def error_marker_colors(note, palette, insertion_only=False):
    if is_symbol_error_note(note):
        # Keep wrong-symbol marker distinct and readable across themes.
        return "#5a0f16", "#ffdce1"
    if insertion_only:
        # Subtle insertion marker so EOF fixes do not flash bright cyan/violet blocks.
        return palette.get("insert_bg", palette.get("line_bg", palette["fix_bg"])), "#ffffff"
    return palette["fix_bg"], "#ffffff"


def current_error_palette(variant, theme):
    theme = theme if isinstance(theme, dict) else {}
    name = str(variant or "SIINDBAD").upper()
    if name == "KAMUE":
        return {
            "fix_bg": "#3e2d5a",
            "line_bg": "#241038",
            "insert_bg": "#3e2d5a",
            "border": theme.get("logo_border_outer", "#6b37b6"),
            "tint_bg": "#090512",
            "tint_fg": "#8a72a6",
            "overlay_bg": "#0f071a",
            "overlay_fg": "#f0e7ff",
            "drag_sel_bg": "#4a2d72",
            "drag_sel_fg": "#ffffff",
        }
    return {
        "fix_bg": "#2c4f64",
        "line_bg": "#123B4A",
        "insert_bg": "#2c4f64",
        "border": "#123B4A",
        "tint_bg": "#070d17",
        "tint_fg": "#5f7388",
        "overlay_bg": "#11161f",
        "overlay_fg": "#ffffff",
        "drag_sel_bg": "#2e4e67",
        "drag_sel_fg": "#ffffff",
    }


def selection_colors(theme, use_error_palette=False, error_palette=None):
    source_theme = theme if isinstance(theme, dict) else {}
    if use_error_palette and isinstance(error_palette, dict):
        sel_bg = error_palette.get("drag_sel_bg", source_theme.get("select_bg", "#2f3a4d"))
        sel_fg = error_palette.get("drag_sel_fg", source_theme.get("select_fg", "#ffffff"))
        return sel_bg, sel_fg
    return source_theme.get("select_bg", "#2f3a4d"), source_theme.get("select_fg", "#ffffff")
