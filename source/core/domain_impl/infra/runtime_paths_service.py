"""Runtime data path resolution helpers."""

import os
from typing import Any


def _normalized_home(expected_errors: Any) -> str:
    try:
        return os.path.abspath(os.path.expanduser("~"))
    except expected_errors:
        return os.path.abspath(os.getcwd())


def _safe_windows_base(base: Any, expected_errors: Any) -> str:
    # Runtime path safety: keep env-derived base rooted under user home.
    # If LOCALAPPDATA/APPDATA points outside home, fall back to home.
    home = _normalized_home(expected_errors)
    try:
        candidate = os.path.abspath(str(base or "").strip())
    except expected_errors:
        return home
    if not candidate:
        return home
    try:
        if os.path.commonpath([home, candidate]) == home:
            return candidate
    except expected_errors:
        return home
    return home


def runtime_data_dir(runtime_dir_name: Any, create: Any, platform_name: Any, env: Any, expected_errors: Any) -> Any:
    """Resolve runtime data directory path with platform-aware base fallback."""
    base = None
    match platform_name:
        case "win32":
            env_base = str(env.get("LOCALAPPDATA", "")).strip() or str(env.get("APPDATA", "")).strip()
            base = _safe_windows_base(env_base, expected_errors)
        case _:
            base = None
    if not base:
        try:
            home = os.path.expanduser("~")
            match platform_name:
                case "win32":
                    base = home
                case _:
                    base = os.path.join(home, ".local", "state")
        except expected_errors:
            base = os.getcwd()
    target = os.path.join(base, runtime_dir_name)
    if create:
        try:
            os.makedirs(target, exist_ok=True)
        except expected_errors:
            return os.getcwd()
    return target
