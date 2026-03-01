"""User settings load/save parsing helpers."""

from __future__ import annotations

import json
import os
from typing import Any

from core.domain_impl.infra import windows_runtime_service


_VALID_THEME_VARIANTS = frozenset({"SIINDBAD", "KAMUE", "GLITCH"})


def _candidate_paths(owner: Any, expected_errors: tuple[type[BaseException], ...]) -> list[str]:
    paths: list[str] = [str(owner._settings_path())]
    legacy_fn = getattr(owner, "_legacy_settings_path", None)
    if not callable(legacy_fn):
        return paths
    try:
        legacy_path = legacy_fn()
    except expected_errors:
        legacy_path = None
    if legacy_path:
        paths.append(str(legacy_path))
    return paths


def _coerce_startup_update_pref(
    raw_value: Any,
    default_value: bool,
) -> bool:
    if isinstance(raw_value, bool):
        return bool(raw_value)
    if isinstance(raw_value, (int, float)):
        return bool(int(raw_value))
    if isinstance(raw_value, str):
        token = raw_value.strip().lower()
        if token in ("1", "true", "yes", "on"):
            return True
        if token in ("0", "false", "no", "off"):
            return False
    return bool(default_value)


def _apply_loaded_values(owner: Any, payload: dict[str, Any]) -> None:
    font_size = payload.get("font_size")
    if isinstance(font_size, int) and 6 <= font_size <= 32:
        owner._font_size = font_size

    theme_variant = str(payload.get("app_theme", "")).upper()
    if theme_variant in _VALID_THEME_VARIANTS:
        owner._app_theme_variant = theme_variant

    owner._startup_update_check_enabled = _coerce_startup_update_pref(
        payload.get("startup_update_check"),
        bool(getattr(owner, "_startup_update_check_enabled", False)),
    )


def load_user_settings(
    owner: Any,
    *,
    expected_errors: tuple[type[BaseException], ...],
) -> None:
    """Load persisted user settings into runtime fields."""
    for path in _candidate_paths(owner, expected_errors):
        if not os.path.isfile(path):
            continue
        try:
            reader = getattr(owner, "_read_json_file", None)
            if callable(reader):
                payload = reader(path, encoding="utf-8")
            else:
                payload = windows_runtime_service.read_json_file(path=path, encoding="utf-8")
            if not isinstance(payload, dict):
                continue
            _apply_loaded_values(owner, payload)
            return
        except expected_errors:
            continue


def save_user_settings(
    owner: Any,
    *,
    expected_errors: tuple[type[BaseException], ...],
) -> None:
    """Persist runtime user settings to the configured settings path."""
    path = owner._settings_path()
    payload = {
        "font_size": int(owner._font_size),
        "app_theme": str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper(),
        "startup_update_check": bool(getattr(owner, "_startup_update_check_enabled", False)),
    }
    try:
        data = json.dumps(payload, ensure_ascii=False)
        writer = getattr(owner, "_write_text_file_atomic", None)
        if callable(writer):
            writer(path, data, encoding="utf-8")
            return
        windows_runtime_service.write_text_file_atomic(
            path=path,
            text=data,
            encoding="utf-8",
        )
    except expected_errors:
        return
