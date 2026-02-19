def footer_style_variant():
    # Approved footer style policy: Variant-B visuals.
    return "B"


def footer_visual_spec(mode):
    use_mode = str(mode or "").upper()
    if use_mode == "B":
        return {
            "chip_icon_size": 10,
            "chip_icon_left_pad": 6,
            "chip_icon_gap": 4,
            "chip_text_right_pad": 6,
            "chip_text_pady": 0,
            "chip_gap": 4,
            "label_gap": 5,
            "theme_chip_padx": 7,
            "theme_chip_pady": 1,
            "theme_chip_gap": 4,
        }
    return {
        "chip_icon_size": 11,
        "chip_icon_left_pad": 8,
        "chip_icon_gap": 3,
        "chip_text_right_pad": 8,
        "chip_text_pady": 1,
        "chip_gap": 5,
        "label_gap": 6,
        "theme_chip_padx": 8,
        "theme_chip_pady": 1,
        "theme_chip_gap": 5,
    }
