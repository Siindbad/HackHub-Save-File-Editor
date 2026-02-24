"""README popup formatting and rendering helpers."""

import os
import re
import textwrap
from typing import Any


def format_readme_content(content: Any, wrap_width: Any) -> str:
    """Wrap readable prose while preserving section/divider formatting."""
    width = max(56, int(wrap_width or 0))
    out_lines = []
    in_change_logs = False
    for raw_line in str(content or "").splitlines():
        line = raw_line.rstrip()
        # Preserve centered/indented ASCII lines exactly as generated.
        if line and (len(line) - len(line.lstrip(" ")) > 0):
            out_lines.append(line)
            continue
        stripped = line.strip()
        if not stripped:
            out_lines.append("")
            continue
        if re.fullmatch(r"=+", stripped):
            # Normalize divider length to current README viewport width.
            out_lines.append("=" * width)
            continue

        if stripped.upper() == "[ CHANGE LOGS ]":
            in_change_logs = True
            out_lines.append(stripped)
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            # Keep changelog scope active for the version marker only.
            if in_change_logs and not re.match(r"^\[\s*Version\b.*\]$", stripped, re.IGNORECASE):
                in_change_logs = False
            out_lines.append(stripped)
            continue

        num_match = re.match(r"^(\s*\d+\.\s+)(.+)$", line)
        bullet_match = re.match(r"^(\s*-\s+)(.+)$", line)
        if num_match or bullet_match:
            match = num_match or bullet_match
            prefix = match.group(1)
            body = match.group(2).strip()
            if in_change_logs and bullet_match:
                # Keep changelog bullets single-line so release notes stay aligned.
                out_lines.append(prefix + body)
                continue
            body_width = max(24, width - len(prefix))
            wrapped = textwrap.wrap(
                body,
                width=body_width,
                break_long_words=False,
                break_on_hyphens=False,
            )
            if not wrapped:
                out_lines.append(prefix.rstrip())
                continue
            out_lines.append(prefix + wrapped[0])
            continuation_prefix = " " * len(prefix)
            out_lines.extend(continuation_prefix + chunk for chunk in wrapped[1:])
            continue

        wrapped = textwrap.wrap(
            stripped,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if wrapped:
            out_lines.extend(wrapped)
        else:
            out_lines.append("")
    return "\n".join(out_lines)


def show_readme(
    owner: Any,
    position_hint: Any = None,
    *,
    tk_module: Any,
    ttk_module: Any,
    tkfont_module: Any,
    messagebox_module: Any,
    expected_errors: Any,
) -> None:
    theme = getattr(owner, "_theme", None)
    base_dir = owner._resource_base_dir()
    readme_path = os.path.join(base_dir, "assets", "Readme.txt")
    content = ""
    if os.path.isfile(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as handle:
                content = handle.read()
        except expected_errors as exc:
            messagebox_module.showerror("ReadMe", f"Failed to load README.md: {exc}")
            return
    else:
        content = "Readme.txt not found in assets."

    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()

    existing = getattr(owner, "_readme_window", None)
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.destroy()
        except (tk_module.TclError, RuntimeError, AttributeError):
            pass

    window = tk_module.Toplevel(owner.root)
    owner._readme_window = window
    window.title("ReadMe")
    window.transient(owner.root)
    window.bind(
        "<Destroy>",
        lambda _evt, win=window: setattr(owner, "_readme_window", None)
        if getattr(owner, "_readme_window", None) is win
        else None,
        add="+",
    )
    if theme:
        window.configure(bg=theme["bg"])
        try:
            owner._apply_windows_titlebar_theme(
                bg=theme.get("title_bar_bg"),
                fg=theme.get("title_bar_fg"),
                border=theme.get("title_bar_border"),
                window_widget=window,
            )
            window.after(
                0,
                lambda win=window, th=theme: owner._apply_windows_titlebar_theme(
                    bg=th.get("title_bar_bg"),
                    fg=th.get("title_bar_fg"),
                    border=th.get("title_bar_border"),
                    window_widget=win,
                ),
            )
        except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            pass

    frame = ttk_module.Frame(window)
    frame.pack(fill="both", expand=True, padx=8, pady=8)

    mono = owner._readme_font_for_theme()
    lines = content.splitlines() or [""]
    trimmed_lengths = [len(line.rstrip()) for line in lines if line.rstrip()]
    if trimmed_lengths:
        sorted_lengths = sorted(trimmed_lengths)
        p90_index = max(0, int((len(sorted_lengths) - 1) * 0.90))
        target_chars = sorted_lengths[p90_index] + 2
    else:
        target_chars = 80
    # Keep README wider so changelog bullets do not need forced formatter wraps.
    target_chars = max(78, min(118, target_chars + 8))
    if variant == "KAMUE":
        content = owner._apply_kamue_readme_header(content, center_width=target_chars)
        lines = content.splitlines() or [""]
    elif variant == "SIINDBAD":
        content = owner._apply_siindbad_readme_header(content, center_width=target_chars)
        lines = content.splitlines() or [""]
    # Keep content compact while avoiding awkward single-word wraps on long lines.
    readme_wrap_chars = max(72, target_chars - 1)
    # Small right-side gutter so content does not hug the final visible column.
    readme_view_chars = readme_wrap_chars + 2
    content = format_readme_content(content, wrap_width=readme_wrap_chars)
    lines = content.splitlines() or [""]

    if variant == "KAMUE":
        readme_bg = theme.get("panel", "#0d061c") if theme else "#0d061c"
        readme_fg = "#efe5ff"
        readme_border = readme_bg
        readme_highlight = 0
    else:
        readme_bg = theme.get("panel", "#161b24") if theme else "#161b24"
        readme_fg = "#dce8f4"
        readme_border = theme.get("panel", "#161b24") if theme else "#161b24"
        readme_highlight = 1

    text = tk_module.Text(frame, wrap="none", font=mono, width=readme_view_chars)
    text.pack(fill="both", expand=True, side="left")
    v_scroll_style = getattr(owner, "_v_scrollbar_style", "Vertical.TScrollbar")
    v_scroll = ttk_module.Scrollbar(frame, orient="vertical", command=text.yview, style=v_scroll_style)
    v_scroll.pack(fill="y", side="right")
    h_scroll_style = getattr(owner, "_h_scrollbar_style", "Horizontal.TScrollbar")
    h_scroll = ttk_module.Scrollbar(frame, orient="horizontal", command=text.xview, style=h_scroll_style)
    h_scroll.pack(fill="x", side="bottom")
    text.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
    if theme:
        text.configure(
            bg=readme_bg,
            fg=readme_fg,
            insertbackground=readme_fg,
            selectbackground=theme["select_bg"],
            selectforeground=theme["select_fg"],
            relief="flat",
            highlightthickness=readme_highlight,
            highlightbackground=readme_border,
            highlightcolor=readme_border,
        )
    text.insert("1.0", content)
    text.configure(state="disabled")
    try:
        font = tkfont_module.Font(font=mono)
        char_w = font.measure("M")
        line_h = font.metrics("linespace")
        width_px = char_w * readme_view_chars + 56
        height_px = min(680, max(360, line_h * min(len(lines) + 2, 38)))
        popup_scale = max(0.9, min(1.2, float(getattr(owner, "_display_scale", 1.0) or 1.0)))
        owner._apply_centered_toplevel_geometry(
            window,
            width_px=int(round(width_px * popup_scale)),
            height_px=int(round(height_px * popup_scale)),
            min_width=640,
            min_height=360,
            max_width_ratio=0.92,
            max_height_ratio=0.90,
        )
        if position_hint is not None:
            try:
                window.update_idletasks()
                w = max(220, int(window.winfo_width()))
                h = max(140, int(window.winfo_height()))
                screen_w, screen_h = owner._screen_size()
                px, py = int(position_hint[0]), int(position_hint[1])
                max_x = max(0, int(screen_w) - w)
                max_y = max(0, int(screen_h) - h)
                px = max(0, min(max_x, px))
                py = max(0, min(max_y, py))
                window.geometry(f"{w}x{h}+{px}+{py}")
            except (tk_module.TclError, RuntimeError, TypeError, ValueError, AttributeError):
                pass
    except (tk_module.TclError, RuntimeError, TypeError, ValueError, AttributeError):
        owner._apply_centered_toplevel_geometry(
            window,
            width_px=760,
            height_px=520,
            min_width=640,
            min_height=360,
            max_width_ratio=0.92,
            max_height_ratio=0.90,
        )
        if position_hint is not None:
            try:
                window.update_idletasks()
                w = max(220, int(window.winfo_width()))
                h = max(140, int(window.winfo_height()))
                screen_w, screen_h = owner._screen_size()
                px, py = int(position_hint[0]), int(position_hint[1])
                max_x = max(0, int(screen_w) - w)
                max_y = max(0, int(screen_h) - h)
                px = max(0, min(max_x, px))
                py = max(0, min(max_y, py))
                window.geometry(f"{w}x{h}+{px}+{py}")
            except (tk_module.TclError, RuntimeError, TypeError, ValueError, AttributeError):
                pass
