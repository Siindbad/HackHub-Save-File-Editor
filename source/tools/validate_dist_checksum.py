#!/usr/bin/env python3
"""Validate dist checksum artifact for shipped update payload."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re

def _parse_checksum_text(text: str, asset_name: str) -> str | None:
    asset_name = (asset_name or "").strip().lower()
    single_hash_re = re.compile(r"^[0-9a-fA-F]{64}$")
    hash_anywhere_re = re.compile(r"\b[0-9a-fA-F]{64}\b")
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if single_hash_re.fullmatch(line):
            return line.lower()
        if asset_name and asset_name not in line.lower():
            continue
        match = hash_anywhere_re.search(line)
        if match:
            return match.group(0).lower()
    return None


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def _resolve_dist_paths(dist_dir_raw: str, exe_name: str, checksum_name: str) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    # Restrict artifact names to flat file names; no path separators from CLI input.
    dist_dir = pathlib.Path(dist_dir_raw).expanduser()
    dist_dir = dist_dir.resolve()

    for arg_name, file_name in (("--exe-name", exe_name), ("--checksum-name", checksum_name)):
        parsed_name = pathlib.Path(str(file_name or "").strip())
        if (
            not parsed_name.name
            or parsed_name.name != str(file_name or "").strip()
            or parsed_name.is_absolute()
            or any(part == ".." for part in parsed_name.parts)
        ):
            raise ValueError(f"{arg_name} must be a file name without path separators.")

    exe_path = (dist_dir / exe_name).resolve()
    checksum_path = (dist_dir / checksum_name).resolve()
    if not exe_path.is_relative_to(dist_dir) or not checksum_path.is_relative_to(dist_dir):
        raise ValueError("Artifact paths must resolve under --dist-dir.")
    return dist_dir, exe_path, checksum_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--exe-name", default="sins_editor-onedir.zip")
    parser.add_argument("--checksum-name", default="sins_editor-onedir.zip.sha256")
    parser.add_argument(
        "--require",
        action="store_true",
        help="Fail if exe/checksum file is missing.",
    )
    args = parser.parse_args()

    try:
        _, exe_path, checksum_path = _resolve_dist_paths(args.dist_dir, args.exe_name, args.checksum_name)
    except ValueError as exc:
        print(f"Checksum validation failed: {exc}")
        return 1

    if not exe_path.is_file():
        if args.require:
            print(f"Checksum validation failed: missing asset '{exe_path}'.")
            return 1
        print(f"Checksum validation skipped: '{exe_path}' not found.")
        return 0

    if not checksum_path.is_file():
        print(f"Checksum validation failed: missing checksum file '{checksum_path}'.")
        return 1

    expected = _parse_checksum_text(
        checksum_path.read_text(encoding="utf-8", errors="replace"),
        args.exe_name,
    )
    if not expected:
        print(
            "Checksum validation failed: could not parse expected SHA-256 "
            f"from '{checksum_path}'."
        )
        return 1

    actual = _sha256_file(exe_path)
    if actual != expected:
        print(
            "Checksum validation failed: digest mismatch for "
            f"'{exe_path.name}'. expected={expected} actual={actual}"
        )
        return 1

    print(f"Checksum validation passed: {exe_path.name} matches {checksum_path.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
