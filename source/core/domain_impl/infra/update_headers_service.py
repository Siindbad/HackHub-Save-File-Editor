"""Update request-header helpers."""
from typing import Any


def download_headers(token_value: Any="") -> Any:
    """Build update request headers with optional bearer token."""
    headers = {"User-Agent": "sins-editor"}
    token = str(token_value or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
