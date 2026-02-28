"""INPUT mode paned-window lock orchestration helpers."""

from typing import Any


def repair_input_mode_tree_pane_mapping(owner: Any, *, tk_module: Any) -> bool:
    if str(getattr(owner, "_editor_mode", "JSON")).upper() != "INPUT":
        return False
    body = getattr(owner, "_body_panedwindow", None)
    tree = getattr(owner, "tree", None)
    if body is None or tree is None:
        return False
    left = getattr(tree, "master", None)
    if left is None:
        return False
    try:
        if not bool(body.winfo_ismapped()):
            return False
    except (tk_module.TclError, RuntimeError, AttributeError):
        return False
    try:
        if bool(left.winfo_ismapped()):
            return False
    except (tk_module.TclError, RuntimeError, AttributeError):
        return False
    try:
        body.pane(left, weight=1)
        return True
    except (tk_module.TclError, RuntimeError, AttributeError):
        return False


def cancel_input_mode_paned_lock_recheck(owner: Any, *, tk_module: Any) -> None:
    after_id = getattr(owner, "_input_mode_paned_recheck_after_id", None)
    owner._input_mode_paned_recheck_after_id = None
    if not after_id:
        return
    root = getattr(owner, "root", None)
    if root is None:
        return
    try:
        root.after_cancel(after_id)
    except (tk_module.TclError, RuntimeError, AttributeError):
        return


def schedule_input_mode_paned_lock_recheck(owner: Any, delay_ms: Any = 72, *, tk_module: Any) -> None:
    if str(getattr(owner, "_editor_mode", "JSON")).upper() != "INPUT":
        return
    root = getattr(owner, "root", None)
    if root is None:
        return
    owner._cancel_input_mode_paned_lock_recheck()

    def _run_recheck() -> None:
        owner._input_mode_paned_recheck_after_id = None
        owner._sync_input_mode_paned_sash_lock("INPUT")

    try:
        owner._input_mode_paned_recheck_after_id = root.after(
            max(16, int(delay_ms)),
            _run_recheck,
        )
    except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
        owner._input_mode_paned_recheck_after_id = None


def sync_input_mode_paned_sash_lock(owner: Any, mode: Any = None, *, tk_module: Any) -> None:
    """Disable divider dragging in INPUT mode and keep sash at its locked position."""
    body = getattr(owner, "_body_panedwindow", None)
    if body is None:
        return
    lock_active = bool(getattr(owner, "_input_mode_paned_lock_active", False))
    try:
        body_class = str(body.winfo_class() or "")
    except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
        body_class = "TPanedwindow"
    default_tags = tuple(getattr(owner, "_body_paned_bindtags_default", ()) or ())
    if not default_tags:
        try:
            default_tags = tuple(body.bindtags())
        except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            default_tags = ()
        if default_tags:
            owner._body_paned_bindtags_default = default_tags
    use_mode = str(mode or getattr(owner, "_editor_mode", "JSON")).upper()
    try:
        current_x = int(body.sashpos(0))
    except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
        current_x = None
    try:
        body_width = int(body.winfo_width() or 0)
    except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
        body_width = 0
    fallback_x = None
    if body_width > 160:
        min_tree_width = 180
        min_editor_width = 320
        max_sash = max(min_tree_width, int(body_width) - min_editor_width)
        candidate = max(min_tree_width, int(round(float(body_width) * 0.30)))
        candidate = min(candidate, max_sash)
        if candidate > 10:
            fallback_x = int(candidate)
    # Persist a sane first sash position as INPUT lock baseline so
    # JSON-mode manual sash moves do not change INPUT layout.
    # Ignore near-zero values to avoid capturing pre-layout sash=0.
    fixed_input_x = getattr(owner, "_input_mode_paned_fixed_sash_x", None)
    try:
        fixed_input_x = int(fixed_input_x) if fixed_input_x is not None else None
    except (TypeError, ValueError):
        fixed_input_x = None
    if fixed_input_x is not None and int(fixed_input_x) <= 10:
        fixed_input_x = None
    if fixed_input_x is None and current_x is not None and int(current_x) > 10:
        fixed_input_x = int(current_x)
        owner._input_mode_paned_fixed_sash_x = fixed_input_x
    if fixed_input_x is None and fallback_x is not None:
        fixed_input_x = int(fallback_x)
        owner._input_mode_paned_fixed_sash_x = fixed_input_x
    if use_mode != "INPUT":
        owner._cancel_input_mode_paned_lock_recheck()
        if not lock_active and getattr(owner, "_input_mode_paned_sash_x", None) is None:
            return
        owner._input_mode_paned_sash_x = None
        if lock_active and default_tags:
            try:
                if tuple(body.bindtags()) != default_tags:
                    body.bindtags(default_tags)
            except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                return
        owner._input_mode_paned_lock_active = False
        return
    if default_tags and not lock_active:
        locked_tags = tuple(tag for tag in default_tags if str(tag) != body_class)
        if not locked_tags:
            locked_tags = default_tags
        try:
            if tuple(body.bindtags()) != locked_tags:
                body.bindtags(locked_tags)
        except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            owner._schedule_input_mode_paned_lock_recheck()
            return
    owner._input_mode_paned_lock_active = True
    # Windows zoom->normal can leave the tree pane attached-but-unmapped.
    # Reassert pane config so INPUT tree does not disappear until a mode toggle.
    repair_input_mode_tree_pane_mapping(owner, tk_module=tk_module)
    if current_x is None:
        owner._schedule_input_mode_paned_lock_recheck()
        return
    locked_x = getattr(owner, "_input_mode_paned_sash_x", None)
    if locked_x is None:
        if fixed_input_x is not None:
            target_x = int(fixed_input_x)
        elif int(current_x) > 10:
            target_x = int(current_x)
            owner._input_mode_paned_fixed_sash_x = int(current_x)
        elif fallback_x is not None:
            target_x = int(fallback_x)
            owner._input_mode_paned_fixed_sash_x = int(target_x)
        else:
            # Wait for a stable configure pass before locking INPUT sash.
            owner._schedule_input_mode_paned_lock_recheck()
            return
        owner._input_mode_paned_sash_x = int(target_x)
        locked_x = int(target_x)
    else:
        try:
            locked_x = int(locked_x)
        except (TypeError, ValueError):
            locked_x = None
    if locked_x is None:
        owner._schedule_input_mode_paned_lock_recheck()
        return
    # Self-heal if an older transient lock captured an invalid near-zero split.
    if int(locked_x) <= 10:
        if int(current_x) > 10:
            locked_x = int(current_x)
            owner._input_mode_paned_sash_x = int(locked_x)
            if fixed_input_x is None:
                owner._input_mode_paned_fixed_sash_x = int(locked_x)
        elif fallback_x is not None:
            locked_x = int(fallback_x)
            owner._input_mode_paned_sash_x = int(locked_x)
            if fixed_input_x is None:
                owner._input_mode_paned_fixed_sash_x = int(locked_x)
    apply_x = int(locked_x)
    if body_width > 160:
        min_tree_width = 180
        min_editor_width = 320
        max_sash = max(min_tree_width, int(body_width) - min_editor_width)
        apply_x = max(min_tree_width, min(apply_x, max_sash))
    if int(apply_x) != current_x:
        try:
            body.sashpos(0, int(apply_x))
        except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            owner._schedule_input_mode_paned_lock_recheck()
            return
    # If metrics are still transient, recheck shortly so INPUT can recover
    # without requiring a mode toggle.
    if int(apply_x) <= 10 or body_width <= 160:
        owner._schedule_input_mode_paned_lock_recheck()
        return
    owner._cancel_input_mode_paned_lock_recheck()
