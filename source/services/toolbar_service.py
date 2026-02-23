from tkinter import ttk
import tkinter as tk
import hashlib
import time
import sys
import os
import importlib
from typing import Any
from core.exceptions import EXPECTED_ERRORS

def resolve_siindbad_effective_style(
    style_focus: Any,
    show_toolbar_variant_controls: Any,
    app_theme_variant: Any,
    style_map: Any,
) -> Any:
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


def siindbad_toolbar_button_symbol(style: Any, key: Any) -> Any:
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


def siindbad_toolbar_label_text(style: Any, key: Any, text: Any) -> Any:
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


def siindbad_toolbar_button_width(style: Any, key: Any, text: Any) -> Any:
    use_style = str(style or "").upper()
    match use_style:
        case "A":
            widths = {
                "open": 92,
                "apply": 96,
                "export": 126,
                "find": 92,
                "update": 84,
                "readme": 84,
            }
        case "B":
            widths = {
                "open": 10,
                "apply": 12,
                "export": 14,
                "find": 11,
                "update": 9,
                "readme": 9,
            }
        case _:
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


def _build_toolbar_structure(owner: Any, top, inter_button_pad):
        style = owner._siindbad_effective_style()
        is_variant_b = style == "B"
        find_host_pad = (2, 0) if is_variant_b else (4, 2)
        find_btn_pad = (2, 0) if is_variant_b else (4, 0)
        font_host_pad = (2, 0)

        right_actions = ttk.Frame(top)
        right_actions.pack(side="right")

        open_btn = owner._make_toolbar_button(top, "Open", owner.open_file, image_key="open")
        owner._pack_toolbar_control(open_btn, side="left")
        owner._toolbar_buttons["open"] = open_btn

        apply_btn = owner._make_toolbar_button(top, "Apply Edit", owner.apply_edit, image_key="apply")
        owner._pack_toolbar_control(apply_btn, side="left", padx=(inter_button_pad, 0))
        owner._toolbar_buttons["apply"] = apply_btn

        export_btn = owner._make_toolbar_button(top, "Export .hhsav", owner.export_hhsave, image_key="export")
        owner._pack_toolbar_control(export_btn, side="left", padx=(inter_button_pad, 0))
        owner._toolbar_buttons["export"] = export_btn

        theme = getattr(owner, "_theme", {})
        find_fill = tk.Frame(
            top,
            bg=theme.get("bg", "#0f131a"),
            bd=0,
            highlightthickness=0,
        )
        find_fill.pack(side="left", padx=find_host_pad)
        owner._find_host_default_padx = find_host_pad
        find_fill.configure(height=33 if is_variant_b else 34)
        find_fill.pack_propagate(False)
        owner._find_entry_host = find_fill
        find_bg = theme.get("panel", "#161b24")
        find_fg = theme.get("fg", "#e6e6e6")
        find_select_bg = theme.get("select_bg", "#2f3a4d")
        find_select_fg = theme.get("select_fg", "#ffffff")
        find_border = theme.get("find_border", "#ffffff")
        owner.find_entry = tk.Entry(
            find_fill,
            width=20,
            font=(owner._preferred_mono_family(), 10),
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=find_border,
            highlightcolor=find_border,
            bg=find_bg,
            fg=find_fg,
            insertbackground=find_fg,
            selectbackground=find_select_bg,
            selectforeground=find_select_fg,
        )
        owner.find_entry.pack(fill="none", expand=False, padx=0, pady=(5, 3), ipady=1)
        owner.find_entry.bind("<Return>", owner.find_next)

        find_btn = owner._make_toolbar_button(right_actions, "Find Next", owner.find_next, image_key="find")
        owner._pack_toolbar_control(find_btn, side="left", padx=find_btn_pad)
        owner._find_button_default_padx = find_btn_pad
        owner._toolbar_buttons["find"] = find_btn

        font_frame = ttk.Frame(right_actions)
        font_frame.pack(side="left", padx=font_host_pad)
        owner._font_control_host = font_frame
        owner._render_font_control()

        update_btn = owner._make_toolbar_button(
            right_actions, "Update", owner.check_for_updates_manual, image_key="update"
        )
        owner._pack_toolbar_control(update_btn, side="left", padx=(inter_button_pad, 0))
        owner._toolbar_buttons["update"] = update_btn

        readme_btn = owner._make_toolbar_button(right_actions, "ReadMe", owner.show_readme, image_key="readme")
        owner._pack_toolbar_control(readme_btn, side="left", padx=(inter_button_pad, 0))
        owner._toolbar_buttons["readme"] = readme_btn


def _draw_siindbad_toolbar_icon(owner: Any, key, fg_hex, accent_hex, style, accent2_hex=None):
        image_module = importlib.import_module("PIL.Image")
        draw_module = importlib.import_module("PIL.ImageDraw")
        icon = image_module.new("RGBA", (16, 16), (0, 0, 0, 0))
        draw = draw_module.Draw(icon)
        fg = owner._hex_to_rgb_tuple(fg_hex) + (255,)
        accent = owner._hex_to_rgb_tuple(accent_hex) + (130,)
        accent2 = owner._hex_to_rgb_tuple(accent2_hex or accent_hex) + (220,)
        y_shift = 1 if style == "A" else 0

        def shift_line(points):
            return (points[0], points[1] + y_shift, points[2], points[3] + y_shift)

        def shift_box(box):
            return (box[0], box[1] + y_shift, box[2], box[3] + y_shift)

        def shift_poly(points):
            return [(x, y + y_shift) for x, y in points]

        if style == "B":
            # Bracket frame corners (R5 concept style).
            frame = accent2
            draw.line((1, 1, 5, 1), fill=frame, width=1)
            draw.line((1, 1, 1, 5), fill=frame, width=1)
            draw.line((11, 1, 15, 1), fill=frame, width=1)
            draw.line((15, 1, 15, 5), fill=frame, width=1)
            draw.line((1, 11, 1, 15), fill=frame, width=1)
            draw.line((1, 15, 5, 15), fill=frame, width=1)
            draw.line((15, 11, 15, 15), fill=frame, width=1)
            draw.line((11, 15, 15, 15), fill=frame, width=1)

        def glow_line(points, width=1):
            draw.line(points, fill=accent, width=max(1, width + 2))
            draw.line(points, fill=fg, width=width)

        def glow_rect(box, width=1):
            draw.rectangle(box, outline=accent, width=max(1, width + 1))
            draw.rectangle(box, outline=fg, width=width)

        def glow_ellipse(box, width=1):
            draw.ellipse(box, outline=accent, width=max(1, width + 1))
            draw.ellipse(box, outline=fg, width=width)

        if style == "B" and key == "open":
            glow_line((3, 6, 6, 6), width=1)
            glow_line((6, 6, 7, 5), width=1)
            glow_line((7, 5, 11, 5), width=1)
            glow_rect((3, 7, 12, 12), width=1)
            return icon
        if style == "B" and key == "apply":
            glow_line((3, 9, 6, 12), width=2)
            glow_line((6, 12, 12, 5), width=2)
            return icon
        if style == "B" and key == "export":
            glow_rect((3, 10, 13, 12), width=1)
            glow_line((8, 4, 8, 9), width=2)
            draw.polygon([(5, 8), (8, 12), (11, 8)], fill=fg)
            return icon
        if style == "B" and key == "find":
            glow_ellipse((2, 2, 10, 10), width=2)
            glow_line((9, 9, 13, 13), width=2)
            return icon
        if style == "B" and key == "update":
            draw.arc((2, 2, 13, 13), start=35, end=340, fill=accent, width=3)
            draw.arc((2, 2, 13, 13), start=35, end=340, fill=fg, width=2)
            draw.polygon([(11, 2), (14, 3), (12, 5)], fill=fg)
            return icon
        if style == "B" and key == "readme":
            glow_rect((3, 3, 12, 12), width=1)
            glow_line((7, 3, 7, 12), width=1)
            return icon
        if key == "open":
            # Folder icon: tab + body.
            glow_line(shift_line((2, 5, 5, 5)), width=1)
            glow_line(shift_line((5, 5, 6, 4)), width=1)
            glow_line(shift_line((6, 4, 9, 4)), width=1)
            glow_line(shift_line((2, 6, 12, 6)), width=1)
            glow_rect(shift_box((2, 6, 13, 12)), width=1)
            return icon
        if key == "apply":
            # Check icon.
            glow_line(shift_line((3, 8, 7, 12)), width=2)
            glow_line(shift_line((7, 12, 13, 4)), width=2)
            return icon
        if key == "export":
            # Download/export: tray + arrow.
            glow_rect(shift_box((3, 10, 13, 13)), width=1)
            glow_line(shift_line((8, 2, 8, 9)), width=2)
            draw.polygon(shift_poly([(5, 8), (8, 12), (11, 8)]), fill=accent)
            draw.polygon(shift_poly([(6, 8), (8, 11), (10, 8)]), fill=fg)
            return icon
        if key == "find":
            glow_ellipse(shift_box((2, 2, 10, 10)), width=2)
            glow_line(shift_line((9, 9, 13, 13)), width=2)
            return icon
        if key == "update":
            draw.arc(shift_box((2, 2, 13, 13)), start=30, end=325, fill=accent, width=3)
            draw.arc(shift_box((2, 2, 13, 13)), start=30, end=325, fill=fg, width=2)
            draw.polygon(shift_poly([(11, 2), (14, 3), (12, 5)]), fill=fg)
            return icon
        if key == "readme":
            # Book icon.
            glow_rect(shift_box((2, 3, 13, 12)), width=1)
            glow_line(shift_line((7, 3, 7, 12)), width=1)
            glow_line(shift_line((3, 5, 6, 5)), width=1)
            glow_line(shift_line((8, 5, 12, 5)), width=1)
            return icon

        return icon


def _siindbad_b_sprite_bundle(owner: Any, key, width, height, render_mode="full"):
        sprite_dir = owner._siindbad_b_sprite_dir()
        manifest = owner._siindbad_b_sprite_manifest()
        if not os.path.isdir(sprite_dir):
            return None
        render_mode = owner._siindbad_b_render_mode(render_mode)
        buttons_meta = manifest.get("buttons", {}) if isinstance(manifest, dict) else {}
        meta = buttons_meta.get(str(key), {}) if isinstance(buttons_meta, dict) else {}

        base_name = str(meta.get("base", f"{key}_base.png"))
        base_path = os.path.join(sprite_dir, base_name)
        if not os.path.isfile(base_path):
            return None

        image_module = importlib.import_module("PIL.Image")
        image_chops_module = importlib.import_module("PIL.ImageChops")
        image_stat_module = importlib.import_module("PIL.ImageStat")
        image_tk_module = importlib.import_module("PIL.ImageTk")

        try:
            base_image = image_module.open(base_path).convert("RGBA")
        except EXPECTED_ERRORS:
            return None
        if str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper() == "KAMUE":
            try:
                base_image = owner._shade_toolbar_button_for_theme(base_image)
                base_image = owner._harmonize_kamue_b_outer_frame(base_image)
            except EXPECTED_ERRORS:
                pass
        if base_image.width != width or base_image.height != height:
            try:
                base_image = base_image.resize((width, height), image_module.LANCZOS)
            except EXPECTED_ERRORS:
                return None

        hover_files = meta.get("hover_frames", [])
        if not hover_files:
            prefix = f"{key}_hover_"
            try:
                hover_files = sorted(
                    name for name in os.listdir(sprite_dir) if name.startswith(prefix) and name.endswith(".png")
                )
            except EXPECTED_ERRORS:
                hover_files = []

        hover_images = []
        for hover_name in hover_files:
            hover_path = os.path.join(sprite_dir, str(hover_name))
            if not os.path.isfile(hover_path):
                continue
            try:
                hover_image = image_module.open(hover_path).convert("RGBA")
                if str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper() == "KAMUE":
                    try:
                        hover_image = owner._shade_toolbar_button_for_theme(hover_image)
                        hover_image = owner._harmonize_kamue_b_outer_frame(hover_image)
                    except EXPECTED_ERRORS:
                        pass
                if hover_image.width != width or hover_image.height != height:
                    hover_image = hover_image.resize((width, height), image_module.LANCZOS)
                hover_images.append(hover_image)
            except EXPECTED_ERRORS:
                continue
        if not hover_images:
            hover_images = [base_image.copy()]
        else:
            # Slightly soften hover frames so mouseover highlight is less aggressive.
            hover_mix = float(meta.get("hover_mix", manifest.get("hover_mix", 0.84)) or 0.84)
            hover_mix = max(0.60, min(0.98, hover_mix))
            softened = []
            for hover_img in hover_images:
                try:
                    softened.append(image_module.blend(base_image, hover_img, hover_mix))
                except EXPECTED_ERRORS:
                    softened.append(hover_img)
            hover_images = softened

        interval = int(meta.get("frame_interval_ms", manifest.get("frame_interval_ms", 40)) or 40)
        # Preview R5 sweep is a single ~2.2s pass. Capture exports may contain extra
        # partial loops; trim to one clean pass for stable replay in Tk.
        cycle_ms = int(meta.get("scan_cycle_ms", manifest.get("scan_cycle_ms", 2200)) or 2200)
        # Match preferred slower feel while keeping room for smoother frame cadence.
        cycle_ms = int(round(float(cycle_ms) * 1.75))
        cycle_ms = max(1200, min(4000, cycle_ms))
        if hover_images and interval > 0:
            expected_frames = max(20, int(round(float(cycle_ms) / float(interval))))
            if len(hover_images) > expected_frames + 1:
                if render_mode == "fast":
                    hover_images = hover_images[:int(expected_frames)]
                else:
                    # Choose a contiguous cycle window with the smoothest wrap seam.
                    # This avoids visible "reset jumps" when the animation loops.
                    def _seam_cost(img_a, img_b):
                        try:
                            a = img_a.convert("L").resize((40, 12), image_module.BILINEAR)
                            b = img_b.convert("L").resize((40, 12), image_module.BILINEAR)
                            diff = image_chops_module.difference(a, b)
                            stat = image_stat_module.Stat(diff)
                            return float(stat.sum[0])
                        except EXPECTED_ERRORS:
                            return 0.0

                    n = len(hover_images)
                    m = int(expected_frames)
                    best_start = 0
                    best_score = None
                    max_start = max(0, n - m)
                    for start in range(max_start + 1):
                        first = hover_images[start]
                        last = hover_images[start + m - 1]
                        score = _seam_cost(first, last)
                        if best_score is None or score < best_score:
                            best_score = score
                            best_start = start
                    hover_images = hover_images[best_start: best_start + m]

        # Add one in-between blend frame between each captured frame.
        # This preserves visual style from R5 sprites while reducing stepped motion in Tk.
        if render_mode != "fast" and len(hover_images) > 1:
            smoothed = []
            total = len(hover_images)
            for idx, frame in enumerate(hover_images):
                smoothed.append(frame)
                nxt = hover_images[(idx + 1) % total]
                try:
                    smoothed.append(image_module.blend(frame, nxt, 0.5))
                except EXPECTED_ERRORS:
                    pass
            if smoothed:
                hover_images = smoothed

        # Keep a bounded frame budget for Tk runtime to avoid hitching on full-image swaps.
        max_runtime_frames = int(meta.get("runtime_max_frames", manifest.get("runtime_max_frames", 120)) or 120)
        if render_mode == "fast":
            max_runtime_frames = min(max_runtime_frames, 36)
        max_runtime_frames = max(24, min(120, max_runtime_frames))
        if len(hover_images) > max_runtime_frames:
            reduced = []
            step = float(len(hover_images)) / float(max_runtime_frames)
            pos = 0.0
            for _ in range(max_runtime_frames):
                reduced.append(hover_images[int(pos) % len(hover_images)])
                pos += step
            hover_images = reduced

        if hover_images and interval > 0:
            interval = int(round(float(cycle_ms) / float(max(1, len(hover_images)))))
        interval = max(20, min(100, interval))
        hover_frames = [image_tk_module.PhotoImage(img) for img in hover_images]
        return {
            "base": image_tk_module.PhotoImage(base_image),
            "hover_frames": hover_frames,
            "frame_interval_ms": interval,
        }


def _siindbad_b_render_button_bundle(owner: Any, key, text, width, height, palette, render_mode=None):
        cache = getattr(owner, "_siindbad_b_button_image_cache", None)
        if cache is None:
            cache = {}
            owner._siindbad_b_button_image_cache = cache
        render_mode = owner._siindbad_b_render_mode(render_mode)
        signature = (
            str(key),
            str(text),
            int(width),
            int(height),
            str(render_mode),
            palette.get("button_bg"),
            palette.get("button_fg"),
            palette.get("button_active"),
            palette.get("border"),
            palette.get("border_active"),
            palette.get("inner_border"),
        )
        cached = cache.get(signature)
        if cached:
            return cached

        try:
            image_module = importlib.import_module("PIL.Image")
            draw_module = importlib.import_module("PIL.ImageDraw")
            font_module = importlib.import_module("PIL.ImageFont")
            image_tk_module = importlib.import_module("PIL.ImageTk")
        except EXPECTED_ERRORS:
            # Keep startup functional when Pillow is unavailable (dev env or minimal runtime).
            return None

        sprite_bundle = owner._siindbad_b_sprite_bundle(
            key=key,
            width=width,
            height=height,
            render_mode=render_mode,
        )
        if sprite_bundle:
            owner._bounded_cache_put(cache, signature, sprite_bundle, max_items=64)
            return sprite_bundle

        def _rgb(hex_color, fallback):
            return owner._hex_to_rgb_tuple(hex_color, default_rgb=fallback)

        def _rgba(rgb, alpha=255):
            return (rgb[0], rgb[1], rgb[2], alpha)

        # Primary R5 path: use the exact Variant-B source art footprint and animate hover scan over it.
        asset_path = owner._siindbad_b_asset_button_path(key)
        if asset_path:
            try:
                source = image_module.open(asset_path).convert("RGBA")
                if source.width != width or source.height != height:
                    source = source.resize((width, height), image_module.LANCZOS)

                border_active_rgb = owner._hex_to_rgb_tuple(
                    palette.get("border_active", "#95eaff"),
                    default_rgb=(149, 234, 255),
                )
                hover_base = source.copy()
                hover_tint = image_module.new("RGBA", (width, height), _rgba(border_active_rgb, 16))
                hover_base = image_module.alpha_composite(hover_base, hover_tint)

                hover_frames = []
                scan_step = 8 if render_mode == "fast" else 4
                for pos in range(-34, width + 34, scan_step):
                    frame = hover_base.copy()
                    frame_draw = draw_module.Draw(frame)
                    for idx in range(24):
                        alpha = int(max(0, 94 - abs(12 - idx) * 7))
                        x = pos + idx
                        if 0 <= x < width:
                            frame_draw.line((x, 1, x, height - 2), fill=_rgba(border_active_rgb, alpha), width=1)
                    core_x = pos + 12
                    if 0 <= core_x < width:
                        frame_draw.line((core_x, 1, core_x, height - 2), fill=_rgba((225, 252, 255), 170), width=1)
                    hover_frames.append(image_tk_module.PhotoImage(frame))

                if render_mode == "fast" and len(hover_frames) > 24:
                    hover_frames = hover_frames[:24]
                bundle = {
                    "base": image_tk_module.PhotoImage(source),
                    "hover_frames": hover_frames,
                    "frame_interval_ms": 40,
                }
                owner._bounded_cache_put(cache, signature, bundle, max_items=64)
                return bundle
            except EXPECTED_ERRORS:
                pass

        def _mix(rgb_a, rgb_b, amount):
            amount = max(0.0, min(1.0, float(amount)))
            return (
                int(rgb_a[0] * (1.0 - amount) + rgb_b[0] * amount),
                int(rgb_a[1] * (1.0 - amount) + rgb_b[1] * amount),
                int(rgb_a[2] * (1.0 - amount) + rgb_b[2] * amount),
            )

        bg_rgb = _rgb(palette.get("button_bg", "#10253b"), (16, 37, 59))
        fg_rgb = _rgb(palette.get("button_fg", "#dff5ff"), (223, 245, 255))
        border_rgb = _rgb(palette.get("border", "#3f82a9"), (63, 130, 169))
        border_active_rgb = _rgb(palette.get("border_active", "#95eaff"), (149, 234, 255))
        icon_frame_rgb = _rgb(palette.get("inner_border", "#73d7fb"), (115, 215, 251))
        inner_border_rgb = _mix(border_rgb, bg_rgb, 0.55)
        slot_rgb = _mix(bg_rgb, (0, 0, 0), 0.22)
        top_gloss_rgb = _mix(border_active_rgb, fg_rgb, 0.35)
        corner_bar_rgb = _mix(border_active_rgb, border_rgb, 0.5)

        base = image_module.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = draw_module.Draw(base)

        # Outer/inner frame to match R5 bracket-frame concept.
        draw.rectangle((0, 0, width - 1, height - 1), fill=_rgba(bg_rgb), outline=_rgba(border_rgb))
        draw.rectangle((1, 1, width - 2, height - 2), outline=_rgba(inner_border_rgb))
        draw.line((2, 2, width - 3, 2), fill=_rgba(top_gloss_rgb, 120), width=1)
        draw.line((2, height - 3, width - 3, height - 3), fill=_rgba(slot_rgb, 190), width=1)

        # Stream-tag right corner accents used in the preview.
        draw.line((width - 11, 4, width - 4, 4), fill=_rgba(border_active_rgb), width=1)
        draw.line((width - 4, 4, width - 4, 9), fill=_rgba(border_active_rgb), width=1)
        draw.line((width - 16, height - 4, width - 4, height - 4), fill=_rgba(corner_bar_rgb), width=1)

        # Bracket icon shell from R5.
        ix = 7
        iy = max(2, (height - 18) // 2)
        iw = 18
        ih = 18
        bracket_len = 5
        draw.line((ix, iy, ix + bracket_len, iy), fill=_rgba(icon_frame_rgb), width=1)
        draw.line((ix, iy, ix, iy + bracket_len), fill=_rgba(icon_frame_rgb), width=1)
        draw.line((ix + iw - bracket_len - 1, iy, ix + iw - 1, iy), fill=_rgba(icon_frame_rgb), width=1)
        draw.line((ix + iw - 1, iy, ix + iw - 1, iy + bracket_len), fill=_rgba(icon_frame_rgb), width=1)
        draw.line((ix, iy + ih - bracket_len - 1, ix, iy + ih - 1), fill=_rgba(icon_frame_rgb), width=1)
        draw.line((ix, iy + ih - 1, ix + bracket_len, iy + ih - 1), fill=_rgba(icon_frame_rgb), width=1)
        draw.line(
            (ix + iw - 1, iy + ih - bracket_len - 1, ix + iw - 1, iy + ih - 1),
            fill=_rgba(icon_frame_rgb),
            width=1,
        )
        draw.line(
            (ix + iw - bracket_len - 1, iy + ih - 1, ix + iw - 1, iy + ih - 1),
            fill=_rgba(icon_frame_rgb),
            width=1,
        )

        gx = ix + 3
        gy = iy + 3

        def _stroke(points, width_px=2):
            draw.line(points, fill=_rgba(icon_frame_rgb, 155), width=max(1, width_px + 2), joint="curve")
            draw.line(points, fill=_rgba(fg_rgb), width=width_px, joint="curve")

        def _rect(box, width_px=1):
            draw.rectangle(box, outline=_rgba(icon_frame_rgb, 135), width=max(1, width_px + 1))
            draw.rectangle(box, outline=_rgba(fg_rgb), width=width_px)

        def _ellipse(box, width_px=1):
            draw.ellipse(box, outline=_rgba(icon_frame_rgb, 135), width=max(1, width_px + 1))
            draw.ellipse(box, outline=_rgba(fg_rgb), width=width_px)

        # Match SVG glyph language from R5 preview.
        if key == "open":
            _stroke((gx + 0, gy + 4, gx + 4, gy + 4, gx + 5, gy + 2, gx + 10, gy + 2, gx + 10, gy + 4), 1)
            _stroke((gx + 0, gy + 5, gx + 12, gy + 5), 1)
            draw.polygon(
                [(gx + 0, gy + 5), (gx + 12, gy + 5), (gx + 10, gy + 11), (gx + 1, gy + 11)],
                fill=None,
                outline=_rgba(fg_rgb),
            )
        elif key == "apply":
            _stroke((gx + 1, gy + 7, gx + 4, gy + 10, gx + 11, gy + 3), 2)
        elif key == "export":
            _stroke((gx + 6, gy + 1, gx + 6, gy + 8), 2)
            _stroke((gx + 3, gy + 6, gx + 6, gy + 9, gx + 9, gy + 6), 2)
            _rect((gx + 1, gy + 9, gx + 11, gy + 11), 1)
        elif key == "find":
            _ellipse((gx + 0, gy + 0, gx + 8, gy + 8), 2)
            _stroke((gx + 7, gy + 7, gx + 11, gy + 11), 2)
        elif key == "update":
            draw.arc((gx + 0, gy + 0, gx + 11, gy + 11), start=35, end=330, fill=_rgba(icon_frame_rgb, 180), width=3)
            draw.arc((gx + 0, gy + 0, gx + 11, gy + 11), start=35, end=330, fill=_rgba(fg_rgb), width=2)
            draw.polygon([(gx + 8, gy + 0), (gx + 11, gy + 1), (gx + 9, gy + 3)], fill=_rgba(fg_rgb))
        elif key == "readme":
            _rect((gx + 1, gy + 1, gx + 10, gy + 10), 1)
            _stroke((gx + 5, gy + 1, gx + 5, gy + 10), 1)

        # Prefer Tektur for R5 parity when present; fallback to existing bundled font.
        font_candidates = [
            os.path.join(owner._resource_base_dir(), "assets", "fonts", "Tektur-SemiBold.ttf"),
            os.path.join(owner._resource_base_dir(), "assets", "fonts", "Tektur-Regular.ttf"),
            os.path.join(owner._resource_base_dir(), "assets", "fonts", "Rajdhani-SemiBold.ttf"),
        ]
        text_font = None
        for font_path in font_candidates:
            try:
                if os.path.isfile(font_path):
                    text_font = font_module.truetype(font_path, 14)
                    break
            except EXPECTED_ERRORS:
                continue
        if text_font is None:
            try:
                text_font = font_module.load_default()
            except EXPECTED_ERRORS:
                text_font = None
        tx = ix + iw + 8
        bbox = draw.textbbox((0, 0), text, font=text_font)
        th = max(1, bbox[3] - bbox[1])
        ty = max(1, (height - th) // 2 - 1)
        draw.text((tx + 1, ty + 1), text, fill=_rgba((7, 20, 33), 210), font=text_font)
        draw.text((tx, ty), text, fill=_rgba(fg_rgb), font=text_font)

        hover_base = base.copy()
        hover_draw = draw_module.Draw(hover_base)
        hover_draw.rectangle((0, 0, width - 1, height - 1), outline=_rgba(border_active_rgb))
        hover_draw.rectangle((1, 1, width - 2, height - 2), outline=_rgba(_mix(border_active_rgb, border_rgb, 0.42)))
        hover_draw.text((tx + 1, ty), text, fill=_rgba(border_active_rgb, 92), font=text_font)

        hover_frames = []
        scan_step = 10 if render_mode == "fast" else 5
        for pos in range(-34, width + 34, scan_step):
            frame = hover_base.copy()
            frame_draw = draw_module.Draw(frame)
            # Wider scanning pass than single-line sweep.
            for idx in range(24):
                alpha = int(max(0, 86 - abs(12 - idx) * 7))
                x = pos + idx
                if 1 <= x <= width - 2:
                    frame_draw.line((x, 1, x, height - 2), fill=_rgba(border_active_rgb, alpha), width=1)
            core_x = pos + 12
            if 1 <= core_x <= width - 2:
                frame_draw.line((core_x, 2, core_x, height - 3), fill=_rgba((222, 252, 255), 160), width=1)
            hover_frames.append(image_tk_module.PhotoImage(frame))

        if render_mode == "fast" and len(hover_frames) > 24:
            hover_frames = hover_frames[:24]

        bundle = {
            "base": image_tk_module.PhotoImage(base),
            "hover_frames": hover_frames,
            "frame_interval_ms": 40,
        }
        owner._bounded_cache_put(cache, signature, bundle, max_items=64)
        return bundle


def _apply_siindbad_toolbar_button_style(owner: Any, button, key, text):
        palette = owner._siindbad_toolbar_style_palette()
        style = owner._siindbad_effective_style()
        frame_host = getattr(button, "_siindbad_frame_host", None)
        if frame_host is not None and frame_host.winfo_exists():
            try:
                frame_host.configure(
                    bg=palette["button_bg"],
                    highlightbackground=palette["border"],
                    highlightcolor=palette["border_active"],
                )
            except EXPECTED_ERRORS:
                pass

        display_text = owner._siindbad_toolbar_label_text(style, key, text)
        if style == "B":
            width = owner._siindbad_toolbar_frame_width(style, key, display_text)
            height = owner._siindbad_b_button_height(key, default_height=34)
            try:
                if frame_host is not None and frame_host.winfo_exists():
                    frame_host.configure(width=max(1, int(width)), height=height)
                    frame_host.pack_propagate(False)
            except EXPECTED_ERRORS:
                pass

            bundle = owner._siindbad_b_render_button_bundle(
                key=key,
                text=display_text,
                width=max(48, int(width)),
                height=max(24, height),
                palette=palette,
            )
            if not isinstance(bundle, dict):
                bundle = {}
            button._siindbad_base_image = bundle.get("base")
            button._siindbad_hover_frames = bundle.get("hover_frames", [])
            base_interval = int(bundle.get("frame_interval_ms", 40) or 40)
            button._siindbad_scan_interval_ms = max(20, min(100, base_interval))
            owner._stop_siindbad_b_button_scan(button)
            try:
                if isinstance(button, tk.Label):
                    if button._siindbad_base_image is None:
                        button.configure(
                            text=display_text,
                            image="",
                            compound="none",
                            font=owner._toolbar_button_font(),
                            relief="flat",
                            borderwidth=0,
                            highlightthickness=0,
                            padx=8,
                            pady=4,
                            bg=palette["button_bg"],
                            fg=palette["button_fg"],
                            cursor="hand2",
                            anchor="center",
                            justify="center",
                        )
                    else:
                        button.configure(
                            text="",
                            image=button._siindbad_base_image,
                            compound="none",
                            font=owner._toolbar_button_font(),
                            relief="flat",
                            borderwidth=0,
                            highlightthickness=0,
                            padx=0,
                            pady=0,
                            bg=palette["button_bg"],
                            fg=palette["button_fg"],
                            cursor="hand2",
                            anchor="center",
                            justify="center",
                        )
                else:
                    button.configure(
                        text="",
                        image=button._siindbad_base_image,
                        compound="none",
                        font=owner._toolbar_button_font(),
                        relief="flat",
                        borderwidth=0,
                        highlightthickness=0,
                        highlightbackground=palette["border"],
                        highlightcolor=palette["border_active"],
                        padx=0,
                        pady=0,
                        bg=palette["button_bg"],
                        fg=palette["button_fg"],
                        activebackground=palette["button_bg"],
                        activeforeground=palette["button_fg"],
                        disabledforeground="#57768c",
                        takefocus=0,
                        cursor="hand2",
                        width=0,
                        anchor="center",
                        justify="center",
                        overrelief="flat",
                        height=0,
                    )
            except EXPECTED_ERRORS:
                return
            return

        owner._ensure_siindbad_button_icons()
        icon = owner._siindbad_button_icons.get(key)
        symbol = owner._siindbad_toolbar_button_symbol(key)
        if icon is not None:
            label_text = display_text
            image_value = icon
            compound = "left"
            anchor = "w"
            pad_x = 7 if style == "A" else 7
        else:
            label_text = f"{symbol}  {display_text}" if symbol else display_text
            image_value = ""
            compound = "none"
            anchor = "center"
            pad_x = 10
        justify = "left"
        if style == "A" and key == "open":
            anchor = "center"
            justify = "center"
            pad_x = 5
        width = owner._siindbad_toolbar_button_width(style, key, display_text) if style == "A" else 0
        pad_y = 5 if style == "A" else (4 if style == "B" else 4)
        relief = "flat"
        border_width = 0
        highlight_thickness = 0 if style in ("A", "B") else 1
        try:
            button.configure(
                text=label_text,
                image=image_value,
                compound=compound,
                font=owner._toolbar_button_font(),
                relief=relief,
                borderwidth=border_width,
                highlightthickness=highlight_thickness,
                highlightbackground=palette["border"],
                highlightcolor=palette["border_active"],
                padx=pad_x,
                pady=pad_y,
                bg=palette["button_bg"],
                fg=palette["button_fg"],
                activebackground=palette["button_active"],
                activeforeground="#ffffff",
                disabledforeground="#7a93a8" if style != "B" else "#57768c",
                takefocus=0,
                cursor="hand2",
                width=width,
                anchor=anchor,
                justify=justify,
                overrelief="flat",
                height=0,
            )
        except EXPECTED_ERRORS:
            return


def _make_siindbad_stepper_button(owner: Any, parent, symbol, command):
        palette = owner._siindbad_toolbar_style_palette()
        style = owner._siindbad_effective_style()
        box_w = 28 if style == "A" else 22
        box_h = 22
        box = tk.Frame(
            parent,
            bg=palette["slot_bg"],
            bd=0,
            highlightthickness=1,
            highlightbackground=palette["border"],
            highlightcolor=palette["border_active"],
            width=box_w,
            height=box_h,
        )
        box.pack_propagate(False)
        symbol_canvas = tk.Canvas(
            box,
            bg=palette["slot_bg"],
            bd=0,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )
        symbol_canvas.pack(fill="both", expand=True, padx=1, pady=1)

        stroke = 2
        normal_bg = palette["slot_bg"]
        active_bg = palette["button_active"]
        fg = palette["button_fg"]

        def _draw_symbol(_event=None):
            symbol_canvas.delete("symbol")
            w = max(4, int(symbol_canvas.winfo_width()))
            h = max(4, int(symbol_canvas.winfo_height()))
            cx = w // 2
            cy = h // 2
            half = max(4, min(w, h) // 4)
            symbol_canvas.create_line(
                cx - half,
                cy,
                cx + half,
                cy,
                fill=fg,
                width=stroke,
                capstyle="round",
                tags="symbol",
            )
            if symbol == "+":
                v_half = max(3, half - 1)
                symbol_canvas.create_line(
                    cx,
                    cy - v_half,
                    cx,
                    cy + v_half,
                    fill=fg,
                    width=stroke,
                    capstyle="round",
                    tags="symbol",
                )

        def _on_press(_event):
            symbol_canvas.configure(bg=active_bg)

        def _on_release(_event):
            symbol_canvas.configure(bg=normal_bg)
            command()

        def _on_leave(_event):
            symbol_canvas.configure(bg=normal_bg)

        symbol_canvas.bind("<Configure>", _draw_symbol)
        symbol_canvas.bind("<ButtonPress-1>", _on_press)
        symbol_canvas.bind("<ButtonRelease-1>", _on_release)
        symbol_canvas.bind("<Leave>", _on_leave)
        _draw_symbol()
        return box


def _make_toolbar_button(owner: Any, parent, text, command, image_key=None):
        key = owner._normalize_button_token(image_key or text)
        owner._toolbar_button_text[key] = text
        variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
        style = owner._siindbad_effective_style()
        if variant == "SIINDBAD" or (variant == "KAMUE" and style == "B"):
            if style == "A":
                palette = owner._siindbad_toolbar_style_palette()
                frame = tk.Frame(
                    parent,
                    bg=palette["button_bg"],
                    bd=1,
                    relief="solid",
                    highlightthickness=1,
                    highlightbackground=palette["border"],
                    highlightcolor=palette["border_active"],
                )
                button = tk.Button(frame, command=command)
                button.pack(fill="both", expand=True)
                button._siindbad_frame_host = frame
            elif style == "B":
                palette = owner._siindbad_toolbar_style_palette()
                frame_width = owner._siindbad_toolbar_frame_width(style, key, text)
                frame_height = owner._siindbad_b_button_height(key, default_height=34)
                frame = tk.Frame(
                    parent,
                    bg=palette["button_bg"],
                    bd=0,
                    relief="flat",
                    highlightthickness=0,
                    highlightbackground=palette["button_bg"],
                    highlightcolor=palette["button_bg"],
                    width=max(1, int(frame_width)) if frame_width else 1,
                    height=max(1, int(frame_height)),
                )
                frame.pack_propagate(False)
                button = tk.Label(
                    frame,
                    text="",
                    bd=0,
                    relief="flat",
                    highlightthickness=0,
                    bg=palette["button_bg"],
                    cursor="hand2",
                )
                button.pack(fill="both", expand=True, padx=0, pady=0)
                button._siindbad_frame_host = frame
                button._siindbad_scan_running = False
                button._siindbad_scan_after_id = None
                button._siindbad_hover_leave_after_id = None
                button._siindbad_scan_start_ts = None
                button._siindbad_hover_require_reenter = False
                hover_targets = (frame, button)
                for target in hover_targets:
                    target.bind(
                        "<Enter>",
                        lambda _event, b=button: owner._siindbad_b_button_hover_enter(b),
                        add="+",
                    )
                    target.bind(
                        "<Leave>",
                        lambda _event, b=button: owner._siindbad_b_button_hover_leave(b),
                        add="+",
                    )
                for target in (frame, button):
                    target.bind(
                        "<Button-1>",
                        lambda _event, b=button, cmd=command: owner._invoke_siindbad_b_button(b, cmd),
                        add="+",
                    )
            else:
                button = tk.Button(parent, command=command)
            owner._apply_siindbad_toolbar_button_style(button, key=key, text=text)
            return button
        image = owner._toolbar_button_images.get(key)
        if image is not None:
            button = tk.Button(
                parent,
                image=image,
                command=command,
            )
            owner._apply_asset_toolbar_button_style(button)
            return button
        return ttk.Button(parent, text=text, command=command)
