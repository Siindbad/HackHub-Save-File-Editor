"""Toolbar/logo image and cache helper service."""

from typing import Any


def shade_toolbar_button_for_theme(
    owner: Any,
    image: Any,
    cache_key: Any = None,
    *,
    importlib_module: Any,
    expected_errors: Any,
) -> Any:
    """Apply theme-specific color treatment to toolbar button assets."""
    if str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper() != "KAMUE":
        return image
    if cache_key:
        cache = getattr(owner, "_toolbar_theme_shade_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            owner._toolbar_theme_shade_cache = cache
        key = (str(cache_key), int(getattr(image, "width", 0) or 0), int(getattr(image, "height", 0) or 0))
        cached = cache.get(key)
        if cached is not None:
            try:
                return cached.copy()
            except tuple(expected_errors):
                return cached
    try:
        image_module = importlib_module.import_module("PIL.Image")
        image_chops_module = importlib_module.import_module("PIL.ImageChops")
        image_enhance_module = importlib_module.import_module("PIL.ImageEnhance")

        base = image.convert("RGBA")
        r_chan, g_chan, b_chan, alpha_chan = base.split()

        # Build a mask biased toward blue-cyan pixels so we tint frames/background
        # harder than bright text/icons.
        blue_vs_red = image_chops_module.subtract(b_chan, r_chan).point(
            lambda p: min(255, int(p * 2.8))
        )
        blue_vs_green = image_chops_module.subtract(b_chan, g_chan).point(
            lambda p: min(255, int(p * 2.5))
        )
        tint_mask = image_chops_module.lighter(blue_vs_red, blue_vs_green)
        tint_mask = tint_mask.point(lambda p: min(255, int(p * 0.62)))

        purple_overlay = image_module.new("RGBA", base.size, (108, 56, 176, 0))
        purple_overlay.putalpha(tint_mask)
        tinted = image_module.alpha_composite(base, purple_overlay)

        # Darken primarily tinted regions instead of the whole button.
        dark_mask = tint_mask.point(lambda p: min(255, int(p * 0.38)))
        dark_overlay = image_module.new("RGBA", base.size, (16, 7, 30, 0))
        dark_overlay.putalpha(dark_mask)
        tinted = image_module.alpha_composite(tinted, dark_overlay)

        # Preserve white label readability (text/icons) after tinting.
        luma = base.convert("L")
        highlight_mask = luma.point(
            lambda p: 0 if p < 170 else (70 if p < 205 else 120)
        )
        highlight_overlay = image_module.new("RGBA", base.size, (244, 244, 255, 0))
        highlight_overlay.putalpha(highlight_mask)
        tinted = image_module.alpha_composite(tinted, highlight_overlay)

        # Final crispness pass.
        rgb = tinted.convert("RGB")
        rgb = image_enhance_module.Contrast(rgb).enhance(1.09)
        rgb = image_enhance_module.Sharpness(rgb).enhance(1.08)
        out = rgb.convert("RGBA")
        out.putalpha(alpha_chan)
        if cache_key:
            cache = getattr(owner, "_toolbar_theme_shade_cache", None)
            if not isinstance(cache, dict):
                cache = {}
                owner._toolbar_theme_shade_cache = cache
            key = (str(cache_key), int(out.width), int(out.height))
            owner._bounded_cache_put(cache, key, out.copy(), max_items=192)
        return out
    except (ImportError, OSError, ValueError, TypeError, AttributeError):
        return image


def harmonize_kamue_b_outer_frame(owner: Any, image: Any, *, importlib_module: Any) -> Any:
    """Force KAMUE Variant-B sprite outer frame to match FONT frame border color."""
    if str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper() != "KAMUE":
        return image
    try:
        draw_module = importlib_module.import_module("PIL.ImageDraw")
        theme = getattr(owner, "_theme", {})
        border_hex = theme.get("find_border", "#cfb5ee")
        border_rgb = owner._hex_to_rgb_tuple(border_hex, default_rgb=(207, 181, 238))
        out = image.copy().convert("RGBA")
        draw = draw_module.Draw(out)
        w, h = out.size
        if w >= 2 and h >= 2:
            draw.rectangle(
                (0, 0, w - 1, h - 1),
                outline=(border_rgb[0], border_rgb[1], border_rgb[2], 255),
                width=1,
            )
        return out
    except (ImportError, OSError, ValueError, TypeError, AttributeError):
        return image


def load_toolbar_button_image(
    owner: Any,
    path: Any,
    max_width: Any = 208,
    max_height: Any = 40,
    stretch_to_fit: Any = False,
    *,
    importlib_module: Any,
    tk_module: Any,
    expected_errors: Any,
) -> Any:
    cache = getattr(owner, "_toolbar_asset_image_cache", None)
    if cache is None:
        cache = {}
        owner._toolbar_asset_image_cache = cache
    theme_variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    signature = (
        str(path),
        int(max_width),
        int(max_height),
        bool(stretch_to_fit),
        theme_variant,
    )
    cached = cache.get(signature)
    if cached is not None:
        return cached

    try:
        image_module = importlib_module.import_module("PIL.Image")
        image_tk_module = importlib_module.import_module("PIL.ImageTk")
        image = image_module.open(path).convert("RGBA")
        image = owner._shade_toolbar_button_for_theme(image, cache_key=f"asset:{path}")
        if stretch_to_fit and max_width > 0 and max_height > 0:
            if image.width != max_width or image.height != max_height:
                image = image.resize((max_width, max_height), image_module.LANCZOS)
            photo = image_tk_module.PhotoImage(image)
            owner._bounded_cache_put(cache, signature, photo, max_items=192)
            return photo
        scale = min(max_width / image.width, max_height / image.height, 1.0)
        if scale < 1.0:
            new_size = (
                max(1, int(image.width * scale)),
                max(1, int(image.height * scale)),
            )
            image = image.resize(new_size, image_module.LANCZOS)
        photo = image_tk_module.PhotoImage(image)
        owner._bounded_cache_put(cache, signature, photo, max_items=192)
        return photo
    except (ImportError, OSError, ValueError, TypeError, AttributeError, tk_module.TclError, RuntimeError):
        pass

    try:
        image = tk_module.PhotoImage(file=path)
    except (tk_module.TclError, RuntimeError, OSError, ValueError):
        return None
    scale = 1
    if image.width() > max_width:
        scale = max(scale, (image.width() + max_width - 1) // max_width)
    if image.height() > max_height:
        scale = max(scale, (image.height() + max_height - 1) // max_height)
    if scale > 1:
        image = image.subsample(scale, scale)
    owner._bounded_cache_put(cache, signature, image, max_items=192)
    return image


def load_logo_image(
    owner: Any,
    path: Any,
    *,
    importlib_module: Any,
    os_module: Any,
    tk_module: Any,
    expected_errors: Any,
    theme_service: Any,
) -> Any:
    ext = os_module.path.splitext(path)[1].lower()
    cache = getattr(owner, "_logo_photo_cache", None)
    if cache is None:
        cache = {}
        owner._logo_photo_cache = cache
    try:
        image_module = importlib_module.import_module("PIL.Image")
        image_tk_module = importlib_module.import_module("PIL.ImageTk")
        is_banner_logo = owner._is_banner_logo_path(path)
        max_width = 700
        if is_banner_logo:
            # Keep logo frame aligned with top controls (which use 4px side padding).
            # Two highlight borders add ~4px to the frame width.
            try:
                owner.root.update_idletasks()
                available_width = int(owner.root.winfo_width())
            except tuple(expected_errors):
                available_width = 0
            if available_width > 120:
                side_padding = 4 * 2
                frame_border = 4
                max_width = max(700, available_width - side_padding - frame_border)
            else:
                max_width = 988
        signature = (os_module.path.abspath(path), int(max_width) if is_banner_logo else 0)
        cached = cache.get(signature)
        if cached is not None:
            return cached
        image = theme_service.get_cached_rgba_image(owner, path, image_module)
        if image is None:
            return None
        if image.width > max_width:
            scale = max_width / image.width
            new_size = (max_width, int(image.height * scale))
            image = image.resize(new_size, image_module.LANCZOS)
        photo = image_tk_module.PhotoImage(image)
        owner._bounded_cache_put(cache, signature, photo, max_items=48)
        return photo
    except tuple(expected_errors):
        pass

    try:
        signature = (os_module.path.abspath(path), 0)
        cached = cache.get(signature)
        if cached is not None:
            return cached
        if ext in (".png", ".gif", ".ppm", ".pgm"):
            photo = tk_module.PhotoImage(file=path)
            owner._bounded_cache_put(cache, signature, photo, max_items=48)
            return photo
    except tuple(expected_errors):
        return None
    return None
