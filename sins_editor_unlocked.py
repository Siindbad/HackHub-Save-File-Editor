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
    APP_VERSION = "1.0.0"
    GITHUB_OWNER = "Siindbad"
    GITHUB_REPO = "HackHub-Save-File-Editor"
    GITHUB_ASSET_NAME = "sins_editor_unlocked.exe"
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
        self.hidden_keys = set()

        self._build_ui()
        if path:
            self.load_file(path)

    def _build_ui(self):
        self._apply_dark_theme()

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
        ttk.Button(top, text="Update", command=self.check_for_updates_manual).pack(
            side="left", padx=(6, 0)
        )

        find_frame = ttk.Frame(top)
        find_frame.pack(side="left", padx=(12, 0))
        ttk.Label(find_frame, text="Find:").pack(side="left", padx=(0, 4))
        self.find_entry = ttk.Entry(find_frame, width=24)
        self.find_entry.pack(side="left")
        ttk.Button(find_frame, text="Find Next", command=self.find_next).pack(side="left", padx=(6, 0))
        self.find_entry.bind("<Return>", self.find_next)

        self.status = ttk.Label(top, text="")
        self.status.pack(side="right")

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
        lines = [
            "@echo off",
            "setlocal",
            "set EXE_NAME=" + exe_name,
            "set EXE_PATH=" + exe_path,
            "set NEW_PATH=" + new_path,
            ":loop",
            "tasklist /FI \"IMAGENAME eq %EXE_NAME%\" | find /I \"%EXE_NAME%\" >nul",
            "if not errorlevel 1 (timeout /t 1 >nul & goto loop)",
            "move /Y \"%NEW_PATH%\" \"%EXE_PATH%\" >nul",
            "start \"\" \"%EXE_PATH%\"",
            "del \"%~f0\"",
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

    def set_status(self, msg):
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
            messagebox.showerror("Invalid JSON", str(exc))
            return

        if not self._is_edit_allowed(path, new_value):
            return

        self._set_value(path, new_value)

        # Refresh subtree
        self._populate_children(item_id)
        self.set_status("Edited")

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
