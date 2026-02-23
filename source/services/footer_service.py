from tkinter import ttk
import tkinter as tk
import hashlib
import time
import sys
import os
import importlib
from typing import Any
from core.exceptions import EXPECTED_ERRORS

def footer_style_variant() -> Any:
    # Approved footer style policy: Variant-B visuals.
    return "B"


def footer_visual_spec(mode: Any) -> Any:
    use_mode = str(mode or "").upper()
    match use_mode:
        case "B":
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
        case _:
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


def _apply_footer_layout_variant(owner: Any):
        bar = getattr(owner, "_credit_bar", None)
        content = getattr(owner, "_credit_content", None)
        left_slot = getattr(owner, "_credit_left_slot", None)
        center_slot = getattr(owner, "_credit_center_slot", None)
        right_slot = getattr(owner, "_credit_right_slot", None)
        if bar is None or content is None or left_slot is None or center_slot is None or right_slot is None:
            return
        try:
            if not (bar.winfo_exists() and content.winfo_exists()):
                return
        except EXPECTED_ERRORS:
            return

        is_b = owner._footer_style_variant() == "B"
        try:
            # Keep content owned by left slot; only adjust grid placement for alignment.
            if not content.winfo_manager():
                content.pack(side="left")
        except EXPECTED_ERRORS:
            pass

        if is_b:
            try:
                center_slot.grid_remove()
                right_slot.grid_remove()
            except EXPECTED_ERRORS:
                pass
            try:
                left_slot.grid_configure(column=0, columnspan=3, sticky="ew", padx=(6, 6), pady=(1, 1))
                bar.grid_columnconfigure(0, weight=1)
                bar.grid_columnconfigure(1, weight=0)
                bar.grid_columnconfigure(2, weight=0)
                content.pack_configure(side="left", fill="none", expand=False)
            except EXPECTED_ERRORS:
                pass
        else:
            try:
                left_slot.grid_configure(column=0, columnspan=1, sticky="w", padx=(6, 0), pady=(1, 1))
                center_slot.grid(row=0, column=1, sticky="ew", pady=(1, 1))
                right_slot.grid(row=0, column=2, sticky="e", padx=(0, 6), pady=(1, 1))
                bar.grid_columnconfigure(0, weight=0)
                bar.grid_columnconfigure(1, weight=1)
                bar.grid_columnconfigure(2, weight=0)
                content.pack_configure(side="left", fill="none", expand=False)
            except EXPECTED_ERRORS:
                pass

        divider_pad = (5, 4) if is_b else (8, 6)
        left_side_widgets = (
            getattr(owner, "_credit_badge_host", None),
            getattr(owner, "_credit_badges_divider", None),
            getattr(owner, "_credit_discord_badge_host", None),
            getattr(owner, "_credit_discord_divider", None),
            getattr(owner, "_bug_report_host", None),
            getattr(owner, "_credit_theme_divider", None),
            getattr(owner, "_theme_selector_host", None),
        )
        for widget in left_side_widgets:
            if widget is None:
                continue
            try:
                if widget.winfo_exists():
                    widget.pack_configure(side="left")
            except EXPECTED_ERRORS:
                continue
        for divider in (
            getattr(owner, "_credit_badges_divider", None),
            getattr(owner, "_credit_discord_divider", None),
            getattr(owner, "_credit_theme_divider", None),
        ):
            if divider is None:
                continue
            try:
                if divider.winfo_exists():
                    divider.pack_configure(padx=divider_pad)
            except EXPECTED_ERRORS:
                continue


def _extract_badge_boxes(image, threshold=16):
        rgb = image.convert("RGB")
        width, height = rgb.size
        pixels = rgb.load()
        min_row_pixels = max(8, width // 60)
        min_group_height = max(20, height // 20)

        def row_lit_count(y):
            lit = 0
            for x in range(width):
                if max(pixels[x, y]) > threshold:
                    lit += 1
            return lit

        def box_for_rows(y1, y2):
            x1, x2 = width, -1
            for yy in range(y1, y2 + 1):
                for xx in range(width):
                    if max(pixels[xx, yy]) > threshold:
                        if xx < x1:
                            x1 = xx
                        if xx > x2:
                            x2 = xx
            if x2 < x1:
                return None
            pad = 4
            return (
                max(0, x1 - pad),
                max(0, y1 - pad),
                min(width, x2 + pad + 1),
                min(height, y2 + pad + 1),
            )

        row_has = [row_lit_count(y) >= min_row_pixels for y in range(height)]
        groups = []
        y = 0
        while y < height:
            while y < height and not row_has[y]:
                y += 1
            if y >= height:
                break
            start = y
            while y < height and row_has[y]:
                y += 1
            end = y - 1
            if end - start + 1 >= min_group_height:
                groups.append((start, end))

        boxes = []
        for start, end in groups:
            box = box_for_rows(start, end)
            if not box:
                continue
            area = (box[2] - box[0]) * (box[3] - box[1])
            if area >= 20000:
                boxes.append(box)

        if len(boxes) < 2:
            halves = ((0, height // 2), (height // 2, height))
            split_boxes = []
            for y_start, y_end in halves:
                top = None
                bottom = None
                for yy in range(y_start, y_end):
                    if row_lit_count(yy) >= min_row_pixels:
                        if top is None:
                            top = yy
                        bottom = yy
                if top is None or bottom is None:
                    continue
                box = box_for_rows(top, bottom)
                if not box:
                    continue
                area = (box[2] - box[0]) * (box[3] - box[1])
                if area >= 20000:
                    split_boxes.append(box)
            boxes = split_boxes

        if len(boxes) > 2:
            boxes = sorted(
                boxes,
                key=lambda b: (b[2] - b[0]) * (b[3] - b[1]),
                reverse=True,
            )[:2]
        boxes.sort(key=lambda b: b[1])
        return boxes


def _load_credit_github_icon(owner: Any, max_size=16, tint="#dff6ff", with_plate=False):
        cache = getattr(owner, "_credit_github_icon_cache", None)
        if cache is None:
            cache = {}
            owner._credit_github_icon_cache = cache
        signature = (int(max_size), str(tint), bool(with_plate))
        cached = cache.get(signature)
        if cached is not None:
            return cached
        base_dir = owner._resource_base_dir()
        candidates = [
            os.path.join(base_dir, "assets", "buttons", "github_mark_official.png"),
            os.path.join(base_dir, "assets", "buttons", "github_mark_octicons.png"),
        ]
        icon_path = next((path for path in candidates if os.path.isfile(path)), None)
        if not icon_path:
            owner._bounded_cache_put(cache, signature, None, max_items=64)
            return None
        try:
            image_module = importlib.import_module("PIL.Image")
            with image_module.open(icon_path) as icon_file:
                icon = icon_file.convert("RGBA")
            alpha = icon.split()[-1]
            alpha_min, alpha_max = alpha.getextrema()
            mask = alpha
            if alpha_min == 255 and alpha_max == 255:
                # Some downloaded marks ship on white backgrounds; derive a mask from luminance.
                gray = icon.convert("L")
                mask = gray.point(lambda p: max(0, min(255, (235 - p) * 4)))
            bounds = mask.getbbox()
            if bounds:
                icon = icon.crop(bounds)
                mask = mask.crop(bounds)
            tint_hex = str(tint).strip().lstrip("#")
            if len(tint_hex) != 6:
                tint_hex = "dff6ff"
            rgb = tuple(int(tint_hex[i:i + 2], 16) for i in (0, 2, 4))
            tinted = image_module.new("RGBA", icon.size, rgb + (0,))
            tinted.putalpha(mask)
            icon = tinted
            if max_size and (icon.width > max_size or icon.height > max_size):
                scale = min(max_size / float(icon.width), max_size / float(icon.height))
                new_size = (
                    max(1, int(round(icon.width * scale))),
                    max(1, int(round(icon.height * scale))),
                )
                icon = icon.resize(new_size, image_module.LANCZOS)
            if with_plate:
                draw_module = importlib.import_module("PIL.ImageDraw")
                plate_pad = 3
                plate_size = max(icon.width, icon.height) + (plate_pad * 2)
                plate = image_module.new("RGBA", (plate_size, plate_size), (0, 0, 0, 0))
                draw = draw_module.Draw(plate)
                draw.ellipse(
                    (0, 0, plate_size - 1, plate_size - 1),
                    fill=(70, 116, 146, 28),
                )
                draw.ellipse(
                    (1, 1, plate_size - 2, plate_size - 2),
                    fill=(18, 30, 42, 210),
                    outline=(76, 111, 136, 120),
                    width=1,
                )
                pos = ((plate_size - icon.width) // 2, (plate_size - icon.height) // 2)
                plate.alpha_composite(icon, pos)
                icon = plate
            photo = owner._pil_to_photo(icon)
            owner._bounded_cache_put(cache, signature, photo, max_items=64)
            return photo
        except (ImportError, OSError, ValueError, TypeError, AttributeError, tk.TclError, RuntimeError):
            owner._bounded_cache_put(cache, signature, None, max_items=64)
            return None


def _load_credit_discord_icon(owner: Any, max_size=16, tint="#dff6ff", with_plate=False):
        cache = getattr(owner, "_credit_discord_icon_cache", None)
        if cache is None:
            cache = {}
            owner._credit_discord_icon_cache = cache
        signature = (int(max_size), str(tint), bool(with_plate))
        cached = cache.get(signature)
        if cached is not None:
            return cached
        base_dir = owner._resource_base_dir()
        candidates = [
            os.path.join(base_dir, "assets", "buttons", "discord_clyde_icon.png"),
            os.path.join(base_dir, "assets", "buttons", "discord_mark_symbol.png"),
        ]
        icon_path = next((path for path in candidates if os.path.isfile(path)), None)
        if not icon_path:
            owner._bounded_cache_put(cache, signature, None, max_items=64)
            return None
        try:
            image_module = importlib.import_module("PIL.Image")
            with image_module.open(icon_path) as icon_file:
                icon = icon_file.convert("RGBA")
            alpha = icon.split()[-1]
            alpha_min, alpha_max = alpha.getextrema()
            mask = alpha
            if alpha_min == 255 and alpha_max == 255:
                gray = icon.convert("L")
                mask = gray.point(lambda p: max(0, min(255, (235 - p) * 4)))
            bounds = mask.getbbox()
            if bounds:
                icon = icon.crop(bounds)
                mask = mask.crop(bounds)
            tint_hex = str(tint).strip().lstrip("#")
            if len(tint_hex) != 6:
                tint_hex = "dff6ff"
            rgb = tuple(int(tint_hex[i:i + 2], 16) for i in (0, 2, 4))
            tinted = image_module.new("RGBA", icon.size, rgb + (0,))
            tinted.putalpha(mask)
            icon = tinted
            if max_size and (icon.width > max_size or icon.height > max_size):
                scale = min(max_size / float(icon.width), max_size / float(icon.height))
                new_size = (
                    max(1, int(round(icon.width * scale))),
                    max(1, int(round(icon.height * scale))),
                )
                icon = icon.resize(new_size, image_module.LANCZOS)
            if with_plate:
                draw_module = importlib.import_module("PIL.ImageDraw")
                plate_pad = 3
                plate_size = max(icon.width, icon.height) + (plate_pad * 2)
                plate = image_module.new("RGBA", (plate_size, plate_size), (0, 0, 0, 0))
                draw = draw_module.Draw(plate)
                draw.ellipse(
                    (0, 0, plate_size - 1, plate_size - 1),
                    fill=(70, 116, 146, 28),
                )
                draw.ellipse(
                    (1, 1, plate_size - 2, plate_size - 2),
                    fill=(18, 30, 42, 210),
                    outline=(76, 111, 136, 120),
                    width=1,
                )
                pos = ((plate_size - icon.width) // 2, (plate_size - icon.height) // 2)
                plate.alpha_composite(icon, pos)
                icon = plate
            photo = owner._pil_to_photo(icon)
            owner._bounded_cache_put(cache, signature, photo, max_items=64)
            return photo
        except (ImportError, OSError, ValueError, TypeError, AttributeError, tk.TclError, RuntimeError):
            owner._bounded_cache_put(cache, signature, None, max_items=64)
            return None


def _render_credit_badges(owner: Any):
        parent = owner._credit_badge_host
        if parent is None:
            return

        github_specs = [
            ("SIINDBAD", "https://github.com/Siindbad"),
            ("KAMUE", "https://github.com/Kamue-cmd"),
        ]
        variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
        palette = owner._footer_badge_palette(variant)
        spec = owner._footer_visual_spec()
        sources = owner._load_credit_badge_sources()
        owner._credit_badge_images = []
        chip_bg = palette["bg"]
        chip_border = palette["border"]
        text_fg = palette["fg"]
        icon_tint = "#d8e8f2"
        icon_with_plate = False
        icon_size = int(spec["chip_icon_size"])
        render_signature = (
            tuple(github_specs),
            variant,
            owner._footer_style_variant(),
            chip_bg,
            chip_border,
            text_fg,
            icon_tint,
            bool(icon_with_plate),
            int(icon_size),
            tuple(spec["chip_font"]),
        )
        if (
            render_signature == getattr(owner, "_credit_badge_render_signature", None)
            and parent.winfo_children()
        ):
            return
        for child in parent.winfo_children():
            child.destroy()

        github_icon_photo = owner._load_credit_github_icon(
            max_size=icon_size,
            tint=icon_tint,
            with_plate=icon_with_plate,
        )
        if github_icon_photo is not None:
            owner._credit_badge_images.append(github_icon_photo)
        name_font = spec["chip_font"]

        for idx, (name, url) in enumerate(github_specs):
            source = sources[idx] if idx < len(sources) else None
            pad_left = 0 if idx == 0 else int(spec["chip_gap"])
            open_cb = lambda _event, link=url: owner._open_external_link(link)

            chip = tk.Frame(
                parent,
                bg=chip_bg,
                bd=0,
                highlightthickness=1,
                highlightbackground=chip_border,
                highlightcolor=chip_border,
            )
            chip.pack(side="left", padx=(pad_left, 0))
            if github_icon_photo is not None:
                icon_label = tk.Label(
                    chip,
                    image=github_icon_photo,
                    bg=chip_bg,
                    bd=0,
                    highlightthickness=0,
                )
                icon_label.pack(side="left", padx=(spec["chip_icon_left_pad"], spec["chip_icon_gap"]), pady=0)
            elif source is not None:
                icon_width = max(1, int(round(source.width * 0.30)))
                icon = source.crop((0, 0, icon_width, source.height))
                icon = owner._resize_pil_image_to_height(icon, int(spec["chip_icon_size"]))
                icon_photo = owner._pil_to_photo(icon)
                if icon_photo is not None:
                    owner._credit_badge_images.append(icon_photo)
                    icon_label = tk.Label(
                        chip,
                        image=icon_photo,
                        bg=chip_bg,
                        bd=0,
                        highlightthickness=0,
                    )
                    icon_label.pack(side="left", padx=(spec["chip_icon_left_pad"], spec["chip_icon_gap"]), pady=0)
            text_label = tk.Label(
                chip,
                text=name,
                bg=chip_bg,
                fg=text_fg,
                font=name_font,
                bd=0,
                highlightthickness=0,
                padx=0,
                pady=spec["chip_text_pady"],
            )
            text_label.pack(side="left", padx=(0, spec["chip_text_right_pad"]), pady=0)
            owner._bind_click_recursive(chip, open_cb)
        owner._credit_badge_render_signature = render_signature


def _render_credit_discord_badges(owner: Any):
        parent = owner._credit_discord_badge_host
        if parent is None:
            return
        discord_specs = [
            ("SIN.NETWORK", "https://discord.gg/kpFXrtyr2Z"),
            ("G-DEVS", "https://discord.gg/U7pZFXXtcn"),
        ]
        variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
        palette = owner._footer_badge_palette(variant)
        spec = owner._footer_visual_spec()
        theme = getattr(owner, "_theme", {})
        owner._credit_discord_badge_images = []
        chip_bg = palette["bg"]
        chip_border = palette["border"]
        text_fg = palette["fg"]
        label_bg = theme.get("credit_bg", "#0b1118")
        label_fg = theme.get("credit_label_fg", "#b5cade")
        icon_tint = "#d8e8f2"
        icon_with_plate = False
        icon_size = int(spec["chip_icon_size"])
        render_signature = (
            tuple(discord_specs),
            variant,
            owner._footer_style_variant(),
            chip_bg,
            chip_border,
            text_fg,
            label_bg,
            label_fg,
            icon_tint,
            bool(icon_with_plate),
            int(icon_size),
            tuple(spec["chip_font"]),
        )
        if (
            render_signature == getattr(owner, "_credit_discord_badge_render_signature", None)
            and parent.winfo_children()
        ):
            return
        for child in parent.winfo_children():
            child.destroy()
        discord_icon_photo = owner._load_credit_discord_icon(
            max_size=icon_size,
            tint=icon_tint,
            with_plate=icon_with_plate,
        )
        if discord_icon_photo is not None:
            owner._credit_discord_badge_images.append(discord_icon_photo)
        name_font = spec["chip_font"]
        discord_label = tk.Label(
            parent,
            text="DISCORD :",
            bg=label_bg,
            fg=label_fg,
            font=spec["label_font"],
            bd=0,
            highlightthickness=0,
            padx=0,
            pady=spec["chip_text_pady"],
        )
        discord_label.pack(side="left", padx=(0, spec["label_gap"]))

        for idx, (name, url) in enumerate(discord_specs):
            pad_left = 0 if idx == 0 else int(spec["chip_gap"])
            chip = tk.Frame(
                parent,
                bg=chip_bg,
                bd=0,
                highlightthickness=1,
                highlightbackground=chip_border,
                highlightcolor=chip_border,
            )
            chip.pack(side="left", padx=(pad_left, 0))
            if discord_icon_photo is not None:
                icon_label = tk.Label(
                    chip,
                    image=discord_icon_photo,
                    bg=chip_bg,
                    bd=0,
                    highlightthickness=0,
                )
                icon_label.pack(side="left", padx=(spec["chip_icon_left_pad"], spec["chip_icon_gap"]), pady=0)
            text_label = tk.Label(
                chip,
                text=name,
                bg=chip_bg,
                fg=text_fg,
                font=name_font,
                bd=0,
                highlightthickness=0,
                padx=0,
                pady=spec["chip_text_pady"],
            )
            text_label.pack(side="left", padx=(0, spec["chip_text_right_pad"]), pady=0)
            if url:
                owner._bind_click_recursive(chip, lambda _event, link=url: owner._open_external_link(link))
        owner._credit_discord_badge_render_signature = render_signature
