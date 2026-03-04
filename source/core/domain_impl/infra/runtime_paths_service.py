"""Runtime data path resolution helpers."""

import os
import re
from typing import Any


def _normalized_home(expected_errors: Any) -> str:
    try:
        return os.path.abspath(os.path.expanduser("~"))
    except expected_errors:
        return os.path.abspath(os.getcwd())


def _safe_windows_base(base: Any, expected_errors: Any) -> str:
    # Runtime path safety: block known system locations, otherwise allow explicit env override.
    # This keeps CI/test win32 simulation deterministic across non-Windows hosts.
    home = _normalized_home(expected_errors)
    drive_pattern = re.compile(r"^[A-Za-z]:[\\/]")
    try:
        raw = str(base or "").strip()
    except expected_errors:
        return home
    if not raw:
        return home

    normalized_raw = raw.replace("/", "\\").lower()
    if normalized_raw.startswith("c:\\windows\\system32") or normalized_raw.startswith("c:\\windows\\"):
        return home

    if drive_pattern.match(raw):
        return raw

    try:
        candidate = os.path.abspath(raw)
    except expected_errors:
        return home

    if os.path.isabs(raw):
        return candidate

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
