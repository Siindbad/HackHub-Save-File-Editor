#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

SCRIPT_PATH = Path(__file__).resolve()
# Support both source repo path (`tools/...`) and mirrored public path (`source/tools/...`).
ROOT = SCRIPT_PATH.parents[2] if SCRIPT_PATH.parents[1].name.lower() == "source" else SCRIPT_PATH.parents[1]


BADGE_RE = re.compile(
    r"https://img\.shields\.io/badge/([^-\)]+)-([^-\)\?]+)-[^)\s]+",
    re.IGNORECASE,
)
TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
VERSION_RE = re.compile(
    r"Release(?:\s+version)?\s*:\s*\*{0,2}v?(\d+\.\d+\.\d+)\*{0,2}",
    re.IGNORECASE,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate SECURITY.md badges are synced with dist/security-report.txt."
    )
    parser.add_argument("--report", required=True, help="Path to dist/security-report.txt")
    parser.add_argument("--security-md", required=True, help="Path to SECURITY.md")
    parser.add_argument(
        "--version",
        default="",
        help="Expected release version (x.y.z). Defaults to app_version from report.",
    )
    return parser.parse_args()


def _normalize_gate_label(label: str) -> str:
    normalized = label.strip().upper().replace("_", " ")
    aliases = {
        "DEFENDER": "MICROSOFT DEFENDER",
        "VIRUSTOTAL": "VIRUS TOTAL",
        "PIP-AUDIT": "PIP AUDIT",
    }
    return aliases.get(normalized, normalized)


def _resolve_gate_result(status_text: str) -> str:
    raw = (status_text or "").strip().lower()
    if not raw:
        return "UNKNOWN"
    if re.search(r"(fail|error|blocked)", raw):
        return "FAIL"
    if re.search(r"(^skip|not_run)", raw):
        return "SKIP"
    if re.search(r"(pass|ok|clean|success|found_existing|uploaded|no_threat|no_issues|safe)", raw):
        return "PASS"
    return "UNKNOWN"


def _normalize_status(status_text: str) -> str:
    normalized = (status_text or "").strip().upper()
    aliases = {
        "SKIPPED": "SKIP",
        "PASSED": "PASS",
        "FAILED": "FAIL",
    }
    return aliases.get(normalized, normalized)


def _parse_report_map(report_path: Path) -> dict[str, str]:
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")
    report_map: dict[str, str] = {}
    for raw_line in report_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Za-z0-9_]+)\s*:\s*(.*)$", raw_line)
        if not match:
            continue
        report_map[match.group(1).strip().lower()] = match.group(2).strip()
    return report_map


def _expected_statuses(report_map: dict[str, str]) -> dict[str, str]:
    sha_match = (report_map.get("asset_sha256_match", "") or "").strip().lower()
    sha_status = "UNKNOWN"
    if sha_match == "true":
        sha_status = "PASS"
    elif sha_match == "false":
        sha_status = "FAIL"
    return {
        "SEMGREP": _resolve_gate_result(report_map.get("semgrep_status", "")),
        "TRUFFLEHOG": _resolve_gate_result(report_map.get("trufflehog_status", "")),
        "BANDIT": _resolve_gate_result(report_map.get("bandit_status", "")),
        "PIP AUDIT": _resolve_gate_result(report_map.get("pip_audit_status", "")),
        "SBOM": _resolve_gate_result(report_map.get("sbom_status", "")),
        "MICROSOFT DEFENDER": _resolve_gate_result(report_map.get("defender_status", "")),
        "VIRUS TOTAL": _resolve_gate_result(report_map.get("virustotal_status", "")),
        "SHA256": sha_status,
    }


def _parse_observed_badges(security_body: str) -> dict[str, str]:
    observed: dict[str, str] = {}
    status_tokens = {"PASS", "FAIL", "SKIP", "UNKNOWN"}

    def _extract_status(cell_text: str) -> str:
        text = str(cell_text or "").strip()
        if not text:
            return ""
        m = re.search(r"!\[(PASS|FAIL|SKIP|UNKNOWN)\]", text, re.IGNORECASE)
        if m:
            return _normalize_status(m.group(1))
        m = re.search(r"/badge/(PASS|FAIL|SKIP|UNKNOWN)(?:[-?]|%2D)", unquote(text), re.IGNORECASE)
        if m:
            return _normalize_status(m.group(1))
        m = re.search(r"-(PASS|FAIL|SKIP|UNKNOWN)(?:[-?]|%2D)", unquote(text), re.IGNORECASE)
        if m:
            return _normalize_status(m.group(1))
        return _normalize_status(text)

    for raw_line in security_body.splitlines():
        line = raw_line.strip()
        row = TABLE_ROW_RE.match(line)
        if not row:
            continue
        gate = _normalize_gate_label(row.group(1))
        if gate in {"GATE", "STATUS", "---", ""}:
            continue
        status = _extract_status(row.group(2))
        if status:
            observed[gate] = status

    for match in BADGE_RE.finditer(security_body):
        label = _normalize_gate_label(unquote(match.group(1)))
        if label in status_tokens:
            continue
        status = _normalize_status(match.group(2) or "")
        if label and status:
            observed[label] = status
    return observed


def _validate_version(security_body: str, expected_version: str) -> str | None:
    match = VERSION_RE.search(security_body)
    if not match:
        return "Missing release version line: `Release version: **vx.y.z**`."
    found = match.group(1)
    if found != expected_version:
        return f"Version mismatch: SECURITY.md has v{found}, expected v{expected_version}."
    return None


def _validate_virustotal_line(security_body: str, permalink: str) -> str | None:
    if permalink:
        badge_expected = (
            "- VirusTotal permalink: "
            "[![Click Here For VirusTotal Results]"
            "(https://img.shields.io/badge/Click%20Here%20For%20VirusTotal%20Results-0B5E20?style=for-the-badge)]"
            f"({permalink})"
        )
        markdown_expected = f"- VirusTotal permalink: [{permalink}]({permalink})"
        plaintext_expected = f"- VirusTotal permalink: {permalink}"
        if (
            badge_expected not in security_body
            and markdown_expected not in security_body
            and plaintext_expected not in security_body
        ):
            return "VirusTotal permalink line is missing or does not match security-report permalink."
        return None
    fallback = "- VirusTotal permalink: not available in this report."
    if fallback not in security_body:
        return "VirusTotal permalink fallback line missing for empty permalink state."
    return None


def _resolve_repo_path(path_value: str, *, arg_name: str) -> Path:
    # Reject traversal tokens from CLI path input but allow absolute paths for CI temp dirs.
    candidate = Path(path_value).expanduser()
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"{arg_name} must not include parent traversal segments.")
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve()


def main() -> int:
    args = _parse_args()
    try:
        report_path = _resolve_repo_path(args.report, arg_name="--report")
        security_md_path = _resolve_repo_path(args.security_md, arg_name="--security-md")
    except ValueError as exc:
        print(f"Security snapshot sync check failed: {exc}")
        return 1

    if not security_md_path.exists():
        print(f"SECURITY.md not found: {security_md_path}")
        return 1

    report_map = _parse_report_map(report_path)
    security_body = security_md_path.read_text(encoding="utf-8")
    expected = _expected_statuses(report_map)
    observed = _parse_observed_badges(security_body)

    errors: list[str] = []
    for gate, expected_status in expected.items():
        found = _normalize_status(observed.get(gate, ""))
        if not found:
            errors.append(f"Missing badge for gate: {gate}")
            continue
        if found != _normalize_status(expected_status):
            errors.append(
                f"Badge mismatch for {gate}: SECURITY.md={found}, report={expected_status}"
            )

    requested_version = args.version.strip() or report_map.get("app_version", "").strip()
    if not requested_version:
        errors.append("Unable to determine expected release version (missing --version and app_version).")
    else:
        version_error = _validate_version(security_body, requested_version)
        if version_error:
            errors.append(version_error)

    vt_error = _validate_virustotal_line(
        security_body,
        (report_map.get("virustotal_permalink", "") or "").strip(),
    )
    if vt_error:
        errors.append(vt_error)

    if errors:
        print("Security snapshot sync check failed:")
        for item in errors:
            print(f"- {item}")
        return 1

    print(
        "Security snapshot sync check passed: "
        "SECURITY.md badges, version, and VirusTotal permalink match security-report."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
