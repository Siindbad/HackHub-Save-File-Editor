"""Downloaded update signature verification helpers."""
from typing import Any
from core.exceptions import AppRuntimeError


def verify_downloaded_update_signature(owner: Any, path: Any, subprocess_module: Any, json_module: Any, os_module: Any, sys_module: Any) -> Any:
    """Verify downloaded update signature using Authenticode on Windows."""
    if not bool(getattr(owner, "UPDATE_VERIFY_AUTHENTICODE", True)):
        return
    if sys_module.platform != "win32":
        return
    check_path = os_module.path.abspath(path)
    escaped_path = check_path.replace("'", "''")
    ps_script = (
        "$ErrorActionPreference='Stop';"
        f"$sig=Get-AuthenticodeSignature -LiteralPath '{escaped_path}';"
        "[pscustomobject]@{"
        "Status=[string]$sig.Status;"
        "StatusMessage=[string]$sig.StatusMessage;"
        "Subject=[string]$(if($sig.SignerCertificate){$sig.SignerCertificate.Subject}else{''});"
        "Thumbprint=[string]$(if($sig.SignerCertificate){$sig.SignerCertificate.Thumbprint}else{''})"
        "} | ConvertTo-Json -Compress"
    )
    strict = bool(getattr(owner, "UPDATE_REQUIRE_AUTHENTICODE", False))
    allowed_subjects = tuple(
        str(item).strip().casefold()
        for item in (getattr(owner, "UPDATE_AUTHENTICODE_ALLOWED_SUBJECTS", ()) or ())
        if str(item).strip()
    )
    # Prefer absolute system PowerShell path to avoid PATH-hijack risk on updater signature checks.
    ps_exe = os_module.path.join(
        os_module.environ.get("WINDIR", r"C:\Windows"),
        "System32",
        "WindowsPowerShell",
        "v1.0",
        "powershell.exe",
    )
    if not os_module.path.isfile(ps_exe):
        ps_exe = "powershell.exe"
    try:
        # Trusted local signature probe using fixed executable + static args.
        probe = subprocess_module.run(  # nosec B603
            [ps_exe, "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if probe.returncode != 0:
            raise AppRuntimeError((probe.stderr or probe.stdout or "").strip() or "signature check failed")
        payload = json_module.loads((probe.stdout or "").strip() or "{}")
        status = str(payload.get("Status", "")).strip()
        subject = str(payload.get("Subject", "")).strip()
        status_msg = str(payload.get("StatusMessage", "")).strip()
    except (subprocess_module.SubprocessError, OSError, RuntimeError, ValueError, json_module.JSONDecodeError) as exc:
        if strict:
            raise AppRuntimeError(f"Downloaded update signature check failed: {exc}") from exc
        return

    is_valid = status.lower() == "valid"
    if is_valid and allowed_subjects:
        subj_norm = subject.casefold()
        is_valid = any(token in subj_norm for token in allowed_subjects)
        if strict and not is_valid:
            raise AppRuntimeError("Downloaded update signature subject is not in allow-list.")

    if strict and not is_valid:
        detail = status_msg or status or "invalid signature"
        raise AppRuntimeError(f"Downloaded update Authenticode signature check failed: {detail}")
