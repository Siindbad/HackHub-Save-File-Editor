"""Update asset download and validation helpers."""

import os
import tempfile
import zipfile
from typing import Any
from core.exceptions import AppRuntimeError


def download_dist_asset(owner: Any) -> Any:
    """Download latest update asset and validate payload integrity/trust signals."""
    release_info = None
    try:
        release_info = owner._fetch_latest_release_info()
    except RuntimeError:
        release_info = None
    url = owner._release_asset_download_url(release_info, owner.GITHUB_ASSET_NAME)
    if not url:
        url = owner._dist_url(owner.GITHUB_ASSET_NAME)
    tmp_dir = tempfile.mkdtemp(prefix="sins_update_")
    new_path = os.path.join(tmp_dir, owner.GITHUB_ASSET_NAME)
    owner._download_to_file_with_retries(url, new_path)
    if not os.path.isfile(new_path) or os.path.getsize(new_path) <= 0:
        raise AppRuntimeError("Downloaded update is empty.")
    update_asset_name = str(getattr(owner, "GITHUB_ASSET_NAME", "")).strip().lower()
    if update_asset_name.endswith(".zip"):
        if not zipfile.is_zipfile(new_path):
            raise AppRuntimeError("Downloaded update is not a valid ZIP package.")
    else:
        # Basic sanity check for a Windows PE executable.
        with open(new_path, "rb") as handle:
            signature = handle.read(2)
        if signature != b"MZ":
            raise AppRuntimeError("Downloaded update is not a valid EXE file.")
    expected_sha256 = owner._fetch_dist_asset_sha256(release_info=release_info)
    if not expected_sha256:
        if owner.UPDATE_REQUIRE_SHA256:
            raise AppRuntimeError("Update checksum file missing or invalid.")
    else:
        actual_sha256 = owner._sha256_file(new_path).strip().lower()
        if actual_sha256 != expected_sha256:
            raise AppRuntimeError("Downloaded update checksum mismatch.")
    if not update_asset_name.endswith(".zip"):
        owner._verify_downloaded_update_signature(new_path)
    return new_path
