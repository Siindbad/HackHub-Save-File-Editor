from typing import Optional, Tuple


def _to_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        return float(default)


def _to_int(value, default=0) -> int:
    try:
        return int(value)
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        return int(default)


def resolve_find_entry_base_width(style: str, search_spec_width: Optional[int] = None) -> int:
    style = str(style or "").upper()
    if style == "B":
        width = _to_int(search_spec_width, default=172)
        return max(1, width)
    if style == "C":
        return 154
    return 156


def compute_mode_spacing(
    mode: str,
    style: str,
    default_host_padx: Tuple[int, int],
    default_btn_padx: Tuple[int, int],
) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    mode_name = str(mode or "").lower()
    style_name = str(style or "").upper()
    if mode_name == "maximized" and style_name == "B":
        # Pull these controls together only in max mode.
        return (1, 0), (0, 0)
    return tuple(default_host_padx), tuple(default_btn_padx)


def compute_search_compaction_target(
    toolbar_w,
    logo_w,
    base_width: int,
    style: str,
) -> Optional[int]:
    toolbar_w = _to_float(toolbar_w, default=0.0)
    logo_w = _to_float(logo_w, default=0.0)
    base_width = max(1, _to_int(base_width, default=1))
    style_name = str(style or "").upper()
    if toolbar_w <= 0.0 or logo_w <= 0.0:
        return None

    overflow = int(round(toolbar_w - logo_w))
    if overflow <= 0:
        return None

    if style_name == "B":
        min_width = max(120, int(round(base_width * 0.68)))
    else:
        min_width = max(96, int(round(base_width * 0.70)))

    target = max(min_width, int(base_width - overflow))
    if target >= base_width:
        return None
    return target


def compute_centered_toolbar_position(
    toolbar_w,
    toolbar_h,
    host_w,
    host_h,
    logo_center_rel=None,
) -> Optional[Tuple[int, int]]:
    toolbar_w = _to_int(toolbar_w, default=0)
    toolbar_h = _to_int(toolbar_h, default=0)
    host_w = _to_int(host_w, default=0)
    host_h = _to_int(host_h, default=0)
    if toolbar_w <= 0 or host_w <= 0:
        return None

    if logo_center_rel is None:
        logo_center_rel = float(host_w) / 2.0
    else:
        logo_center_rel = _to_float(logo_center_rel, default=(float(host_w) / 2.0))

    x = int(round(float(logo_center_rel) - (float(toolbar_w) / 2.0)))
    max_x = max(0, int(host_w - toolbar_w))
    x = max(0, min(max_x, x))
    y = max(0, int((host_h - toolbar_h) / 2.0))
    return x, y
