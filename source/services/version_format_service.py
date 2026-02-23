"""Version parse/format helpers shared by update and display flows."""
from typing import Any


def release_version(version: Any) -> Any:
    """Parse version text into numeric tuple."""
    if not version:
        return ()
    cleaned = str(version).strip().lstrip("vV")
    parts = []
    for token in cleaned.split("."):
        try:
            parts.append(int(token))
        except ValueError:
            break
    return tuple(parts)


def format_version(version_tuple: Any) -> Any:
    """Format numeric version tuple into dotted text."""
    if not version_tuple:
        return ""
    return ".".join(str(part) for part in version_tuple)
