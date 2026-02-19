from typing import Iterable, Optional


def _to_float(value, default=0.0) -> float:
    # Safe numeric coercion helper for mixed tk/system metric inputs.
    try:
        return float(value)
    except Exception:
        return float(default)


def _to_int(value, default=0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def clamp_display_scale(value, minimum: float = 0.8, maximum: float = 2.5) -> float:
    # Keep UI scale within supported runtime bounds.
    scale = _to_float(value, default=1.0)
    return max(float(minimum), min(float(maximum), scale))


def detect_display_scale_from_candidates(
    candidates: Optional[Iterable[float]],
    minimum: float = 0.8,
    maximum: float = 2.5,
) -> float:
    # Choose the largest valid display scale from detected monitor candidates.
    vals = []
    if candidates is not None:
        for item in candidates:
            val = _to_float(item, default=0.0)
            if val > 0.0:
                vals.append(val)
    if not vals:
        return 1.0
    return clamp_display_scale(max(vals), minimum=minimum, maximum=maximum)


def tk_scaling_from_display_scale(display_scale: float) -> float:
    scale = clamp_display_scale(display_scale)
    return (96.0 * scale) / 72.0


def compute_window_layout_for_screen(
    screen_width,
    screen_height,
    display_scale=1.0,
    base_width=1000,
    base_height=700,
):
    # Compute startup window size/min-size centered for the active monitor.
    screen_width = max(640, _to_int(round(_to_float(screen_width, 1280.0)), default=1280))
    screen_height = max(480, _to_int(round(_to_float(screen_height, 720.0)), default=720))
    display_scale = clamp_display_scale(display_scale)
    base_width = max(760, _to_int(round(_to_float(base_width, 1000.0)), default=1000))
    base_height = max(520, _to_int(round(_to_float(base_height, 700.0)), default=700))

    scale_boost = max(1.0, min(1.2, display_scale))
    desired_width = int(round(base_width * scale_boost))
    desired_height = int(round(base_height * scale_boost))

    max_width = max(640, int(round(screen_width * 0.94)))
    max_height = max(460, int(round(screen_height * 0.90)))
    width = max(560, min(desired_width, max_width))
    height = max(420, min(desired_height, max_height))

    min_scale_boost = max(1.0, min(1.15, display_scale))
    base_min_width = int(round(760 * min_scale_boost))
    base_min_height = int(round(520 * min_scale_boost))
    min_width = max(520, min(width, base_min_width, int(round(screen_width * 0.80))))
    min_height = max(360, min(height, base_min_height, int(round(screen_height * 0.78))))
    x = max(0, int(round((screen_width - width) / 2.0)))
    y = max(0, int(round((screen_height - height) / 2.0)))
    return {
        "width": int(width),
        "height": int(height),
        "x": int(x),
        "y": int(y),
        "min_width": int(min_width),
        "min_height": int(min_height),
    }


def auto_display_profile_for_screen(screen_width, screen_height, display_scale):
    # Apply low-scale boosts on high-resolution displays to preserve readability.
    width = max(640, _to_int(round(_to_float(screen_width, 1280.0)), default=1280))
    height = max(480, _to_int(round(_to_float(screen_height, 720.0)), default=720))
    scale = clamp_display_scale(display_scale)
    pixel_count = float(width) * float(height)

    profile = {
        "name": "default",
        "scale_boost": 1.0,
        "window_boost": 1.0,
    }

    if scale > 1.08:
        return profile

    if pixel_count >= (3840.0 * 2160.0 * 0.90) and scale <= 1.10:
        profile["name"] = "uhd_low_scale"
        profile["scale_boost"] = 1.12
        profile["window_boost"] = 1.16
        return profile

    if pixel_count >= (2560.0 * 1440.0 * 0.92) and scale <= 1.05:
        profile["name"] = "qhd_low_scale"
        profile["scale_boost"] = 1.08
        profile["window_boost"] = 1.10
        return profile

    if width >= 3200 and height >= 1400 and scale <= 1.05:
        profile["name"] = "wide_low_scale"
        profile["scale_boost"] = 1.08
        profile["window_boost"] = 1.10
        return profile

    return profile


def compute_centered_toplevel_geometry(
    screen_width,
    screen_height,
    width_px,
    height_px,
    *,
    min_width=260,
    min_height=160,
    max_width_ratio=0.92,
    max_height_ratio=0.90,
    anchor_rect=None,
    virtual_root_rect=None,
):
    # Center popups and clamp them to either anchor rect or monitor bounds.
    screen_width = max(640, _to_int(round(_to_float(screen_width, 1280.0)), default=1280))
    screen_height = max(480, _to_int(round(_to_float(screen_height, 720.0)), default=720))
    max_width_ratio = max(0.50, min(0.98, _to_float(max_width_ratio, 0.92)))
    max_height_ratio = max(0.40, min(0.98, _to_float(max_height_ratio, 0.90)))

    target_width = max(220, _to_int(round(_to_float(width_px, 0.0)), default=220))
    target_height = max(140, _to_int(round(_to_float(height_px, 0.0)), default=140))
    max_width = max(220, int(round(screen_width * max_width_ratio)))
    max_height = max(140, int(round(screen_height * max_height_ratio)))

    width = min(target_width, max_width, screen_width)
    height = min(target_height, max_height, screen_height)
    width = max(220, int(width))
    height = max(140, int(height))

    min_width = max(220, _to_int(round(_to_float(min_width, 0.0)), default=220))
    min_height = max(140, _to_int(round(_to_float(min_height, 0.0)), default=140))
    min_width = min(min_width, width)
    min_height = min(min_height, height)

    can_anchor = anchor_rect is not None and virtual_root_rect is not None
    if can_anchor:
        try:
            ax, ay, aw, ah = anchor_rect
            vx, vy, vw, vh = virtual_root_rect
            ax = _to_int(ax, 0)
            ay = _to_int(ay, 0)
            aw = max(1, _to_int(aw, 1))
            ah = max(1, _to_int(ah, 1))
            vx = _to_int(vx, 0)
            vy = _to_int(vy, 0)
            vw = max(1, _to_int(vw, screen_width))
            vh = max(1, _to_int(vh, screen_height))
            x = int(round(ax + ((aw - width) / 2.0)))
            y = int(round(ay + ((ah - height) / 2.0)))
            max_x = max(vx, (vx + vw) - width)
            max_y = max(vy, (vy + vh) - height)
            x = max(vx, min(max_x, x))
            y = max(vy, min(max_y, y))
        except Exception:
            x = max(0, int(round((screen_width - width) / 2.0)))
            y = max(0, int(round((screen_height - height) / 2.0)))
    else:
        x = max(0, int(round((screen_width - width) / 2.0)))
        y = max(0, int(round((screen_height - height) / 2.0)))

    return {
        "width": int(width),
        "height": int(height),
        "x": int(x),
        "y": int(y),
        "min_width": int(min_width),
        "min_height": int(min_height),
    }
