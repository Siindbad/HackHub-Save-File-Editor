import os
import shutil
import subprocess
import sys
import tempfile
import time
import ctypes
import json
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def enable_windows_dpi_awareness() -> Any:
    """Enable best-available DPI awareness before Tk root creation."""
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.windll.user32
    except (AttributeError, OSError):
        return False

    try:
        if bool(user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))):
            return True
    except (AttributeError, OSError, ValueError):
        pass
    try:
        shcore = ctypes.windll.shcore
        if int(shcore.SetProcessDpiAwareness(2)) == 0:
            return True
    except (AttributeError, OSError, ValueError):
        pass
    try:
        if bool(user32.SetProcessDPIAware()):
            return True
    except (AttributeError, OSError, ValueError):
        pass
    return False


def ps_escape(value: Any) -> Any:
    # Single-quote escaping for inline PowerShell literal strings.
    return str(value).replace("'", "''")


def is_retryable_file_write_error(exc: Any, platform_name: Any=None) -> Any:
    if isinstance(exc, PermissionError):
        return True
    if not isinstance(exc, OSError):
        return False
    platform_name = str(platform_name or sys.platform)
    if platform_name == "win32":
        return getattr(exc, "winerror", None) in (5, 32, 33)
    return getattr(exc, "errno", None) in (13,)


def write_text_file_atomic(
    path: Any,
    text: Any,
    encoding: Any="utf-8",
    retries: Any=5,
    base_delay: Any=0.08,
    is_retryable_fn: Any=None,
    sleep_fn: Any=None,
) -> Any:
    # Write via temp file + os.replace so readers never see partial content.
    target_path = os.path.abspath(path)
    target_dir = os.path.dirname(target_path) or os.getcwd()
    os.makedirs(target_dir, exist_ok=True)
    retries = max(1, int(retries))
    retryable = is_retryable_fn if callable(is_retryable_fn) else is_retryable_file_write_error
    sleeper = sleep_fn if callable(sleep_fn) else time.sleep
    for attempt in range(retries):
        temp_path = None
        try:
            fd, temp_path = tempfile.mkstemp(
                prefix=".sins_tmp_",
                suffix=".tmp",
                dir=target_dir,
                text=False,
            )
            with os.fdopen(fd, "w", encoding=encoding, newline="") as fh:
                fh.write(text)
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except EXPECTED_ERRORS as exc:
                    _LOG.debug('expected_error', exc_info=exc)
                    pass
            os.replace(temp_path, target_path)
            return
        except EXPECTED_ERRORS as exc:
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except EXPECTED_ERRORS as exc:
                _LOG.debug('expected_error', exc_info=exc)
                pass
            if attempt + 1 < retries and retryable(exc):
                sleeper(base_delay * (attempt + 1))
                continue
            raise


def read_json_file(path: Any, encoding: Any="utf-8") -> Any:
    """Read and parse JSON from disk using a stable UTF-8 text contract."""
    with open(path, "r", encoding=encoding) as handle:
        return json.load(handle)


def commit_file_to_destination_with_retries(
    source_path: Any,
    target_path: Any,
    retries: Any=5,
    base_delay: Any=0.08,
    is_retryable_fn: Any=None,
    sleep_fn: Any=None,
) -> Any:
    # Copy update payload with retry-on-lock semantics common on Windows.
    source_path = os.path.abspath(source_path)
    target_path = os.path.abspath(target_path)
    target_dir = os.path.dirname(target_path) or os.getcwd()
    os.makedirs(target_dir, exist_ok=True)
    retries = max(1, int(retries))
    retryable = is_retryable_fn if callable(is_retryable_fn) else is_retryable_file_write_error
    sleeper = sleep_fn if callable(sleep_fn) else time.sleep
    for attempt in range(retries):
        temp_path = None
        try:
            fd, temp_path = tempfile.mkstemp(
                prefix=".sins_tmp_",
                suffix=".tmp",
                dir=target_dir,
                text=False,
            )
            os.close(fd)
            shutil.copyfile(source_path, temp_path)
            os.replace(temp_path, target_path)
            return
        except EXPECTED_ERRORS as exc:
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except EXPECTED_ERRORS as exc:
                _LOG.debug('expected_error', exc_info=exc)
                pass
            if attempt + 1 < retries and retryable(exc):
                sleeper(base_delay * (attempt + 1))
                continue
            raise


def start_hidden_process(args: Any, subprocess_module: Any=None) -> Any:
    # Launch detached/no-window worker so updater flow stays silent for users.
    subproc = subprocess_module if subprocess_module is not None else subprocess
    startup = None
    if hasattr(subproc, "STARTUPINFO"):
        startup = subproc.STARTUPINFO()
        startup.dwFlags |= subproc.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
    flags = 0
    flags |= getattr(subproc, "CREATE_NEW_PROCESS_GROUP", 0)
    flags |= getattr(subproc, "DETACHED_PROCESS", 0)
    flags |= getattr(subproc, "CREATE_NO_WINDOW", 0)
    subproc.Popen(
        args,
        startupinfo=startup,
        creationflags=flags,
        close_fds=True,
    )


def install_update(
    new_path: Any,
    exe_path: Any,
    current_pid: Any,
    asset_name: Any,
    start_hidden_process_fn: Any,
    schedule_root_destroy_fn: Any,
    ps_escape_fn: Any=None,
    restart_notice_ms: Any=1200,
) -> Any:
    # Staged self-update: wait for current PID, apply payload (EXE or ZIP), relaunch, then cleanup.
    esc = ps_escape_fn if callable(ps_escape_fn) else ps_escape
    work_dir = tempfile.mkdtemp(prefix="sins_update_run_")
    ps_path = os.path.join(work_dir, "sins_update.ps1")
    vbs_path = os.path.join(work_dir, "sins_update.vbs")
    log_path = os.path.join(work_dir, "sins_update.log")
    fallback_path = exe_path + ".new"
    asset_name_text = str(asset_name or "").strip().lower()
    use_zip_payload = asset_name_text.endswith(".zip")
    app_dir = os.path.dirname(exe_path) or os.getcwd()
    ps_lines = [
        "param([switch]$Elevated)",
        "$ErrorActionPreference = 'SilentlyContinue'",
        f"$exePath = '{esc(exe_path)}'",
        f"$newPath = '{esc(new_path)}'",
        f"$appDir = '{esc(app_dir)}'",
        f"$logPath = '{esc(log_path)}'",
        f"$fallbackPath = '{esc(fallback_path)}'",
        f"$vbsPath = '{esc(vbs_path)}'",
        f"$pidToWait = {int(current_pid)}",
        ("$useZipPayload = $true" if use_zip_payload else "$useZipPayload = $false"),
        "function Log($m) {",
        "  Add-Content -Path $logPath -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ' + $m) -Encoding UTF8",
        "}",
        "function Test-AppDirWritable($dirPath) {",
        "  try {",
        "    $null = New-Item -ItemType Directory -Path $dirPath -Force",
        "    $probe = Join-Path $dirPath ('.sins_update_write_' + [Guid]::NewGuid().ToString('N') + '.tmp')",
        "    Set-Content -LiteralPath $probe -Value 'ok' -Encoding ASCII -Force",
        "    Remove-Item -LiteralPath $probe -Force",
        "    return $true",
        "  } catch {",
        "    return $false",
        "  }",
        "}",
        "function Get-IsAdminToken {",
        "  try {",
        "    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()",
        "    $principal = New-Object Security.Principal.WindowsPrincipal($identity)",
        "    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)",
        "  } catch {",
        "    return $false",
        "  }",
        "}",
        "function Test-IsProtectedInstallPath($pathValue) {",
        "  $pathText = [string]$pathValue",
        "  if ([string]::IsNullOrWhiteSpace($pathText)) {",
        "    return $false",
        "  }",
        "  $roots = @()",
        "  if ($env:ProgramFiles) { $roots += $env:ProgramFiles }",
        "  if (${env:ProgramFiles(x86)}) { $roots += ${env:ProgramFiles(x86)} }",
        "  foreach ($root in $roots) {",
        "    try {",
        "      $fullRoot = [System.IO.Path]::GetFullPath($root).TrimEnd('\\') + '\\'",
        "      $fullPath = [System.IO.Path]::GetFullPath($pathText).TrimEnd('\\') + '\\'",
        "      if ($fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) {",
        "        return $true",
        "      }",
        "    } catch {}",
        "  }",
        "  return $false",
        "}",
        "Log 'Update started.'",
        "Start-Sleep -Milliseconds 600",
        "try { Wait-Process -Id $pidToWait -Timeout 120 } catch {}",
        "$isAdminToken = Get-IsAdminToken",
        "$isProtectedInstall = Test-IsProtectedInstallPath $appDir",
        "$isWritable = Test-AppDirWritable $appDir",
        "if ($isProtectedInstall -and -not $isAdminToken) {",
        "  Log 'Install path is under Program Files and updater is not elevated.'",
        "  $isWritable = $false",
        "}",
        "if (-not $isWritable) {",
        "  if (-not $Elevated) {",
        "    Log 'Install directory requires elevation. Relaunching updater as administrator.'",
        "    try {",
        "      Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', $PSCommandPath, '-Elevated') -Verb RunAs -WindowStyle Hidden",
        "      exit 0",
        "    } catch {",
        "      Log ('Elevation request failed: ' + $_.Exception.Message)",
        "      exit 1",
        "    }",
        "  }",
        "  if (-not (Test-AppDirWritable $appDir)) {",
        "    Log 'Install directory is still not writable after elevation.'",
        "    exit 1",
        "  }",
        "}",
        "$updated = $false",
        "if ($useZipPayload) {",
        "  Log 'Applying ZIP update payload.'",
        "  $extractRoot = Join-Path (Split-Path -Parent $newPath) 'extract'",
        "  try {",
        "    if (Test-Path $extractRoot) { Remove-Item -LiteralPath $extractRoot -Recurse -Force }",
        "  } catch {}",
        "  try {",
        "    Expand-Archive -LiteralPath $newPath -DestinationPath $extractRoot -Force",
        "  } catch {",
        "    Log ('ZIP extract failed: ' + $_.Exception.Message)",
        "    exit 1",
        "  }",
        "  $sourceExe = Get-ChildItem -Path $extractRoot -Recurse -File -Filter 'sins_editor.exe' | Select-Object -First 1",
        "  if (-not $sourceExe) {",
        "    Log 'ZIP payload missing sins_editor.exe.'",
        "    exit 1",
        "  }",
        "  $sourceDir = Split-Path -Parent $sourceExe.FullName",
        "  $targetExe = Join-Path $appDir 'sins_editor.exe'",
        "  for ($i = 0; $i -lt 16; $i++) {",
        "    try {",
        "      $null = New-Item -ItemType Directory -Path $appDir -Force",
        "      & robocopy.exe $sourceDir $appDir * /E /R:2 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null",
        "      $rc = $LASTEXITCODE",
        "      try {",
        "        Copy-Item -LiteralPath $sourceExe.FullName -Destination $targetExe -Force",
        "      } catch {",
        "        Log ('Direct EXE copy attempt failed: ' + $_.Exception.Message)",
        "      }",
        "      if ($rc -le 7) {",
        "        $sourceHash = $null",
        "        $targetHash = $null",
        "        try { $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceExe.FullName).Hash } catch {}",
        "        try { $targetHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $targetExe).Hash } catch {}",
        "        if ($sourceHash -and $targetHash -and ($sourceHash -eq $targetHash)) {",
        "          $updated = $true",
        "          break",
        "        }",
        "        Log 'robocopy completed but target EXE hash does not match source yet.'",
      "      }",
        "      Log ('robocopy exit code: ' + [string]$rc)",
        "    } catch {",
        "      Log ('ZIP apply attempt failed: ' + $_.Exception.Message)",
        "    }",
        "    Start-Sleep -Milliseconds 500",
        "  }",
        "} else {",
        "  Log 'Applying EXE update payload.'",
        "  for ($i = 0; $i -lt 16; $i++) {",
        "    try {",
        "      Copy-Item -LiteralPath $newPath -Destination $exePath -Force",
        "      $updated = $true",
        "      break",
        "    } catch {",
        "      Start-Sleep -Milliseconds 500",
        "    }",
        "  }",
        "  if (-not $updated) {",
        "    Log 'Primary replace failed. Attempting fallback copy.'",
        "    try {",
        "      Copy-Item -LiteralPath $newPath -Destination $fallbackPath -Force",
        "      Start-Process explorer.exe -ArgumentList ('/select,\"' + $fallbackPath + '\"')",
        "    } catch {",
        "      Log ('Fallback copy failed: ' + $_.Exception.Message)",
        "    }",
        "  }",
        "}",
        "if (-not $updated) {",
        "  Log 'Update apply failed after retries.'",
        "  exit 1",
        "}",
        "Log 'Update applied.'",
        "try {",
        "  $env:PYINSTALLER_RESET_ENVIRONMENT = '1'",
        "  Log 'Relaunching updated app with clean PyInstaller environment.'",
        "  Start-Process -FilePath $exePath -WorkingDirectory (Split-Path -Parent $exePath)",
        "} catch {",
        "  Log ('Failed to restart updated app: ' + $_.Exception.Message)",
        "} finally {",
        "  Remove-Item Env:PYINSTALLER_RESET_ENVIRONMENT -ErrorAction SilentlyContinue",
        "}",
        "Start-Sleep -Milliseconds 300",
        "try { Remove-Item -LiteralPath $newPath -Force } catch {}",
        "try { Remove-Item -LiteralPath $vbsPath -Force } catch {}",
        "try { Remove-Item -LiteralPath $PSCommandPath -Force } catch {}",
    ]
    with open(ps_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(ps_lines))

    ps_cmd = (
        'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass '
        '-WindowStyle Hidden -File '
        f'"{ps_path}"'
    )
    escaped_ps_cmd = ps_cmd.replace('"', '""')
    vbs_lines = [
        'Set WshShell = CreateObject("WScript.Shell")',
        f'WshShell.Run "{escaped_ps_cmd}", 0, False',
    ]
    with open(vbs_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(vbs_lines))

    try:
        start_hidden_process_fn(["wscript.exe", "//nologo", vbs_path])
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        start_hidden_process_fn(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-WindowStyle",
                "Hidden",
                "-File",
                ps_path,
            ]
        )
    # Leave a short window so users can read "restarting" update messaging.
    schedule_root_destroy_fn(max(0, int(restart_notice_ms)))
