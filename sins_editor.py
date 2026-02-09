import json
import os
import sys
import gzip
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
import urllib.error
import urllib.request
from tkinter import filedialog, messagebox, ttk


class JsonEditor:
    APP_VERSION = "1.1.0"
    GITHUB_OWNER = "Siindbad"
    GITHUB_REPO = "HackHub-Save-File-Editor"
    GITHUB_ASSET_NAME = "sins_editor.exe"
    DIST_BRANCH = "main"
    DIST_VERSION_FILE = "version.txt"
    GITHUB_TOKEN_ENV = "GITHUB_TOKEN"

    def __init__(self, root, path):
        self.root = root
        self.root.title("SIINDBAD's HackHub Editor")
        self.data = None
        self.path = None
        self.seven_zip_path = self._find_7z()
        self.item_to_path = {}
        self.logo_image = None
        self.logo_label = None
        self.network_types = ["ROUTER", "DEVICE", "FIREWALL", "SPLITTER"]
        self.network_types_set = set(self.network_types)
        self.find_matches = []
        self.find_index = 0
        self.last_find_query = ""
        self.hidden_keys = {
            "Skills",
            "ObjectiveState",
            "EscMenu",
            "Save",
            "typewriter",
            "Typewriter",
            "Scoutify",
            "Dialog",
            "ftp",
            "Ftp",
            "GlobalStore",
            "GlobalVariables",
            "BrowserSession",
            "PersonalInfo",
            "Terminal",
            "Taskbar",
            "Phone",
            "PhoneCall",
            "stats",
            "ProgramSizes",
            "Computer",
            "Appstore",
            "AppStore",
            "Process",
            "Bookmarks",
            "BCCNews",
            "GameMode",
            "Hacked",
            "Surfaces",
            "_persist",
        }
        self.error_overlay = None

        self._build_ui()
        if path:
            self.load_file(path)

    def _build_ui(self):
        self._apply_dark_theme()
        self._set_window_icon()

        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=8, pady=(8, 4))

        logo_path = self._find_logo_path()
        if logo_path:
            self.logo_image = self._load_logo_image(logo_path)
        if self.logo_image:
            self.logo_label = ttk.Label(header, image=self.logo_image)
            self.logo_label.pack(anchor="center", pady=(4, 0))

        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=8, pady=6)

        ttk.Button(top, text="Open", command=self.open_file).pack(side="left")
        ttk.Button(top, text="Apply Edit", command=self.apply_edit).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Export .hhsav", command=self.export_hhsave).pack(side="left", padx=(6, 0))

        find_frame = ttk.Frame(top)
        find_frame.pack(side="left", padx=(12, 0))
        ttk.Label(find_frame, text="Find:").pack(side="left", padx=(0, 4))
        self.find_entry = ttk.Entry(find_frame, width=24)
        self.find_entry.pack(side="left")
        ttk.Button(find_frame, text="Find Next", command=self.find_next).pack(side="left", padx=(6, 0))
        self.find_entry.bind("<Return>", self.find_next)

        right_actions = ttk.Frame(top)
        right_actions.pack(side="right")
        ttk.Label(right_actions, text=f"v{self.APP_VERSION}").pack(side="left", padx=(0, 6))
        ttk.Button(right_actions, text="Update", command=self.check_for_updates_manual).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(right_actions, text="ReadMe", command=self.show_readme).pack(
            side="left", padx=(6, 0)
        )
        self.status = None

        body = ttk.Panedwindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=2)

        self.tree = ttk.Treeview(left, show="tree")
        self.tree.pack(fill="both", expand=True, side="left")
        tree_scroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        tree_scroll.pack(fill="y", side="right")
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.bind("<<TreeviewOpen>>", self.on_expand)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.text = tk.Text(right, wrap="none", height=10)
        self.text.pack(fill="both", expand=True, side="left")
        text_scroll = ttk.Scrollbar(right, orient="vertical", command=self.text.yview)
        text_scroll.pack(fill="y", side="right")
        self.text.configure(yscrollcommand=text_scroll.set)
        self._style_text_widget()

        self.root.after(500, self.check_for_updates_auto)

    def check_for_updates_auto(self):
        self._check_for_updates(auto=True)

    def check_for_updates_manual(self):
        self._check_for_updates(auto=False)

    def _check_for_updates(self, auto=False):
        if not getattr(sys, "frozen", False):
            if not auto:
                messagebox.showinfo(
                    "Update",
                    "Update checks are only available in the built .exe.",
                )
            return
        if self.GITHUB_OWNER == "YOUR_GITHUB_USERNAME" or self.GITHUB_REPO == "YOUR_REPO_NAME":
            if not auto:
                messagebox.showinfo(
                    "Update",
                    "Set GITHUB_OWNER and GITHUB_REPO in the source to enable updates.",
                )
            return

        def worker():
            try:
                self._set_status("Checking for updates...")
                latest_version = self._fetch_dist_version()
                if not latest_version:
                    self._set_status("")
                    if not auto:
                        messagebox.showinfo("Update", "No release info available.")
                    return

                latest_version = self._release_version(latest_version)
                current_version = self._release_version(self.APP_VERSION)
                if latest_version and current_version and latest_version < current_version:
                    self._set_status("")
                    if not auto:
                        messagebox.showwarning(
                            "Update",
                            "Release version is older than this build.\n"
                            f"Release: v{self._format_version(latest_version)}\n"
                            f"Current: v{self._format_version(current_version)}\n"
                            "Check dist/version.txt.",
                        )
                    return
                if latest_version == current_version:
                    self._set_status("Up to date.")
                    if not auto:
                        messagebox.showinfo("Update", "You're already on the latest version.")
                    return

                prompt = (
                    f"Update available: v{self._format_version(latest_version)}.\n"
                    "Download and install now?"
                )
                if not messagebox.askyesno("Update", prompt):
                    self._set_status("")
                    return

                self._set_status("Downloading update...")
                new_path = self._download_dist_asset()
                self._set_status("Installing update...")
                self._install_update(new_path)
            except Exception as exc:
                self._set_status("")
                if not auto:
                    messagebox.showerror("Update", f"Update failed: {exc}")
            finally:
                if auto:
                    self._set_status("")

        threading.Thread(target=worker, daemon=True).start()

    def _fetch_dist_version(self):
        url = self._dist_url(self.DIST_VERSION_FILE)
        req = urllib.request.Request(url, headers=self._download_headers())
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read().decode("utf-8")
        return data.strip()

    def _download_dist_asset(self):
        url = self._dist_url(self.GITHUB_ASSET_NAME)
        req = urllib.request.Request(url, headers=self._download_headers())
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        tmp_dir = tempfile.mkdtemp(prefix="sins_update_")
        new_path = os.path.join(tmp_dir, self.GITHUB_ASSET_NAME)
        with open(new_path, "wb") as handle:
            handle.write(data)
        return new_path

    def _install_update(self, new_path):
        exe_path = os.path.abspath(sys.executable)
        exe_name = os.path.basename(exe_path)
        bat_path = os.path.join(tempfile.gettempdir(), "sins_update.bat")
        log_path = os.path.join(tempfile.gettempdir(), "sins_update.log")
        fallback_path = exe_path + ".new"
        lines = [
            "@echo off",
            "setlocal",
            "set EXE_NAME=" + exe_name,
            "set EXE_PATH=" + exe_path,
            "set NEW_PATH=" + new_path,
            "set LOG_PATH=" + log_path,
            "set FALLBACK_PATH=" + fallback_path,
            "echo [%date% %time%] Update started > \"%LOG_PATH%\"",
            "echo EXE_PATH=%EXE_PATH% >> \"%LOG_PATH%\"",
            "echo NEW_PATH=%NEW_PATH% >> \"%LOG_PATH%\"",
            "echo FALLBACK_PATH=%FALLBACK_PATH% >> \"%LOG_PATH%\"",
            ":loop",
            "tasklist /FI \"IMAGENAME eq %EXE_NAME%\" | find /I \"%EXE_NAME%\" >nul",
            "if not errorlevel 1 (timeout /t 1 >nul & goto loop)",
            "set RETRIES=0",
            ":replace",
            "move /Y \"%NEW_PATH%\" \"%EXE_PATH%\" >> \"%LOG_PATH%\" 2>&1",
            "if errorlevel 1 goto fail",
            "echo [%date% %time%] Update applied >> \"%LOG_PATH%\"",
            "start \"\" \"%EXE_PATH%\"",
            "del \"%~f0\"",
            "exit /b 0",
            ":fail",
            "set /a RETRIES=%RETRIES%+1",
            "if %RETRIES% LSS 5 (timeout /t 1 >nul & goto replace)",
            "echo [%date% %time%] Update failed (move). >> \"%LOG_PATH%\"",
            "echo Trying fallback copy to %FALLBACK_PATH% >> \"%LOG_PATH%\"",
            "copy /Y \"%NEW_PATH%\" \"%FALLBACK_PATH%\" >> \"%LOG_PATH%\" 2>&1",
            "if errorlevel 1 (echo Fallback copy failed. >> \"%LOG_PATH%\") else (start \"\" explorer /select,\"%FALLBACK_PATH%\")",
            "exit /b 1",
        ]
        with open(bat_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        subprocess.Popen(
            ["cmd", "/c", bat_path],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        )
        self.root.after(200, self.root.destroy)

    def _release_version(self, version):
        if not version:
            return ()
        cleaned = version.strip().lstrip("vV")
        parts = []
        for token in cleaned.split("."):
            try:
                parts.append(int(token))
            except ValueError:
                break
        return tuple(parts)

    def _format_version(self, version_tuple):
        if not version_tuple:
            return ""
        return ".".join(str(part) for part in version_tuple)

    def _dist_url(self, filename):
        return (
            f"https://raw.githubusercontent.com/{self.GITHUB_OWNER}/{self.GITHUB_REPO}"
            f"/{self.DIST_BRANCH}/dist/{filename}"
        )

    def _download_headers(self):
        headers = {"User-Agent": "sins-editor"}
        token = os.getenv(self.GITHUB_TOKEN_ENV, "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _set_status(self, text):
        if self.status is None:
            return
        self.root.after(0, lambda: self.status.config(text=text))

    def _apply_dark_theme(self):
        bg = "#0f131a"
        fg = "#e6e6e6"
        panel = "#161b24"
        accent = "#2a3342"
        select_bg = "#2f3a4d"
        select_fg = "#ffffff"

        self.root.configure(bg=bg)

        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(".", background=bg, foreground=fg)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TButton", background=accent, foreground=fg, padding=6)
        style.map(
            "TButton",
            background=[("active", "#3a465c"), ("pressed", "#222a36")],
            foreground=[("disabled", "#888888")],
        )
        style.configure("TEntry", fieldbackground=panel, foreground=fg, insertcolor=fg)
        style.configure("TPanedwindow", background=bg)
        style.configure("TScrollbar", background=bg, troughcolor=panel)

        style.configure(
            "Treeview",
            background=panel,
            fieldbackground=panel,
            foreground=fg,
            rowheight=22,
            bordercolor=panel,
            lightcolor=panel,
            darkcolor=panel,
        )
        style.map(
            "Treeview",
            background=[("selected", select_bg)],
            foreground=[("selected", select_fg)],
        )
        self._theme = {
            "bg": bg,
            "fg": fg,
            "panel": panel,
            "select_bg": select_bg,
            "select_fg": select_fg,
        }

    def _style_text_widget(self):
        theme = getattr(self, "_theme", None)
        if not theme:
            return
        self.text.configure(
            bg=theme["panel"],
            fg=theme["fg"],
            insertbackground=theme["fg"],
            selectbackground=theme["select_bg"],
            selectforeground=theme["select_fg"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=theme["panel"],
            highlightcolor=theme["panel"],
        )

    def _find_logo_path(self):
        base_dir = self._resource_base_dir()
        candidates = [
            "assets/logo2.png",
            "assets/logo.png",
            "assets/logo.jpg",
            "assets/logo.jpeg",
            "logo2.png",
            "logo.png",
            "logo.jpg",
            "logo.jpeg",
        ]
        for rel_path in candidates:
            path = os.path.join(base_dir, rel_path)
            if os.path.isfile(path):
                return path
        return None

    def _resource_base_dir(self):
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return sys._MEIPASS
        return os.path.dirname(os.path.abspath(__file__))

    def _set_window_icon(self):
        base_dir = self._resource_base_dir()
        icon_path = os.path.join(base_dir, "assets", "sinlogo.ico")
        if os.path.isfile(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

    def _load_logo_image(self, path):
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in (".png", ".gif", ".ppm", ".pgm"):
                return tk.PhotoImage(file=path)
        except Exception:
            return None

        try:
            from PIL import Image, ImageTk
        except Exception:
            return None

        try:
            image = Image.open(path)
            max_width = 700
            if image.width > max_width:
                scale = max_width / image.width
                new_size = (max_width, int(image.height * scale))
                image = image.resize(new_size, Image.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception:
            return None

    def show_readme(self):
        theme = getattr(self, "_theme", None)
        base_dir = self._resource_base_dir()
        readme_path = os.path.join(base_dir, "assets", "Readme.txt")
        content = ""
        if os.path.isfile(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
            except Exception as exc:
                messagebox.showerror("ReadMe", f"Failed to load README.md: {exc}")
                return
        else:
            content = "Readme.txt not found in assets."

        window = tk.Toplevel(self.root)
        window.title("ReadMe")
        window.geometry("760x520")
        window.transient(self.root)
        if theme:
            window.configure(bg=theme["bg"])

        frame = ttk.Frame(window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        text = tk.Text(frame, wrap="word")
        text.pack(fill="both", expand=True, side="left")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        scroll.pack(fill="y", side="right")
        text.configure(yscrollcommand=scroll.set)
        if theme:
            text.configure(
                bg="#000000",
                fg=theme["fg"],
                insertbackground=theme["fg"],
                selectbackground=theme["select_bg"],
                selectforeground=theme["select_fg"],
                relief="flat",
                highlightthickness=1,
                highlightbackground=theme["panel"],
                highlightcolor=theme["panel"],
            )
        text.insert("1.0", content)
        text.configure(state="disabled")

    def set_status(self, msg):
        if self.status is not None:
            self.status.config(text=msg)

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open File",
            filetypes=[("HackHub Save (.hhsav)", "*.hhsav")],
        )
        if path:
            self.load_file(path)

    def load_file(self, path):
        try:
            if path.lower().endswith(".hhsav"):
                with gzip.open(path, "rb") as f:
                    raw = f.read().decode("utf-8")
                self.data = json.loads(raw)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))
            return

        self.path = path
        self.root.title(f"SIINDBAD's HackHub Editor - {os.path.basename(path)}")
        self._rebuild_tree()
        self.set_status("Loaded")

    def _rebuild_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.item_to_path.clear()
        self._reset_find_state()

        root_id = self.tree.insert("", "end", text="root", open=True)
        self.item_to_path[root_id] = []
        self._add_placeholder_if_container(root_id, self.data)
        self._populate_children(root_id)

    def _add_placeholder_if_container(self, item_id, value):
        if isinstance(value, (dict, list)) and len(value) > 0:
            self.tree.insert(item_id, "end", text="(loading)")

    def _reset_find_state(self):
        self.find_matches = []
        self.find_index = 0
        self.last_find_query = ""

    def _collect_tree_items(self, root_id=""):
        items = []
        for child in self.tree.get_children(root_id):
            items.append(child)
            items.extend(self._collect_tree_items(child))
        return items

    def _has_loading_child(self, item_id):
        children = self.tree.get_children(item_id)
        if len(children) != 1:
            return False
        return self.tree.item(children[0], "text") == "(loading)"

    def _ensure_all_loaded(self, root_id=""):
        for child in self.tree.get_children(root_id):
            if self._has_loading_child(child):
                self._populate_children(child)
            self._ensure_all_loaded(child)

    def _open_to_item(self, item_id):
        parent = self.tree.parent(item_id)
        while parent:
            self.tree.item(parent, open=True)
            parent = self.tree.parent(parent)

    def find_next(self, event=None):
        query = self.find_entry.get().strip()
        if not query:
            self.set_status("Find: enter text to search")
            return

        query_lower = query.lower()
        if query_lower != self.last_find_query:
            self._ensure_all_loaded()
            items = self._collect_tree_items()
            self.find_matches = [
                item_id
                for item_id in items
                if query_lower in self.tree.item(item_id, "text").lower()
            ]
            self.find_index = 0
            self.last_find_query = query_lower

        if not self.find_matches:
            self.set_status(f'Find: no matches for "{query}"')
            return

        item_id = self.find_matches[self.find_index]
        self.find_index = (self.find_index + 1) % len(self.find_matches)
        self._open_to_item(item_id)
        self.tree.selection_set(item_id)
        self.tree.see(item_id)
        self.on_select(None)
        self.set_status(f'Find: {self.find_index}/{len(self.find_matches)}')

    def _populate_children(self, item_id):
        path = self.item_to_path.get(item_id)
        if isinstance(path, tuple) and path[0] == "__group__":
            return
        value = self._get_value(path)
        if not isinstance(value, (dict, list)):
            return

        # Clear existing children
        for child in self.tree.get_children(item_id):
            self.tree.delete(child)

        if isinstance(value, dict):
            for key in value.keys():
                if key in self.hidden_keys:
                    continue
                child_id = self.tree.insert(item_id, "end", text=str(key))
                self.item_to_path[child_id] = path + [key]
                self._add_placeholder_if_container(child_id, value[key])
        elif isinstance(value, list) and self._is_network_list(path, value):
            groups = {}
            for idx, item in enumerate(value):
                group = item.get("type") if isinstance(item, dict) else "UNKNOWN"
                groups.setdefault(group, []).append((idx, item))

            ordered_groups = [t for t in self.network_types if t in groups]
            for group in sorted(g for g in groups.keys() if g not in self.network_types_set):
                ordered_groups.append(group)

            for group in ordered_groups:
                items = groups[group]
                group_id = self.tree.insert(item_id, "end", text=f"{group} ({len(items)})")
                self.item_to_path[group_id] = ("__group__", path, group)
                for idx, item in items:
                    label = f"[{idx}]"
                    if isinstance(item, dict):
                        if group in ("ROUTER", "DEVICE", "FIREWALL", "SPLITTER"):
                            ip = item.get("ip")
                            if group == "SPLITTER":
                                name = None
                            elif group == "FIREWALL":
                                name = None
                                users = item.get("users")
                                if isinstance(users, list) and users:
                                    user0 = users[0]
                                    if isinstance(user0, dict):
                                        name = user0.get("id")
                            else:
                                name = item.get("name")
                                if not name:
                                    domain = item.get("domain")
                                    if isinstance(domain, dict):
                                        name = domain.get("name")
                                if not name:
                                    users = item.get("users")
                                    if isinstance(users, list) and users:
                                        user0 = users[0]
                                        if isinstance(user0, dict):
                                            name = user0.get("firstName") or user0.get("name")
                            if ip is not None or name is not None:
                                ip_str = "" if ip is None else str(ip)
                                name_str = "" if name is None else str(name)
                                label += f" {ip_str} | {name_str}"
                            else:
                                extra = []
                                if "id" in item:
                                    extra.append(f"id={item['id']}")
                                if "ip" in item:
                                    extra.append(f"ip={item['ip']}")
                                if extra:
                                    label += " " + " ".join(extra)
                        else:
                            extra = []
                            if "id" in item:
                                extra.append(f"id={item['id']}")
                            if "ip" in item:
                                extra.append(f"ip={item['ip']}")
                            if extra:
                                label += " " + " ".join(extra)
                    child_id = self.tree.insert(group_id, "end", text=label)
                    self.item_to_path[child_id] = path + [idx]
                    self._add_placeholder_if_container(child_id, item)
        elif isinstance(value, list) and self._is_mail_accounts_list(path, value):
            for idx, item in enumerate(value):
                label = self._mail_account_label(idx, item)
                child_id = self.tree.insert(item_id, "end", text=label)
                self.item_to_path[child_id] = path + [idx]
                self._add_placeholder_if_container(child_id, item)
        elif isinstance(value, list) and self._is_mails_list(path, value):
            for idx, item in enumerate(value):
                label = self._mails_label(idx, item)
                child_id = self.tree.insert(item_id, "end", text=label)
                self.item_to_path[child_id] = path + [idx]
                self._add_placeholder_if_container(child_id, item)
        elif isinstance(value, list) and self._is_phone_messages_list(path, value):
            for idx, item in enumerate(value):
                label = self._phone_messages_label(idx, item)
                child_id = self.tree.insert(item_id, "end", text=label)
                self.item_to_path[child_id] = path + [idx]
                self._add_placeholder_if_container(child_id, item)
        elif isinstance(value, list) and self._is_files_list(path, value):
            for idx, item in enumerate(value):
                label = self._files_label(idx, item)
                child_id = self.tree.insert(item_id, "end", text=label)
                self.item_to_path[child_id] = path + [idx]
                self._add_placeholder_if_container(child_id, item)
        elif isinstance(value, list) and self._is_database_list(path, value):
            for idx, item in enumerate(value):
                label = self._database_label(idx, item)
                child_id = self.tree.insert(item_id, "end", text=label)
                self.item_to_path[child_id] = path + [idx]
                self._add_placeholder_if_container(child_id, item)
        elif isinstance(value, list) and self._is_twotter_users_list(path, value):
            for idx, item in enumerate(value):
                label = self._twotter_user_label(idx, item)
                child_id = self.tree.insert(item_id, "end", text=label)
                self.item_to_path[child_id] = path + [idx]
                self._add_placeholder_if_container(child_id, item)
        elif isinstance(value, list) and self._is_quests_list(path, value):
            for idx, item in enumerate(value):
                label = self._quests_label(idx, item)
                child_id = self.tree.insert(item_id, "end", text=label)
                self.item_to_path[child_id] = path + [idx]
                self._add_placeholder_if_container(child_id, item)
        elif isinstance(value, list) and self._is_kisscord_friends_list(path, value):
            for idx, item in enumerate(value):
                label = self._kisscord_friend_label(idx, item)
                child_id = self.tree.insert(item_id, "end", text=label)
                self.item_to_path[child_id] = path + [idx]
                self._add_placeholder_if_container(child_id, item)
        elif isinstance(value, list) and self._is_website_templates_list(path, value):
            for idx, item in enumerate(value):
                label = self._website_templates_label(idx, item)
                child_id = self.tree.insert(item_id, "end", text=label)
                self.item_to_path[child_id] = path + [idx]
                self._add_placeholder_if_container(child_id, item)
        elif isinstance(value, list) and self._is_terminal_packages_list(path, value):
            for idx, item in enumerate(value):
                label = self._terminal_package_label(idx, item)
                child_id = self.tree.insert(item_id, "end", text=label)
                self.item_to_path[child_id] = path + [idx]
                self._add_placeholder_if_container(child_id, item)
        elif isinstance(value, list) and self._is_terminal_datalist(path, value):
            for idx, item in enumerate(value):
                label = self._terminal_datalist_label(idx, item)
                child_id = self.tree.insert(item_id, "end", text=label)
                self.item_to_path[child_id] = path + [idx]
                self._add_placeholder_if_container(child_id, item)
        else:
            for idx, item in enumerate(value):
                child_id = self.tree.insert(item_id, "end", text=f"[{idx}]")
                self.item_to_path[child_id] = path + [idx]
                self._add_placeholder_if_container(child_id, item)

    def on_expand(self, event):
        item_id = self.tree.focus()
        if item_id:
            self._populate_children(item_id)

    def on_select(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        path = self.item_to_path.get(item_id, [])
        if isinstance(path, tuple) and path[0] == "__group__":
            _, list_path, group = path
            value = self._get_value(list_path)
            group_items = [
                item for item in value
                if isinstance(item, dict) and item.get("type") == group
            ]
            self._show_value(group_items)
            self.set_status(f"group {group} ({len(group_items)})")
            return
        value = self._get_value(path)
        self._show_value(value)
        self.set_status(self._describe(value))

    def _show_value(self, value):
        self.text.delete("1.0", "end")
        try:
            rendered = json.dumps(value, indent=2, ensure_ascii=False)
        except TypeError:
            rendered = str(value)
        self.text.insert("1.0", rendered)

    def _describe(self, value):
        if isinstance(value, dict):
            return f"dict ({len(value)} keys)"
        if isinstance(value, list):
            return f"list ({len(value)} items)"
        return f"{type(value).__name__}"


    def apply_edit(self):
        item_id = self.tree.focus()
        if not item_id:
            messagebox.showwarning("No selection", "Select a node in the tree.")
            return
        path = self.item_to_path.get(item_id, [])
        if isinstance(path, tuple) and path[0] == "__group__":
            messagebox.showwarning("Not editable", "Select a specific item to edit.")
            return

        raw = self.text.get("1.0", "end").strip()
        try:
            new_value = json.loads(raw)
        except Exception as exc:
            self._show_error_overlay("Invalid Entry", self._format_json_error(exc))
            self._highlight_json_error(exc)
            return
        self._clear_json_error_highlight()

        if not self._is_edit_allowed(path, new_value):
            return

        self._set_value(path, new_value)

        # Refresh subtree
        self._populate_children(item_id)
        self.set_status("Edited")

    def _format_json_error(self, exc):
        msg = getattr(exc, "msg", None)
        if isinstance(exc, json.JSONDecodeError) or msg:
            example = self._example_for_error(exc)
            if msg == "Expecting ',' delimiter":
                if self._is_missing_object_open_at(getattr(exc, "lineno", None)):
                    before, after = "{", "{"
                    return self._format_suggestion(
                        "Invalid Entry: add \"{\" before the highlighted line.",
                        before,
                        after,
                    )
                if self._is_missing_object_open(exc):
                    before, after = self._suggestion_from_example(example, add_after="{")
                    return self._format_suggestion(
                        "Invalid Entry: add \"{\" after the highlighted line.",
                        before,
                        after,
                    )
                if self._is_missing_object_close():
                    before, after = self._suggestion_from_example(example, add_after="},")
                    return self._format_suggestion(
                        "Invalid Entry: add the missing closing bracket.",
                        before,
                        after,
                    )
                if self._is_missing_list_close():
                    before, after = self._suggestion_from_example(example, add_after="],")
                    return self._format_suggestion(
                        "Invalid Entry: add the missing closing bracket.",
                        before,
                        after,
                    )
                before, after = self._suggestion_from_example(example, add_after=",")
                return self._format_suggestion(
                    "Invalid Entry: add a comma near the highlighted line.",
                    before,
                    after,
                )
            if msg == "Expecting property name enclosed in double quotes":
                before, after = self._suggestion_from_example(example, quote_key=True)
                return self._format_suggestion(
                    "Invalid Entry: add quotes around the highlighted name.",
                    before,
                    after,
                )
            if msg == "Expecting ':' delimiter":
                before, after = self._suggestion_from_example(example, add_colon=True)
                return self._format_suggestion(
                    "Invalid Entry: add a colon after the highlighted name.",
                    before,
                    after,
                )
            if msg in ("Expecting ']'", "Expecting '}'"):
                before, after = self._suggestion_from_example(example, add_after=example.strip())
                return self._format_suggestion(
                    "Invalid Entry: add the missing closing bracket.",
                    before,
                    after,
                )
            if msg == "Expecting value":
                if self._is_missing_object_open(exc):
                    before, after = self._suggestion_from_example(example, add_after="{")
                    return self._format_suggestion(
                        "Invalid Entry: add \"{\" after the highlighted line.",
                        before,
                        after,
                    )
                if self._is_missing_list_open(exc):
                    before, after = self._suggestion_from_example(example, add_after="[")
                    return self._format_suggestion(
                        "Invalid Entry: add \"[\" after the highlighted line.",
                        before,
                        after,
                    )
                if self._is_missing_list_close():
                    before, after = self._suggestion_from_example(example, add_after="],")
                    return self._format_suggestion(
                        "Invalid Entry: add the missing closing bracket.",
                        before,
                        after,
                    )
            if msg == "Extra data":
                before, after = self._suggestion_from_example(example)
                return self._format_suggestion(
                    "Invalid Entry: extra data after a complete value. Remove it or wrap values in [].",
                    before,
                    after,
                )
            if msg in ("Unexpected ']'", "Unexpected '}'"):
                before, after = self._suggestion_from_example(example)
                return self._format_suggestion(
                    "Invalid Entry: remove the extra closing bracket.",
                    before,
                    after,
                )
            if msg == "Unterminated string":
                before, after = self._suggestion_from_example(example, add_after="\"")
                return self._format_suggestion(
                    "Invalid Entry: close the quote.",
                    before,
                    after,
                )
            return (
                "Invalid Entry: check the highlighted line.\n\n"
                f"{self._format_suggestion('Suggestion', example, example, header_only=True)}"
            )
        return str(exc)

    def _example_for_error(self, exc):
        lineno = getattr(exc, "lineno", None)
        line_text = ""
        if lineno:
            try:
                line_text = self.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()
            except Exception:
                line_text = ""

        msg = getattr(exc, "msg", None)
        if msg == "Expecting ',' delimiter":
            if self._is_missing_object_open_at(lineno):
                return "{"
            if self._is_missing_object_open(exc):
                return self._missing_object_example(lineno)
            if self._is_missing_object_close():
                return self._missing_close_example("Expecting '}'")
            if self._is_missing_list_close():
                return self._missing_close_example("Expecting ']'")
            return self._comma_example_line(lineno)

        if msg == "Expecting property name enclosed in double quotes":
            if line_text:
                return self._quote_property_name(line_text)
            return "\"key\": \"value\""

        if msg == "Expecting ':' delimiter":
            if line_text:
                return self._missing_colon_example(line_text)
            return "\"key\": \"value\""

        if msg in ("Expecting ']'", "Expecting '}'"):
            return self._missing_close_example(msg)

        if msg == "Expecting value":
            if self._is_missing_list_close():
                return self._missing_close_example("Expecting ']'")
            if self._is_missing_object_close():
                return self._missing_close_example("Expecting '}'")
            if self._is_missing_list_open(exc):
                return "\"items\": ["
            if self._is_missing_object_open(exc):
                return "\"data\": {"

        if msg == "Extra data":
            next_line = self._next_non_empty_line(lineno or 1)
            if next_line:
                next_text = self._line_text(next_line).strip()
                if next_text:
                    return next_text
            if line_text:
                return line_text
            return "\"key\": \"value\""

        if msg in ("Unexpected ']'", "Unexpected '}'"):
            return self._missing_close_example(msg)

        if msg == "Unterminated string":
            return "\"text\""

        if line_text:
            return line_text
        return "\"key\": \"value\""

    def _missing_colon_example(self, line_text):
        if ":" in line_text:
            return line_text
        stripped = line_text.strip().strip(",")
        if not stripped:
            return "\"key\": \"value\""
        if not stripped.startswith("\""):
            stripped = f"\"{stripped.strip()}\""
        return f"{stripped}: \"value\""

    def _missing_close_example(self, msg):
        if msg in ("Expecting ']'", "Unexpected ']'"):
            return "],"
        return "},"

    def _format_suggestion(self, header, before, after, header_only=False):
        if header_only:
            return f"Suggestion:\n- Before: {before}\n- After:  {after}"
        return f"{header}\n\nSuggestion:\n- Before: {before}\n- After:  {after}"

    def _suggestion_from_example(self, example, add_after=None, add_colon=False, quote_key=False):
        before = example.strip()
        after = before
        if quote_key:
            after = self._quote_property_name(before)
        if add_colon and ":" not in after:
            if after and not after.endswith(":"):
                after = after.rstrip(",") + ": \"value\""
        if add_after:
            if add_after in (",", "],", "},", "{", "["):
                if add_after == ",":
                    before = before.rstrip().rstrip(",")
                    after = before + ","
                else:
                    after = add_after
                    if add_after in ("},", "],"):
                        before = add_after.replace(",", "")
                    if add_after in ("{", "["):
                        before = add_after
            else:
                after = add_after
        return (before if before else "\"value\""), (after if after else "\"value\"")
    def _is_missing_object_open_at(self, lineno):
        if not lineno:
            return False
        line_text = self._line_text(lineno).lstrip()
        if not line_text or ":" not in line_text:
            return False
        prev_line_num = self._closest_non_empty_line_before(lineno)
        if not prev_line_num:
            return False
        prev_text = self._line_text(prev_line_num).strip()
        if prev_text in ("[", ",", "],", "{", "},"):
            return True
        return False

    def _line_text(self, lineno):
        try:
            return self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")
        except Exception:
            return ""

    def _missing_close_target_line_from_exc(self, exc, open_bracket, close_bracket):
        line = getattr(exc, "lineno", None)
        if line:
            return line
        return self._missing_close_target_line(open_bracket, close_bracket)

    def _missing_close_target_line_any(self, exc):
        if self._is_missing_object_close():
            target = self._missing_object_close_target_line(exc)
            if target:
                return target
        if self._is_missing_list_close():
            target = self._missing_list_close_target_line(exc)
            if target:
                return target
        return None

    def _missing_list_close_target_line(self, exc):
        line = getattr(exc, "lineno", None)
        if not line:
            return None
        comma_line = self._find_comma_only_line_before(line)
        if comma_line:
            return comma_line
        return self._closest_non_empty_line_before(line)

    def _is_missing_list_close(self):
        text = self.text.get("1.0", "end-1c")
        return text.count("[") > text.count("]")

    def _is_missing_object_close(self):
        text = self.text.get("1.0", "end-1c")
        return text.count("{") > text.count("}")

    def _last_unmatched_bracket_line(self, open_bracket, close_bracket):
        text = self.text.get("1.0", "end-1c")
        stack = []
        line = 1
        col = 0
        for ch in text:
            if ch == "\n":
                line += 1
                col = 0
                continue
            col += 1
            if ch == open_bracket:
                stack.append(line)
            elif ch == close_bracket and stack:
                stack.pop()
        if stack:
            return stack[-1]
        return None

    def _missing_object_close_target_line(self, exc):
        line = getattr(exc, "lineno", None)
        if not line:
            return None
        comma_line = self._find_comma_only_line_before(line)
        if comma_line:
            return comma_line
        return self._closest_non_empty_line_before(line)

    def _find_comma_only_line_before(self, start_line):
        line = max(start_line - 1, 1)
        while line >= 1:
            try:
                text = self.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except Exception:
                return None
            if text == ",":
                return line
            line -= 1
        return None

    def _closest_non_empty_line_before(self, start_line):
        line = max(start_line - 1, 1)
        while line >= 1:
            try:
                text = self.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except Exception:
                return None
            if text:
                return line
            line -= 1
        return None


    def _missing_close_target_line(self, open_bracket, close_bracket):
        open_line = self._last_unmatched_bracket_line(open_bracket, close_bracket)
        if not open_line:
            return None
        line = open_line + 1
        last_line = int(self.text.index("end-1c").split(".")[0])
        while line <= last_line:
            try:
                text = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                return open_line
            if text.strip():
                return line
            line += 1
        return open_line

    def _is_missing_object_open(self, exc):
        lineno = getattr(exc, "lineno", None)
        if not lineno:
            return False
        prev_line = self._previous_non_empty_line(lineno)
        if not prev_line:
            return False
        prev_line_stripped = prev_line.strip()
        return prev_line_stripped.endswith("\":") and not prev_line_stripped.endswith("\": {")

    def _is_missing_list_open(self, exc):
        lineno = getattr(exc, "lineno", None)
        if not lineno:
            return False
        prev_line = self._previous_non_empty_line(lineno)
        if not prev_line:
            return False
        prev_line_stripped = prev_line.strip()
        if not prev_line_stripped.endswith("\":"):
            return False
        next_line = self._next_non_empty_line(lineno)
        if not next_line:
            return False
        next_line_stripped = next_line.strip()
        return next_line_stripped.startswith("\"")

    def _previous_non_empty_line(self, lineno):
        line = max(lineno - 1, 1)
        while line >= 1:
            try:
                text = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                return ""
            if text.strip():
                return text
            line -= 1
        return ""

    def _next_non_empty_line(self, lineno):
        line = max(lineno, 1)
        last_line = int(self.text.index("end-1c").split(".")[0])
        while line <= last_line:
            try:
                text = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                return ""
            if text.strip():
                return text
            line += 1
        return ""

    def _missing_object_example(self, lineno):
        prev_line = self._previous_non_empty_line(lineno)
        if not prev_line:
            return "\"data\": {"
        prev_line_stripped = prev_line.strip()
        if prev_line_stripped.endswith("\":"):
            return prev_line_stripped + " {"
        return "\"data\": {"

    def _quote_property_name(self, line_text):
        if ":" in line_text:
            left, right = line_text.split(":", 1)
            left = left.strip()
            if not left.startswith("\""):
                left = f"\"{left.strip().strip(',')}\""
            right = right.strip()
            return f"{left}: {right}"
        return "\"key\": \"value\""

    def _comma_example_line(self, lineno):
        if not lineno:
            return "\"item1\",\n\"item2\""
        target_line = max(lineno - 1, 1)
        try:
            line_text = self.text.get(f"{target_line}.0", f"{target_line}.0 lineend").strip()
        except Exception:
            line_text = ""
        if not line_text:
            return "\"item1\",\n\"item2\""
        if not line_text.endswith(","):
            line_text = line_text.rstrip()
            line_text = line_text + ","
        return line_text

    def _highlight_json_error(self, exc):
        line = getattr(exc, "lineno", None)
        col = getattr(exc, "colno", None)
        try:
            last_line = int(self.text.index("end-1c").split(".")[0])
            if not line:
                line = 1
            if not col:
                col = 1
            line = min(max(line, 1), max(last_line, 1))
            msg = getattr(exc, "msg", None)
            if msg == "Expecting ',' delimiter":
                if self._is_missing_object_open_at(line):
                    line_end = self.text.index(f"{line}.0 lineend")
                    start_index = f"{line}.0"
                    end_index = line_end
                    self.text.tag_remove("json_error", "1.0", "end")
                    self.text.tag_remove("json_error_line", "1.0", "end")
                    self.text.tag_add("json_error", start_index, end_index)
                    self.text.tag_config("json_error", background="#0b6b2b", foreground="#ffffff")
                    self.text.tag_add("json_error_line", f"{line}.0", f"{line}.0 lineend")
                    self.text.tag_config("json_error_line", background="#0f3f24")
                    self.text.mark_set("insert", start_index)
                    self.text.see(start_index)
                    self._log_json_error(exc, line)
                    self._position_error_overlay(line)
                    return
                if self._is_missing_object_open(exc):
                    line = max(line - 1, 1)
                    line_end = self.text.index(f"{line}.0 lineend")
                    start_index = line_end
                    end_index = line_end
                elif self._is_missing_object_close():
                    target_line = self._missing_close_target_line_any(exc)
                    if not target_line:
                        target_line = self._missing_close_target_line_from_exc(exc, "{", "}")
                    if not target_line:
                        target_line = int(self.text.index("end-1c").split(".")[0])
                    line = max(target_line, 1)
                    line_end = self.text.index(f"{line}.0 lineend")
                    start_index = line_end
                    end_index = line_end
                elif self._is_missing_list_close():
                    target_line = self._missing_close_target_line_any(exc)
                    if not target_line:
                        target_line = self._missing_close_target_line_from_exc(exc, "[", "]")
                    if not target_line:
                        target_line = int(self.text.index("end-1c").split(".")[0])
                    line = max(target_line, 1)
                    line_end = self.text.index(f"{line}.0 lineend")
                    start_index = line_end
                    end_index = line_end
                else:
                    line = max(line - 1, 1)
                    line_end = self.text.index(f"{line}.0 lineend")
                    start_index = line_end
                    end_index = line_end
            elif msg == "Expecting ':' delimiter":
                start_index = f"{line}.{max(col - 1, 0)}"
                end_index = f"{line}.{col}"
            elif msg in ("Expecting ']'", "Expecting '}'"):
                target_line = self._missing_close_target_line_any(exc)
                if not target_line:
                    if exc.msg == "Expecting ']'":
                        target_line = self._missing_close_target_line_from_exc(exc, "[", "]")
                    else:
                        target_line = self._missing_close_target_line_from_exc(exc, "{", "}")
                if not target_line:
                    target_line = int(self.text.index("end-1c").split(".")[0])
                line = max(target_line, 1)
                line_end = self.text.index(f"{line}.0 lineend")
                start_index = line_end
                end_index = line_end
            elif msg == "Expecting value":
                if self._is_missing_object_open(exc):
                    line = max(line - 1, 1)
                    line_end = self.text.index(f"{line}.0 lineend")
                    start_index = line_end
                    end_index = line_end
                elif self._is_missing_list_open(exc):
                    line = max(line - 1, 1)
                    line_end = self.text.index(f"{line}.0 lineend")
                    start_index = line_end
                    end_index = line_end
                elif self._is_missing_list_close() or self._is_missing_object_close():
                    target_line = self._missing_close_target_line_any(exc)
                    if not target_line:
                        target_line = int(self.text.index("end-1c").split(".")[0])
                    line = max(target_line, 1)
                    line_end = self.text.index(f"{line}.0 lineend")
                    start_index = line_end
                    end_index = line_end
                else:
                    start_index = f"{line}.{max(col - 1, 0)}"
                    end_index = f"{line}.{col}"
            elif msg in ("Unexpected ']'", "Unexpected '}'", "Unterminated string"):
                start_index = f"{line}.{max(col - 1, 0)}"
                end_index = f"{line}.{col}"
            elif msg == "Extra data":
                next_line = self._next_non_empty_line(line)
                if next_line:
                    line = next_line
                line_end = self.text.index(f"{line}.0 lineend")
                start_index = f"{line}.0"
                end_index = line_end
            else:
                line = max(line - 1, 1)
                line_end = self.text.index(f"{line}.0 lineend")
                start_index = line_end
                end_index = line_end
            self.text.tag_remove("json_error", "1.0", "end")
            self.text.tag_remove("json_error_line", "1.0", "end")
            self.text.tag_add("json_error", start_index, end_index)
            self.text.tag_config("json_error", background="#0b6b2b", foreground="#ffffff")
            self.text.tag_add("json_error_line", f"{line}.0", f"{line}.0 lineend")
            self.text.tag_config("json_error_line", background="#0f3f24")
            self.text.mark_set("insert", start_index)
            self.text.see(start_index)
            self._log_json_error(exc, line)
            self._position_error_overlay(line)
        except Exception as highlight_exc:
            try:
                self._log_json_error(exc, line or 1, note=f"highlight_failed: {highlight_exc}")
            except Exception:
                pass
            return

    def _position_error_overlay(self, line):
        if self.error_overlay is None:
            return
        try:
            bbox = self.text.bbox(f"{line}.0")
            if not bbox:
                return
            x, y, w, h = bbox
            text_w = self.text.winfo_width()
            text_h = self.text.winfo_height()
            overlay = self.error_overlay
            overlay.update_idletasks()
            ow = overlay.winfo_width()
            oh = overlay.winfo_height()

            gap = 6
            # Prefer below; if not enough space, try right
            nx = x
            ny = y + h + gap
            if ny + oh > text_h:
                nx = x + w + gap
                ny = y
            if ny + oh > text_h:
                ny = max(text_h - oh - gap, 0)
            if nx + ow > text_w:
                nx = max(text_w - ow - gap, 0)

            overlay.place_configure(x=nx, y=ny)
        except Exception:
            return

    def _log_json_error(self, exc, target_line, note=""):
        try:
            log_path = os.path.join(tempfile.gettempdir(), "sins_json_diagnostics.log")
            msg = getattr(exc, "msg", str(exc))
            lineno = getattr(exc, "lineno", None)
            colno = getattr(exc, "colno", None)
            context = []
            start = max(target_line - 2, 1)
            end = target_line + 2
            for ln in range(start, end + 1):
                try:
                    text = self.text.get(f"{ln}.0", f"{ln}.0 lineend")
                except Exception:
                    text = ""
                context.append(f"{ln}: {text}")
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write("\n---\n")
                handle.write(f"msg={msg} lineno={lineno} col={colno} target={target_line} {note}\n")
                handle.write("\n".join(context).rstrip() + "\n")
        except Exception:
            return

    def _clear_json_error_highlight(self):
        try:
            self.text.tag_remove("json_error", "1.0", "end")
            self.text.tag_remove("json_error_line", "1.0", "end")
        except Exception:
            return

    def _show_error_overlay(self, title, message):
        self._destroy_error_overlay()
        overlay = tk.Frame(self.text, bg="#11161f", bd=0, highlightthickness=2, highlightbackground="#0b6b2b")
        overlay.place(x=12, y=12)

        msg_label = tk.Label(
            overlay,
            text=message,
            bg="#11161f",
            fg="#ffffff",
            font=("Consolas", 9),
            anchor="w",
            justify="left",
        )
        msg_label.pack(fill="both", padx=10, pady=(8, 8))

        overlay.bind("<Button-1>", lambda _evt: self._destroy_error_overlay())
        msg_label.bind("<Button-1>", lambda _evt: self._destroy_error_overlay())

        self.error_overlay = overlay

    def _destroy_error_overlay(self):
        if self.error_overlay is not None:
            try:
                self.error_overlay.destroy()
            except Exception:
                pass
            self.error_overlay = None

    def save_file(self):
        if not self.path:
            return self.save_file_as()
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        self.set_status("Saved")

    def save_file_as(self):
        path = filedialog.asksaveasfilename(
            title="Save JSON",
            defaultextension=".json",
            filetypes=[("All Files", "*.*"), ("JSON", "*.json")],
        )
        if not path:
            return
        self.path = path
        self.save_file()

    def export_hhsave(self):
        default_ext = ".hhsav"
        initialfile = None
        if self.path:
            base = os.path.basename(self.path)
            name, ext = os.path.splitext(base)
            if ext.lower() == ".hhsav":
                default_ext = ".hhsav"
                initialfile = base
            else:
                initialfile = f"{name}{default_ext}"
        path = filedialog.asksaveasfilename(
            title="Export As .hhsav (gzip)",
            defaultextension=default_ext,
            filetypes=[("HackHub Save (.hhsav)", "*.hhsav")],
            initialfile=initialfile,
        )
        if not path:
            return
        if not path.lower().endswith(".hhsav"):
            path += default_ext
        try:
            payload = json.dumps(self.data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            with tempfile.TemporaryDirectory() as tmpdir:
                src_path = os.path.join(tmpdir, "save.json")
                gzip_path = os.path.join(tmpdir, "save.gz")
                with open(src_path, "wb") as f:
                    f.write(payload)
                seven_zip = self._ensure_7z()
                result = subprocess.run(
                    [seven_zip, "a", "-tgzip", "-mx=9", gzip_path, src_path],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    detail = result.stderr.strip() or result.stdout.strip()
                    raise RuntimeError(f"7z failed: {detail or 'unknown error'}")
                shutil.move(gzip_path, path)
        except FileNotFoundError:
            messagebox.showerror(
                "Export failed",
                "7z not found. Install 7-Zip or select 7z.exe when prompted.",
            )
            return
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        self.set_status("Exported .hhsav")

    def _find_7z(self):
        candidate = shutil.which("7z")
        if candidate:
            return candidate
        common_paths = [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
        ]
        for path in common_paths:
            if os.path.isfile(path):
                return path
        return None

    def _ensure_7z(self):
        if self.seven_zip_path and os.path.isfile(self.seven_zip_path):
            return self.seven_zip_path
        path = filedialog.askopenfilename(
            title="Locate 7z.exe",
            filetypes=[("7-Zip", "7z.exe"), ("All Files", "*.*")],
        )
        if not path:
            raise FileNotFoundError("7z not selected")
        self.seven_zip_path = path
        return path

    def _get_value(self, path):
        value = self.data
        for key in path:
            value = value[key]
        return value

    def _set_value(self, path, new_value):
        if not path:
            self.data = new_value
            return
        parent = self.data
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = new_value

    def _is_network_list(self, path, value):
        if path != ["Network"]:
            return False
        if not value:
            return False
        return all(
            isinstance(item, dict) and item.get("type") in self.network_types_set
            for item in value
        )

    def _is_mail_accounts_list(self, path, value):
        if path != ["MailAccounts"]:
            return False
        return isinstance(value, list)

    def _mail_account_label(self, idx, item):
        if isinstance(item, dict):
            full_name = item.get("fullName")
            if full_name:
                return f"[{idx}] {full_name}"
        return f"[{idx}]"

    def _is_mails_list(self, path, value):
        if path != ["Mails"]:
            return False
        return isinstance(value, list)

    def _mails_label(self, idx, item):
        if isinstance(item, dict):
            from_value = item.get("from")
            if from_value:
                return f"[{idx}] {from_value}"
        return f"[{idx}]"

    def _is_phone_messages_list(self, path, value):
        if path != ["PhoneMessages"]:
            return False
        return isinstance(value, list)

    def _phone_messages_label(self, idx, item):
        if isinstance(item, dict):
            from_value = item.get("from")
            if from_value:
                return f"[{idx}] {from_value}"
        return f"[{idx}]"

    def _is_files_list(self, path, value):
        if path != ["Files"]:
            return False
        return isinstance(value, list)

    def _files_label(self, idx, item):
        if isinstance(item, dict):
            name = item.get("name")
            if name:
                return f"[{idx}] {name}"
        return f"[{idx}]"

    def _is_database_list(self, path, value):
        if path != ["Database"]:
            return False
        return isinstance(value, list)

    def _database_label(self, idx, item):
        if isinstance(item, dict):
            host = item.get("host")
            if host:
                return f"[{idx}] {host}"
        return f"[{idx}]"

    def _is_twotter_users_list(self, path, value):
        if path != ["Twotter", "users"]:
            return False
        return isinstance(value, list)

    def _twotter_user_label(self, idx, item):
        if isinstance(item, dict):
            name = item.get("name")
            if name:
                return f"[{idx}] {name}"
        return f"[{idx}]"

    def _is_quests_list(self, path, value):
        if path != ["Quests"]:
            return False
        return isinstance(value, list)

    def _quests_label(self, idx, item):
        if isinstance(item, dict):
            name = item.get("name")
            if name:
                return f"[{idx}] {name}"
        return f"[{idx}]"

    def _is_kisscord_friends_list(self, path, value):
        if path != ["Kisscord", "friends"]:
            return False
        return isinstance(value, list)

    def _kisscord_friend_label(self, idx, item):
        if isinstance(item, dict):
            name = item.get("name")
            if name:
                return f"[{idx}] {name}"
        return f"[{idx}]"

    def _is_website_templates_list(self, path, value):
        if path != ["WebsiteTemplates"]:
            return False
        return isinstance(value, list)

    def _website_templates_label(self, idx, item):
        if isinstance(item, dict):
            template = item.get("template")
            if template:
                return f"[{idx}] {template}"
        return f"[{idx}]"

    def _is_terminal_packages_list(self, path, value):
        if path != ["Terminal", "installedPackages"]:
            return False
        return isinstance(value, list)

    def _terminal_package_label(self, idx, item):
        if isinstance(item, dict):
            pkg = item.get("pkg")
            if pkg:
                return f"[{idx}] {pkg}"
        return f"[{idx}]"

    def _is_terminal_datalist(self, path, value):
        if path not in (["Terminal", "datalist"], ["Terminal", "dataList"]):
            return False
        return isinstance(value, list)

    def _terminal_datalist_label(self, idx, item):
        if isinstance(item, dict):
            name = item.get("name") or item.get("command")
            input_value = item.get("input")
            if name or input_value:
                parts = []
                if name:
                    parts.append(str(name))
                if input_value:
                    parts.append(str(input_value))
                return " | ".join(parts)
        return f"[{idx}]"

    def _is_edit_allowed(self, path, new_value):
        return True

    def _network_context(self, path):
        if len(path) < 2:
            return None
        if path[0] != "Network":
            return None
        idx = path[1]
        if not isinstance(idx, int):
            return None
        try:
            node = self._get_value(["Network", idx])
        except Exception:
            return None
        if not isinstance(node, dict):
            return None
        node_type = node.get("type")
        if node_type in self.network_types_set:
            return {"type": node_type, "path": ["Network", idx]}
        return None


def main():
    path = None
    if len(sys.argv) > 1:
        path = sys.argv[1]
    root = tk.Tk()
    app = JsonEditor(root, path)
    root.geometry("1000x700")
    root.mainloop()


if __name__ == "__main__":
    main()
