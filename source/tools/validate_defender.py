#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = ROOT / "dist" / "sins_editor-onedir.zip"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Microsoft Defender local file-scan preflight for release artifacts."
    )
    parser.add_argument(
        "--file",
        default=str(DEFAULT_TARGET),
        help="Path to the artifact file to scan.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when Defender reports threats or scan execution errors.",
    )
    parser.add_argument(
        "--require-installed",
        action="store_true",
        help="Fail when MpCmdRun.exe is not available.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=600,
        help="Maximum scan runtime before timeout failure.",
    )
    return parser.parse_args()


def _truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _strict_enabled(cli_strict: bool) -> bool:
    if cli_strict:
        return True
    # Defender strict mode toggle:
    # - HACKHUB_DEFENDER_STRICT=1 => block on detections and execution errors
    # - HACKHUB_DEFENDER_STRICT=0 => record result but stay non-blocking
    return _truthy(os.getenv("HACKHUB_DEFENDER_STRICT", ""))


def _require_installed_enabled(cli_required: bool) -> bool:
    if cli_required:
        return True
    # Defender install requirement toggle:
    # - HACKHUB_DEFENDER_REQUIRE_INSTALLED=1 => missing MpCmdRun fails
    # - HACKHUB_DEFENDER_REQUIRE_INSTALLED=0 => missing MpCmdRun is reported as skipped
    return _truthy(os.getenv("HACKHUB_DEFENDER_REQUIRE_INSTALLED", ""))


def _timeout_seconds(cli_timeout: int) -> int:
    cli_value = max(30, int(cli_timeout))
    env_value = str(os.getenv("HACKHUB_DEFENDER_TIMEOUT_SECONDS", "")).strip()
    if not env_value:
        return cli_value
    try:
        return max(30, int(env_value))
    except ValueError:
        return cli_value


def _find_mpcmdrun() -> Path | None:
    from_path = shutil.which("MpCmdRun.exe")
    if from_path:
        return Path(from_path)

    candidates: list[Path] = []
    for env_name in ("ProgramFiles", "ProgramW6432"):
        base = str(os.getenv(env_name, "")).strip()
        if not base:
            continue
        candidates.extend(
            [
                Path(base) / "Windows Defender" / "MpCmdRun.exe",
                Path(base) / "Microsoft Defender" / "MpCmdRun.exe",
            ]
        )

    program_data = str(os.getenv("ProgramData", "")).strip()
    if program_data:
        platform_root = Path(program_data) / "Microsoft" / "Windows Defender" / "Platform"
        if platform_root.exists():
            versions = sorted(
                [p for p in platform_root.iterdir() if p.is_dir()],
                key=lambda p: p.name,
                reverse=True,
            )
            for version_dir in versions:
                candidates.append(version_dir / "MpCmdRun.exe")

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _extract_threat_count(output_text: str) -> tuple[bool, int]:
    text = str(output_text or "")
    if not text:
        return False, 0

    no_threat_patterns = (
        r"(?i)\bno threats? (were )?found\b",
        r"(?i)\bfound no threats?\b",
        r"(?i)\b0 threats? found\b",
    )
    for pattern in no_threat_patterns:
        if re.search(pattern, text):
            return False, 0

    count_match = re.search(r"(?i)\b(\d+)\s+threats?\s+found\b", text)
    if count_match:
        value = int(count_match.group(1))
        return (value > 0), value

    threat_patterns = (
        r"(?i)\bthreats?\s+found\b",
        r"(?i)\bthreat\b",
        r"(?i)\bmalware\b",
    )
    for pattern in threat_patterns:
        if re.search(pattern, text):
            return True, 1
    return False, 0


def main() -> int:
    args = _parse_args()
    strict = _strict_enabled(args.strict)
    require_installed = _require_installed_enabled(args.require_installed)
    timeout_seconds = _timeout_seconds(args.timeout_seconds)

    target = Path(args.file)
    if not target.is_absolute():
        target = ROOT / target
    if not target.exists():
        print(f"Defender gate failed: target file not found: {target}")
        return 1

    if not sys.platform.startswith("win"):
        print(
            "Defender summary: "
            "status=SKIPPED, source=unsupported_os, threat_detected=false, "
            "threat_count=0, exit_code=-1, mpcmd=none"
        )
        return 1 if require_installed else 0

    mpcmd = _find_mpcmdrun()
    if not mpcmd:
        print(
            "Defender summary: "
            "status=SKIPPED, source=no_mpcmd, threat_detected=false, "
            "threat_count=0, exit_code=-1, mpcmd=none"
        )
        if require_installed:
            print("Defender gate failed: MpCmdRun.exe required but not found.")
            return 1
        return 0

    command = [
        str(mpcmd),
        "-Scan",
        "-ScanType",
        "3",
        "-File",
        str(target),
        "-DisableRemediation",
    ]
    print("Running Defender gate:")
    print(" ".join(command))
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print(
            "Defender summary: "
            "status=ERROR, source=timeout, threat_detected=false, "
            "threat_count=0, exit_code=-1, mpcmd=MpCmdRun.exe"
        )
        if strict:
            print("Defender gate failed in strict mode.")
            return 1
        return 0

    combined = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    threat_detected, threat_count = _extract_threat_count(combined)
    status = "PASS"
    source = "local_scan"
    if threat_detected:
        status = "DETECTED"
    elif completed.returncode != 0:
        status = "ERROR"
        source = "scan_error"

    print(
        "Defender summary: "
        f"status={status}, "
        f"source={source}, "
        f"threat_detected={'true' if threat_detected else 'false'}, "
        f"threat_count={threat_count}, "
        f"exit_code={completed.returncode}, "
        "mpcmd=MpCmdRun.exe"
    )
    print(f"Defender path: {mpcmd}")

    if strict and status in {"DETECTED", "ERROR"}:
        print("Defender gate failed in strict mode.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
