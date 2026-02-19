import os
import shutil
import subprocess
import sys
import tempfile
import time


def ps_escape(value):
    # Single-quote escaping for inline PowerShell literal strings.
    return str(value).replace("'", "''")


def is_retryable_file_write_error(exc, platform_name=None):
    if isinstance(exc, PermissionError):
        return True
    if not isinstance(exc, OSError):
        return False
    platform_name = str(platform_name or sys.platform)
    if platform_name == "win32":
        return getattr(exc, "winerror", None) in (5, 32, 33)
    return getattr(exc, "errno", None) in (13,)


def write_text_file_atomic(
    path,
    text,
    encoding="utf-8",
    retries=5,
    base_delay=0.08,
    is_retryable_fn=None,
    sleep_fn=None,
):
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
                except Exception:
                    pass
            os.replace(temp_path, target_path)
            return
        except Exception as exc:
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            if attempt + 1 < retries and retryable(exc):
                sleeper(base_delay * (attempt + 1))
                continue
            raise


def commit_file_to_destination_with_retries(
    source_path,
    target_path,
    retries=5,
    base_delay=0.08,
    is_retryable_fn=None,
    sleep_fn=None,
):
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
        except Exception as exc:
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            if attempt + 1 < retries and retryable(exc):
                sleeper(base_delay * (attempt + 1))
                continue
            raise


def start_hidden_process(args, subprocess_module=None):
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
    new_path,
    exe_path,
    current_pid,
    start_hidden_process_fn,
    schedule_root_destroy_fn,
    ps_escape_fn=None,
    restart_notice_ms=1200,
):
    # Staged self-update: wait for current PID, replace EXE, relaunch, then cleanup.
    esc = ps_escape_fn if callable(ps_escape_fn) else ps_escape
    work_dir = tempfile.mkdtemp(prefix="sins_update_run_")
    ps_path = os.path.join(work_dir, "sins_update.ps1")
    vbs_path = os.path.join(work_dir, "sins_update.vbs")
    log_path = os.path.join(work_dir, "sins_update.log")
    fallback_path = exe_path + ".new"
    ps_lines = [
        "$ErrorActionPreference = 'SilentlyContinue'",
        f"$exePath = '{esc(exe_path)}'",
        f"$newPath = '{esc(new_path)}'",
        f"$logPath = '{esc(log_path)}'",
        f"$fallbackPath = '{esc(fallback_path)}'",
        f"$vbsPath = '{esc(vbs_path)}'",
        f"$pidToWait = {int(current_pid)}",
        "function Log($m) {",
        "  Add-Content -Path $logPath -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ' + $m) -Encoding UTF8",
        "}",
        "Log 'Update started.'",
        "Start-Sleep -Milliseconds 600",
        "try { Wait-Process -Id $pidToWait -Timeout 120 } catch {}",
        "$updated = $false",
        "for ($i = 0; $i -lt 16; $i++) {",
        "  try {",
        "    Copy-Item -LiteralPath $newPath -Destination $exePath -Force",
        "    $updated = $true",
        "    break",
        "  } catch {",
        "    Start-Sleep -Milliseconds 500",
        "  }",
        "}",
        "if (-not $updated) {",
        "  Log 'Primary replace failed. Attempting fallback copy.'",
        "  try {",
        "    Copy-Item -LiteralPath $newPath -Destination $fallbackPath -Force",
        "    Start-Process explorer.exe -ArgumentList ('/select,\"' + $fallbackPath + '\"')",
        "  } catch {",
        "    Log ('Fallback copy failed: ' + $_.Exception.Message)",
        "  }",
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
    except Exception:
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
