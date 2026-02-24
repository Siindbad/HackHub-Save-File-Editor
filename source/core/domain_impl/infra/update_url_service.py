"""Update/release URL builder helpers."""
from typing import Any


def manual_update_download_url(owner: Any) -> Any:
    """Build manual update fallback URL using GitHub Releases latest asset path."""
    return (
        f"https://github.com/{owner.GITHUB_OWNER}/{owner.GITHUB_REPO}"
        f"/releases/latest/download/{owner.GITHUB_ASSET_NAME}"
    )


def dist_url(owner: Any, filename: Any) -> Any:
    """Build fallback release-asset URL for a filename."""
    return (
        f"https://github.com/{owner.GITHUB_OWNER}/{owner.GITHUB_REPO}"
        f"/releases/latest/download/{filename}"
    )


def latest_release_api_url(owner: Any) -> Any:
    """Build GitHub API URL for latest release metadata."""
    return f"https://api.github.com/repos/{owner.GITHUB_OWNER}/{owner.GITHUB_REPO}/releases/latest"


def release_asset_download_url(release_info: Any, asset_name: Any) -> Any:
    """Resolve browser_download_url for named asset from release metadata payload."""
    if not isinstance(release_info, dict):
        return ""
    want = str(asset_name or "").strip().casefold()
    if not want:
        return ""
    assets = release_info.get("assets")
    if not isinstance(assets, list):
        return ""
    for item in assets:
        if not isinstance(item, dict):
            continue
        if str(item.get("name", "")).strip().casefold() != want:
            continue
        return str(item.get("browser_download_url", "")).strip()
    return ""
