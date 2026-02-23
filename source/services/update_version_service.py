"""Update version resolution helpers."""
from typing import Any


def fetch_dist_version(owner: Any) -> Any:
    """Resolve latest dist version with release-tag preference and file fallback."""
    # Prefer immutable release metadata (tag) over mutable branch files.
    release_info = None
    try:
        release_info = owner._fetch_latest_release_info()
    except RuntimeError:
        release_info = None
    if isinstance(release_info, dict):
        tag_name = str(release_info.get("tag_name", "")).strip()
        if tag_name:
            return tag_name

    # Compatibility fallback: read version asset from latest release download URL.
    url = owner._dist_url(owner.DIST_VERSION_FILE)
    data = owner._download_bytes_with_retries(url)
    data = data.decode("utf-8", errors="replace")
    return data.strip()
