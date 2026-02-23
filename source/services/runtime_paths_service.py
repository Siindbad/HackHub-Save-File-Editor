"""Runtime data path resolution helpers."""

import os
from typing import Any


def runtime_data_dir(runtime_dir_name: Any, create: Any, platform_name: Any, env: Any, expected_errors: Any) -> Any:
    """Resolve runtime data directory path with platform-aware base fallback."""
    base = None
    match platform_name:
        case "win32":
            base = str(env.get("LOCALAPPDATA", "")).strip() or str(env.get("APPDATA", "")).strip()
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
