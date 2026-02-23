"""Environment-token resolution helpers for update/bug-report flows."""

import os
from typing import Any


def resolve_token_from_env_names(*env_names: Any) -> Any:
    """Resolve first non-empty token from ordered env names."""
    for env_name in env_names:
        name = str(env_name or "").strip()
        if not name:
            continue
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def update_token_value(owner: Any) -> Any:
    """Resolve updater token with dedicated-env first, then legacy fallback."""
    return resolve_token_from_env_names(
        getattr(owner, "UPDATE_TOKEN_ENV", ""),
        getattr(owner, "GITHUB_TOKEN_ENV", ""),
    )


def bug_report_token_env_name(owner: Any) -> Any:
    """Resolve bug-report token env name with dedicated-env preference."""
    primary = str(getattr(owner, "BUG_REPORT_TOKEN_ENV", "") or "").strip()
    fallback = str(getattr(owner, "GITHUB_TOKEN_ENV", "") or "").strip()
    if primary and os.getenv(primary, "").strip():
        return primary
    if fallback:
        return fallback
    return primary


def has_bug_report_token(owner: Any) -> Any:
    """Return True when either dedicated or legacy bug-report token is present."""
    return bool(
        resolve_token_from_env_names(
            getattr(owner, "BUG_REPORT_TOKEN_ENV", ""),
            getattr(owner, "GITHUB_TOKEN_ENV", ""),
        )
    )
