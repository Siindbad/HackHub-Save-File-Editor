"""Bug report dialog UI service.

Keeps the large Tk dialog builder out of `sins_editor.py` while preserving
runtime behavior through owner callbacks.
"""

import os
import threading


# UI-only extraction: owner provides methods/state; this module stays stateless.
def open_bug_report_dialog(
    owner,
    tk,
    filedialog,
    messagebox,
    summary_prefill="",
    details_prefill="",
    include_diag_default=True,
    crash_tail="",
):
    existing = getattr(owner, "_bug_report_dialog", None)
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.deiconify()
                existing.lift()
                existing.focus_force()
                return
        except Exception:
            pass
    theme = getattr(owner, "_theme", {})
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    chip_colors = owner._bug_chip_palette(variant)

    dlg = tk.Toplevel(owner.root)
    try:
        dlg.withdraw()
    except Exception:
        pass
    owner._bug_report_dialog = dlg
    dlg.title("Submit Bug Report")
    use_custom_chrome = bool(getattr(owner, "BUG_REPORT_USE_CUSTOM_CHROME", True))
    if not use_custom_chrome:
        dlg.transient(owner.root)
    dlg.configure(bg=theme.get("panel", "#161b24"))
    owner._apply_centered_toplevel_geometry(
        dlg,
        width_px=684,
        height_px=576,
        anchor_window=owner.root,
        min_width=612,
        min_height=504,
    )

    card = tk.Frame(
        dlg,
        bg=theme.get("panel", "#161b24"),
        bd=0,
        highlightthickness=1,
        highlightbackground=chip_colors["border"],
        highlightcolor=chip_colors["border"],
    )
    card.pack(fill="both", expand=True, padx=0, pady=0)
    owner._bug_report_card_frame = card

    header_bg = theme.get("title_bar_bg", chip_colors["bg"])
    header_fg = theme.get("title_bar_fg", theme.get("fg", "#e6e6e6"))
    header_border = theme.get("title_bar_border", chip_colors["border"])
    header = tk.Frame(
        card,
        bg=header_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=header_border,
        highlightcolor=header_border,
    )
    header.pack(fill="x", padx=12, pady=(10, 8))
    header_icon_photo = owner._load_bug_report_chip_icon(max_size=18, tint=header_fg)
    owner._bug_report_header_icon_photo = header_icon_photo
    icon = tk.Label(
        header,
        text="",
        image=header_icon_photo if header_icon_photo is not None else "",
        bg=header_bg,
        fg=header_fg,
        bd=0,
        highlightthickness=0,
    )
    icon.pack(side="left", padx=(8, 7), pady=4)
    title = tk.Label(
        header,
        text="SUBMIT BUG REPORT",
        bg=header_bg,
        fg=header_fg,
        font=(owner._preferred_mono_family(), 12, "bold"),
        anchor="w",
    )
    title.pack(side="left", pady=2)
    close_badge = tk.Label(
        header,
        text="X",
        bg=header_bg,
        fg=header_fg,
        font=(owner._preferred_mono_family(), 11, "bold"),
        cursor="hand2",
        padx=10,
        pady=4,
    )
    close_badge.pack(side="right")
    owner._bug_report_header_frame = header
    owner._bug_report_header_icon = icon
    owner._bug_report_header_title = title
    owner._bug_report_close_badge = close_badge

    form_intro = tk.Frame(card, bg=theme.get("panel", "#161b24"), bd=0, highlightthickness=0)
    form_intro.pack(fill="x", padx=12, pady=(0, 8))
    tk.Label(
        form_intro,
        text="DISCORD (OPTIONAL)",
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("fg", "#e6e6e6"),
        font=(owner._preferred_mono_family(), 10, "bold"),
        anchor="w",
    ).pack(fill="x")
    discord_var = tk.StringVar(value="")
    discord_entry = tk.Entry(
        form_intro,
        textvariable=discord_var,
        bg=theme.get("bg", "#0f131a"),
        fg=theme.get("fg", "#e6e6e6"),
        insertbackground=theme.get("fg", "#e6e6e6"),
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=chip_colors["border"],
        highlightcolor=chip_colors["border"],
        font=(owner._preferred_mono_family(), 10),
    )
    discord_entry.pack(fill="x", pady=(4, 0), ipady=5)

    screenshot_var = tk.StringVar(value="")
    screenshot_block = tk.Frame(form_intro, bg=theme.get("panel", "#161b24"), bd=0, highlightthickness=0)
    screenshot_block.pack(fill="x", pady=(8, 0))
    tk.Label(
        screenshot_block,
        text="SCREENSHOT (OPTIONAL)",
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("fg", "#e6e6e6"),
        font=(owner._preferred_mono_family(), 10, "bold"),
        anchor="w",
    ).pack(fill="x")
    screenshot_row = tk.Frame(screenshot_block, bg=theme.get("panel", "#161b24"), bd=0, highlightthickness=0)
    screenshot_row.pack(fill="x", pady=(4, 0))
    screenshot_entry = tk.Entry(
        screenshot_row,
        textvariable=screenshot_var,
        state="readonly",
        readonlybackground=theme.get("bg", "#0f131a"),
        fg=theme.get("credit_label_fg", "#b5cade"),
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=chip_colors["border"],
        highlightcolor=chip_colors["border"],
        font=(owner._preferred_mono_family(), 9),
    )
    screenshot_entry.pack(side="left", fill="x", expand=True, ipady=5)

    def _pick_screenshot_file():
        file_path = filedialog.askopenfilename(
            title="Select Screenshot",
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg;*.webp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg;*.jpeg"),
                ("WebP", "*.webp"),
            ],
        )
        if not file_path:
            return
        try:
            validated = owner._validate_bug_screenshot_file(file_path)
        except Exception as exc:
            messagebox.showwarning("Bug Report", str(exc))
            return
        screenshot_var.set(validated)

    def _clear_screenshot_file():
        screenshot_var.set("")

    pick_wrap = tk.Frame(
        screenshot_row,
        bg=chip_colors["border"],
        bd=0,
        highlightthickness=0,
    )
    pick_wrap.pack(side="left", padx=(6, 0))
    pick_btn = tk.Button(
        pick_wrap,
        text="Browse",
        bg=theme.get("bg", "#0f131a"),
        fg=theme.get("fg", "#e6e6e6"),
        activebackground=theme.get("accent", "#202737"),
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 9, "bold"),
        padx=10,
        pady=4,
        command=_pick_screenshot_file,
    )
    pick_btn.pack(side="left", padx=1, pady=1)
    clear_wrap = tk.Frame(
        screenshot_row,
        bg=chip_colors["border"],
        bd=0,
        highlightthickness=0,
    )
    clear_wrap.pack(side="left", padx=(6, 0))
    clear_btn = tk.Button(
        clear_wrap,
        text="Clear",
        bg=theme.get("bg", "#0f131a"),
        fg=theme.get("fg", "#e6e6e6"),
        activebackground=theme.get("accent", "#202737"),
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 9, "bold"),
        padx=10,
        pady=4,
        command=_clear_screenshot_file,
    )
    clear_btn.pack(side="left", padx=1, pady=1)

    form = tk.Frame(card, bg=theme.get("panel", "#161b24"), bd=0, highlightthickness=0)
    form.pack(fill="both", expand=True, padx=12, pady=(2, 8))

    tk.Label(
        form,
        text="Title",
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("fg", "#e6e6e6"),
        font=(owner._preferred_mono_family(), 10, "bold"),
        anchor="w",
    ).pack(fill="x")
    summary_var = tk.StringVar(value=str(summary_prefill or ""))
    summary_entry = tk.Entry(
        form,
        textvariable=summary_var,
        bg=theme.get("bg", "#0f131a"),
        fg=theme.get("fg", "#e6e6e6"),
        insertbackground=theme.get("fg", "#e6e6e6"),
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=chip_colors["border"],
        highlightcolor=chip_colors["border"],
        font=(owner._preferred_mono_family(), 10),
    )
    summary_entry.pack(fill="x", pady=(4, 10), ipady=5)

    tk.Label(
        form,
        text="Details",
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("fg", "#e6e6e6"),
        font=(owner._preferred_mono_family(), 10, "bold"),
        anchor="w",
    ).pack(fill="x")
    details_text = tk.Text(
        form,
        wrap="word",
        height=9,
        bg=theme.get("bg", "#0f131a"),
        fg=theme.get("fg", "#e6e6e6"),
        insertbackground=theme.get("fg", "#e6e6e6"),
        selectbackground=theme.get("select_bg", "#2f3a4d"),
        selectforeground=theme.get("select_fg", "#ffffff"),
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=chip_colors["border"],
        highlightcolor=chip_colors["border"],
        font=(owner._preferred_mono_family(), 10),
    )
    details_text.pack(fill="both", expand=True, pady=(4, 8))
    if str(details_prefill or "").strip():
        try:
            details_text.insert("1.0", str(details_prefill))
        except Exception:
            pass

    include_diag_var = tk.BooleanVar(value=bool(include_diag_default))
    diag_block = tk.Frame(form, bg=theme.get("panel", "#161b24"), bd=0, highlightthickness=0)
    diag_block.pack(fill="x", pady=(0, 0))

    include_diag = tk.Checkbutton(
        diag_block,
        text="Include diagnostics tail from local app log",
        variable=include_diag_var,
        onvalue=True,
        offvalue=False,
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("fg", "#e6e6e6"),
        activebackground=theme.get("panel", "#161b24"),
        activeforeground=theme.get("fg", "#e6e6e6"),
        selectcolor=theme.get("panel", "#161b24"),
        highlightthickness=0,
        bd=0,
        font=(owner._preferred_mono_family(), 9),
        anchor="w",
    )
    include_diag.pack(fill="x")
    tk.Label(
        diag_block,
        text=(
            "Privacy Notice: Submitted reports may include your notes, runtime context,\n"
            "optional diagnostics/crash logs, and optional Discord contact info."
        ),
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("credit_label_fg", "#8ca6bb"),
        font=(owner._preferred_mono_family(), 10),
        justify="left",
        anchor="w",
    ).pack(fill="x", padx=(0, 0), pady=(2, 0))

    status_var = tk.StringVar(value="")
    status_label = tk.Label(
        form,
        textvariable=status_var,
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("credit_label_fg", "#b5cade"),
        font=(owner._preferred_mono_family(), 9),
        anchor="w",
    )
    status_label.pack(fill="x", pady=(8, 0))

    controls = tk.Frame(card, bg=theme.get("panel", "#161b24"), bd=0, highlightthickness=0)
    controls.pack(fill="x", padx=12, pady=(0, 12))

    submit_wrap = tk.Frame(
        controls,
        bg=chip_colors["border"],
        bd=0,
        highlightthickness=0,
    )
    submit_wrap.pack(side="right")
    submit_btn = tk.Button(
        submit_wrap,
        text="Submit Report",
        bg=chip_colors["bg"],
        fg=chip_colors["fg"],
        activebackground=chip_colors["active_bg"],
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 10, "bold"),
        padx=14,
        pady=5,
    )
    submit_btn.pack(side="right", padx=1, pady=1)

    cancel_wrap = tk.Frame(
        controls,
        bg=chip_colors["border"],
        bd=0,
        highlightthickness=0,
    )
    cancel_wrap.pack(side="right", padx=(0, 8))
    cancel_btn = tk.Button(
        cancel_wrap,
        text="Cancel",
        bg=theme.get("bg", "#0f131a"),
        fg=theme.get("fg", "#e6e6e6"),
        activebackground=theme.get("accent", "#202737"),
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 10, "bold"),
        padx=14,
        pady=5,
        command=owner._close_bug_report_dialog,
    )
    cancel_btn.pack(side="right", padx=1, pady=1)

    def submit_action():
        cooldown_remaining = owner._bug_report_submit_cooldown_remaining()
        if cooldown_remaining > 0:
            unit = "second" if cooldown_remaining == 1 else "seconds"
            wait_msg = f"Please wait {cooldown_remaining} {unit} before sending another report."
            owner._set_status(wait_msg)
            status_var.set(wait_msg)
            messagebox.showwarning("Bug Report", wait_msg)
            return
        summary = summary_var.get().strip()
        details = details_text.get("1.0", "end-1c").strip()
        if not summary:
            messagebox.showwarning("Bug Report", "Enter a title before submitting.")
            return
        screenshot_path = screenshot_var.get().strip()
        screenshot_file_name = os.path.basename(screenshot_path) if screenshot_path else ""
        issue_title = f"[Bug] {summary}"[:120]
        owner._mark_bug_report_submit_now()

        def worker():
            try:
                owner._ui_call(status_var.set, "Submitting issue...", wait=False)
                owner._ui_call(submit_btn.configure, state="disabled", wait=False)
                screenshot_url = ""
                screenshot_note = ""
                selected_name = screenshot_file_name
                if screenshot_path:
                    try:
                        owner._validate_bug_screenshot_file(screenshot_path)
                        if owner._has_bug_report_token():
                            owner._ui_call(status_var.set, "Uploading screenshot...", wait=False)
                            uploaded = owner._upload_bug_screenshot(screenshot_path, summary=summary)
                            screenshot_url = str(uploaded.get("download_url", "")).strip()
                            selected_name = str(uploaded.get("filename", "")).strip() or selected_name
                        else:
                            screenshot_note = (
                                "Screenshot selected locally, but token is unavailable. "
                                "Attach image manually in browser issue form."
                            )
                    except Exception as upload_exc:
                        screenshot_note = str(upload_exc)
                body = owner._build_bug_report_markdown(
                    summary=summary,
                    details=details,
                    include_diag=bool(include_diag_var.get()),
                    discord_contact=(
                        discord_var.get().strip()
                    ),
                    crash_tail=str(crash_tail or ""),
                    screenshot_url=screenshot_url,
                    screenshot_filename=selected_name,
                    screenshot_note=screenshot_note,
                )
                owner._ui_call(status_var.set, "Submitting issue...", wait=False)
                owner._submit_bug_report_issue(issue_title, body)
                owner._set_status("Bug report submitted.")
                owner._ui_call(status_var.set, "Submitted successfully.", wait=False)
                # Release modal grab and close dialog first.
                owner._ui_call(owner._close_bug_report_dialog, wait=True)
                owner._ui_call(
                    owner._show_bug_submit_splash,
                    "BUG REPORT SUBMITTED",
                    wait=False,
                )
            except Exception as exc:
                owner._set_status("")
                owner._ui_call(status_var.set, "Submit failed.", wait=False)
                owner._ui_call(messagebox.showerror, "Bug Report", str(exc), wait=False)
            finally:
                owner._ui_call(submit_btn.configure, state="normal", wait=False)

        threading.Thread(target=worker, daemon=True).start()

    submit_btn.configure(command=submit_action)
    if use_custom_chrome:
        chrome_ok = owner._activate_bug_report_custom_chrome(
            dlg,
            header=header,
            drag_widgets=(header, icon, title),
            close_widget=close_badge,
        )
        if not chrome_ok:
            owner._set_window_icon_for(dlg)
            owner._apply_windows_titlebar_theme(dlg)
            try:
                close_badge.pack_forget()
            except Exception:
                pass
    else:
        owner._set_window_icon_for(dlg)
        owner._apply_windows_titlebar_theme(dlg)
        try:
            close_badge.pack_forget()
        except Exception:
            pass
    try:
        dlg.deiconify()
        dlg.lift()
        dlg.focus_force()
    except Exception:
        pass
    owner._arm_bug_report_follow_root(dlg)
    dlg.bind("<Escape>", lambda _e: owner._close_bug_report_dialog())
    dlg.protocol("WM_DELETE_WINDOW", owner._close_bug_report_dialog)
    summary_entry.focus_set()
    owner._start_bug_report_header_pulse()

    def clear_ref(_evt=None):
        owner._stop_bug_report_header_pulse()
        owner._bug_report_card_frame = None
        owner._bug_report_header_frame = None
        owner._bug_report_header_icon = None
        owner._bug_report_header_icon_photo = None
        owner._bug_report_header_title = None
        owner._bug_report_close_badge = None
        owner._bug_report_dialog = None
        owner._bug_report_follow_root = False
        owner._bug_report_is_dragging = False

    dlg.bind("<Destroy>", clear_ref, add="+")

