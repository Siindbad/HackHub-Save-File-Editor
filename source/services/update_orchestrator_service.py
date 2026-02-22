"""Update orchestration service.

Coordinates update UI demo and real update flow while owner supplies
runtime dependencies and editor callbacks.
"""

import sys
import threading
import time
from tkinter import messagebox as _tk_messagebox

def run_update_ui_demo(owner, auto=False, sleep_fn=time.sleep):
    try:
        owner._set_status("Preparing update...")
        owner._ui_call(
            owner._show_update_overlay,
            "Preparing update...\nThe app will restart automatically.",
            wait=True,
        )
        owner._ui_call(
            owner._update_update_overlay,
            "Preparing update...\nThe app will restart automatically.",
            stage="preparing",
            wait=True,
        )
        sleep_fn(0.45)

        owner._set_status("Downloading update...")
        owner._ui_call(
            owner._update_update_overlay,
            "Downloading update...\nThis may take a moment.",
            stage="downloading",
            wait=True,
        )
        for _ in range(8):
            owner._ui_call(
                owner._update_update_overlay,
                stage="downloading",
                pulse=True,
                wait=True,
            )
            sleep_fn(0.12)

        owner._set_status("Installing update...")
        owner._ui_call(
            owner._update_update_overlay,
            "Installing update...\nThe app will restart automatically.",
            stage="installing",
            wait=True,
        )
        install_hold_ms = max(0, int(getattr(owner, "_update_install_stage_hold_ms", 3000) or 3000))
        sleep_fn(float(install_hold_ms) / 1000.0)

        owner._set_status("Update installed. Restarting app...")
        owner._ui_call(
            owner._update_update_overlay,
            "Update installed.\nRestarting app...",
            stage="restarting",
            wait=True,
        )
        restart_hold_ms = max(0, int(getattr(owner, "_update_restart_notice_ms", 4200) or 4200))
        sleep_fn(float(restart_hold_ms) / 1000.0)

        if not auto:
            owner._set_status("Update UI demo complete.")
            owner._ui_call(
                owner._show_themed_update_info,
                "Update",
                "Update UI demo complete.\nNo files were downloaded or installed.",
            )
    finally:
        owner._ui_call(owner._close_update_overlay)
        if auto:
            owner._set_status("")


def check_for_updates(owner, auto=False, messagebox=None):
    if messagebox is None:
        messagebox = _tk_messagebox
    if owner._update_ui_demo_enabled():
        threading.Thread(target=lambda: owner._run_update_ui_demo(auto=auto), daemon=True).start()
        return
    if not getattr(sys, "frozen", False):
        owner._set_status("You already have the latest version installed.")
        if not auto:
            owner._show_themed_update_info(
                "Update",
                "You already have the latest version installed.",
                True,
            )
        return
    if owner.GITHUB_OWNER == "YOUR_GITHUB_USERNAME" or owner.GITHUB_REPO == "YOUR_REPO_NAME":
        if not auto:
            owner._show_themed_update_info(
                "Update",
                "Set GITHUB_OWNER and GITHUB_REPO in the source to enable updates.",
            )
        return

    def worker():
        install_started = False
        try:
            owner._set_status("Checking for updates...")
            latest_version = owner._fetch_dist_version()
            if not latest_version:
                owner._set_status("")
                if not auto:
                    owner._ui_call(owner._show_themed_update_info, "Update", "No release info available.")
                return

            latest_version = owner._release_version(latest_version)
            current_version = owner._release_version(owner.APP_VERSION)
            if latest_version and current_version and latest_version < current_version:
                owner._set_status("")
                if not auto:
                    owner._ui_call(
                        owner._show_themed_update_info,
                        "Update",
                        "Release version is older than this build.\n"
                        f"Release: v{owner._format_version(latest_version)}\n"
                        f"Current: v{owner._format_version(current_version)}\n"
                        "Check dist/version.txt.",
                    )
                return
            if latest_version == current_version:
                owner._set_status("Up to date.")
                if not auto:
                    owner._ui_call(
                        owner._show_themed_update_info,
                        "Update",
                        "You're already on the latest version.",
                        True,
                    )
                return

            prompt = (
                f"Update v{owner._format_version(latest_version)} is available.\n"
                "Do you want to install it now?\n\n"
                "The app will close and restart automatically."
            )
            if not owner._ui_call(
                owner._ask_themed_update_confirm,
                "Update",
                prompt,
                True,
                wait=True,
                default=False,
            ):
                owner._set_status("")
                return

            owner._ui_call(
                owner._show_update_overlay,
                "Preparing update...\nThe app will restart automatically.",
                wait=True,
            )
            owner._ui_call(
                owner._update_update_overlay,
                "Preparing update...\nThe app will restart automatically.",
                stage="preparing",
                wait=True,
            )
            owner._set_status("Downloading update...")
            owner._ui_call(
                owner._update_update_overlay,
                "Downloading update...\nThis may take a moment.",
                stage="downloading",
                wait=True,
            )
            new_path = owner._download_dist_asset()
            owner._ui_call(
                owner._update_update_overlay,
                "Installing update...\nThe app will restart automatically.",
                stage="installing",
                wait=True,
            )
            owner._set_status("Installing update...")
            install_hold_ms = max(0, int(getattr(owner, "_update_install_stage_hold_ms", 3000) or 3000))
            if install_hold_ms > 0:
                time.sleep(float(install_hold_ms) / 1000.0)
            install_started = True
            owner._install_update(new_path)
            owner._set_status("Update installed. Restarting app...")
            owner._ui_call(
                owner._update_update_overlay,
                "Update installed.\nRestarting app...",
                stage="restarting",
                wait=True,
            )
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError) as exc:
            owner._set_status("")
            pretty_error = owner._format_update_error(exc)
            owner._log_update_failure(exc, auto=auto, pretty_error=pretty_error)
            if not auto:
                owner._ui_call(messagebox.showerror, "Update", pretty_error)
                owner._ui_call(owner._offer_manual_update_fallback, pretty_error, wait=True, default=False)
        finally:
            if auto and not install_started:
                owner._set_status("")
            # Keep overlay visible on successful install path so restart messaging remains visible
            # until the app closes and relaunches.
            if not install_started:
                owner._ui_call(owner._close_update_overlay)

    threading.Thread(target=worker, daemon=True).start()

