"""Mode-scoped tree style application helpers.

Lets INPUT and JSON modes evolve tree visuals independently while sharing the
same tree data model and selection behavior.
"""

from tkinter import ttk
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def _mode_palette(owner, mode):
    theme = getattr(owner, "_theme", {}) or {}
    normalized = str(mode or "JSON").upper()
    match normalized:
        case "INPUT":
            return {
                "panel": theme.get("input_tree_panel", theme.get("panel", "#161b24")),
                "tree_fg": theme.get("input_tree_fg", theme.get("tree_fg", theme.get("fg", "#e6e6e6"))),
                "select_bg": theme.get("input_tree_select_bg", theme.get("select_bg", "#2f3a4d")),
                "select_fg": theme.get("input_tree_select_fg", theme.get("select_fg", "#ffffff")),
            }
        case _:
            return {
                "panel": theme.get("json_tree_panel", theme.get("panel", "#161b24")),
                "tree_fg": theme.get("json_tree_fg", theme.get("tree_fg", theme.get("fg", "#e6e6e6"))),
                "select_bg": theme.get("json_tree_select_bg", theme.get("select_bg", "#2f3a4d")),
                "select_fg": theme.get("json_tree_select_fg", theme.get("select_fg", "#ffffff")),
            }


def apply_tree_mode(owner: Any, mode: Any) -> Any:
    # Apply mode-specific tree palette without mutating tree data/selection state.
    tree = getattr(owner, "tree", None)
    if tree is None:
        return
    try:
        if not tree.winfo_exists():
            return
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return
    palette = _mode_palette(owner, mode)
    try:
        style = ttk.Style(owner.root)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        style = None
    try:
        owner._apply_tree_style(
            style=style,
            panel=palette["panel"],
            tree_fg=palette["tree_fg"],
            select_bg=palette["select_bg"],
            select_fg=palette["select_fg"],
        )
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return
    try:
        owner._refresh_tree_item_markers()
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        pass
