"""Update checksum parsing and retrieval helpers."""

import re
from typing import Any


def extract_sha256_from_text(text: Any, asset_name: Any) -> Any:
    """Extract first matching SHA-256 digest from checksum text payload."""
    if not text:
        return None
    asset_name = str(asset_name or "").strip().lower()
    single_hash = re.compile(r"^[0-9a-fA-F]{64}$")
    hash_anywhere = re.compile(r"\b[0-9a-fA-F]{64}\b")
    for raw_line in str(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        candidate = line.split("#", 1)[0].strip()
        if not candidate:
            continue
        if single_hash.fullmatch(candidate):
            return candidate.lower()
        if asset_name and asset_name not in candidate.lower():
            continue
        match = hash_anywhere.search(candidate)
        if match:
            return match.group(0).lower()
    return None


def fetch_dist_asset_sha256(owner: Any, release_info: Any=None) -> Any:
    """Fetch release checksum for target asset from known checksum candidates."""
    if release_info is None:
        try:
            release_info = owner._fetch_latest_release_info()
        except RuntimeError:
            release_info = None
    candidates = [f"{owner.GITHUB_ASSET_NAME}.sha256"]
    for name in owner.DIST_ASSET_SHA256_CANDIDATES:
        if name not in candidates:
            candidates.append(name)
    for name in candidates:
        data = None
        try:
            url = owner._release_asset_download_url(release_info, name)
            if not url:
                url = owner._dist_url(name)
            data = owner._download_bytes_with_retries(url)
        except RuntimeError:
            data = None
        if data is None:
            continue
        parsed = extract_sha256_from_text(
            data.decode("utf-8", errors="replace"),
            owner.GITHUB_ASSET_NAME,
        )
        if parsed:
            return parsed
    return None
