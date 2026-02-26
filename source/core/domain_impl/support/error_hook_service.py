"""Unhandled exception hook wiring helpers."""
from typing import Any


def _is_non_crash_control_flow_exception(exc_type: Any, exc_value: Any) -> bool:
    """Skip crash logging for intentional process-interrupt exceptions."""
    candidates = []
    if exc_type is not None:
        candidates.append(exc_type)
    if exc_value is not None:
        candidates.append(type(exc_value))
    for candidate in candidates:
        try:
            if candidate in (KeyboardInterrupt, SystemExit):
                return True
            if isinstance(candidate, type) and issubclass(candidate, (KeyboardInterrupt, SystemExit)):
                return True
        except TypeError:
            continue
    return False


def forward_previous_sys_hook(prev: Any, current_handler: Any, exc_type: Any, exc_value: Any, exc_tb: Any, expected_errors: Any) -> Any:
    """Forward to previous sys.excepthook when callable and not self-recursive."""
    if callable(prev) and prev is not current_handler:
        try:
            prev(exc_type, exc_value, exc_tb)
        except expected_errors:
            pass


def resolve_thread_exception_args(args: Any) -> Any:
    """Normalize threading.excepthook args payload to safe fallback values."""
    return (
        getattr(args, "exc_type", Exception),
        getattr(args, "exc_value", Exception("Unknown thread exception")),
        getattr(args, "exc_traceback", None),
    )


def forward_previous_threading_hook(prev: Any, current_handler: Any, args: Any, expected_errors: Any) -> Any:
    """Forward to previous threading.excepthook when callable and not self-recursive."""
    if callable(prev) and prev is not current_handler:
        try:
            prev(args)
        except expected_errors:
            pass


def install_global_error_hooks(owner: Any, sys_module: Any, threading_module: Any, expected_errors: Any) -> Any:
    """Install global sys/thread/Tk exception hooks once with owner callbacks."""
    if owner._error_hooks_installed:
        return
    owner._error_hooks_installed = True
    try:
        owner._prev_sys_excepthook = sys_module.excepthook
        sys_module.excepthook = owner._handle_sys_excepthook
    except expected_errors:
        pass
    if hasattr(threading_module, "excepthook"):
        try:
            owner._prev_threading_excepthook = threading_module.excepthook
            threading_module.excepthook = owner._handle_threading_excepthook
        except expected_errors:
            pass
    try:
        owner.root.report_callback_exception = owner._handle_tk_callback_exception
    except expected_errors:
        pass


def handle_unhandled_exception(append_crash_log_fn: Any, show_crash_notice_once_fn: Any, context: Any, exc_type: Any, exc_value: Any, exc_tb: Any) -> Any:
    """Dispatch unhandled exception flow: skip control-flow interrupts, otherwise log + notify."""
    if _is_non_crash_control_flow_exception(exc_type, exc_value):
        return
    append_crash_log_fn(context, exc_type, exc_value, exc_tb)
    show_crash_notice_once_fn()
