def theme_palette_for_variant(variant):
    use_variant = str(variant).upper()
    if use_variant == "KAMUE":
        return {
            "bg": "#06040d",
            "fg": "#e9e2f6",
            "tree_fg": "#ead9ff",
            "tree_selected_fg": "#ffffff",
            "panel": "#0d061c",
            "accent": "#180c31",
            "button_active": "#25124f",
            "button_pressed": "#0f071f",
            "select_bg": "#2d155f",
            "select_fg": "#ffffff",
            "title_bar_bg": "#180c32",
            "title_bar_fg": "#eee8ff",
            "title_bar_border": "#30195c",
            "credit_bg": "#06030d",
            "credit_border": "#170c31",
            "credit_label_fg": "#c9b9e8",
            "find_border": "#cfb5ee",
            "logo_border_outer": "#6b37b6",
            "logo_border_inner": "#b678ea",
        }
    return {
        "bg": "#0f131a",
        "fg": "#e6e6e6",
        "tree_fg": "#d7f2ff",
        "tree_selected_fg": "#ffffff",
        "panel": "#161b24",
        "accent": "#2a3342",
        "button_active": "#3a465c",
        "button_pressed": "#222a36",
        "select_bg": "#2f3a4d",
        "select_fg": "#ffffff",
        "title_bar_bg": "#122639",
        "title_bar_fg": "#d7ebf7",
        "title_bar_border": "#264b64",
        "credit_bg": "#0b1118",
        "credit_border": "#1f2f3f",
        "credit_label_fg": "#b5cade",
        "find_border": "#ffffff",
        "logo_border_outer": "#349fc7",
        "logo_border_inner": "#a9ddf0",
    }


def theme_chip_palette(variant):
    use_variant = str(variant).upper()
    if use_variant == "KAMUE":
        return {"bg": "#2a1450", "fg": "#e7dcff", "border": "#6b37b6"}
    return {"bg": "#132230", "fg": "#d4e3ee", "border": "#4e6e86"}


def tree_variant_chip_palette(variant):
    use_variant = str(variant).upper()
    if use_variant == "B":
        return {"bg": "#173042", "fg": "#e8f5ff", "border": "#6bbde3"}
    return {"bg": "#0f1b29", "fg": "#9db9cf", "border": "#2f4a61"}


def bug_chip_palette(variant, footer_style_variant="B"):
    use_variant = str(variant).upper()
    use_footer = str(footer_style_variant).upper()
    if use_footer == "B":
        if use_variant == "KAMUE":
            return {"bg": "#2a1450", "fg": "#f0e7ff", "border": "#6b37b6", "active_bg": "#2a1450"}
        return {"bg": "#132230", "fg": "#e6f6ff", "border": "#4e6e86", "active_bg": "#132230"}
    if use_variant == "KAMUE":
        return {"bg": "#23103c", "fg": "#f0e6ff", "border": "#6b37b6", "active_bg": "#4a2781"}
    return {"bg": "#10212f", "fg": "#e6f6ff", "border": "#4e6e86", "active_bg": "#1f4a67"}


def footer_badge_palette(variant, footer_style_variant="B"):
    use_variant = str(variant).upper()
    use_footer = str(footer_style_variant).upper()
    if use_footer == "B":
        if use_variant == "KAMUE":
            return {"bg": "#2a1450", "fg": "#d8ccec", "border": "#6b37b6"}
        return {"bg": "#132230", "fg": "#c2d4e2", "border": "#4e6e86"}
    if use_variant == "KAMUE":
        return {"bg": "#2a1450", "fg": "#d8ccec", "border": "#6b37b6"}
    return {"bg": "#132230", "fg": "#c2d4e2", "border": "#4e6e86"}


def tree_marker_palette(theme_variant):
    if str(theme_variant).upper() == "KAMUE":
        return {
            "main_fill": "#b57bff",
            "main_edge": "#ecd8ff",
            "sub_edge": "#d5b8ff",
            "sub_fill": "#dcbfff",
        }
    return {
        "main_fill": "#6ecdf6",
        "main_edge": "#b8ecff",
        "sub_edge": "#9fdcf7",
        "sub_fill": "#8fe7ff",
    }
