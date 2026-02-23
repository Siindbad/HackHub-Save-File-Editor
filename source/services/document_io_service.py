"""Document I/O helpers for JSON and .hhsav data paths."""

import gzip
import json
import os
import tempfile
from typing import Any
from core.exceptions import AppRuntimeError


def load_document(path: Any) -> Any:
    """Load JSON-compatible document data from .json or .hhsav path."""
    use_path = str(path or "")
    if use_path.lower().endswith(".hhsav"):
        with gzip.open(use_path, "rb") as handle:
            raw = handle.read().decode("utf-8")
        return json.loads(raw)
    with open(use_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def build_pretty_json_payload(data: Any) -> Any:
    """Build UTF-8 text payload for normal Save operations."""
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def build_compact_json_bytes(data: Any) -> Any:
    """Build compact UTF-8 JSON bytes for .hhsav gzip export."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def export_hhsav_bytes(payload: Any, destination_path: Any, commit_file_fn: Any) -> Any:
    """Write compact JSON bytes into deterministic gzip container and commit."""
    use_destination = str(destination_path or "")
    if not use_destination:
        raise ValueError("Export destination path is required.")
    if not callable(commit_file_fn):
        raise ValueError("commit_file_fn is required.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        gzip_path = os.path.join(tmp_dir, "save.hhsav")
        with open(gzip_path, "wb") as raw_handle:
            with gzip.GzipFile(
                filename="",
                mode="wb",
                fileobj=raw_handle,
                compresslevel=9,
                mtime=0,
            ) as gz_handle:
                gz_handle.write(payload)
        if not os.path.isfile(gzip_path) or os.path.getsize(gzip_path) <= 0:
            raise AppRuntimeError("Exported .hhsav is empty.")
        commit_file_fn(gzip_path, use_destination)
