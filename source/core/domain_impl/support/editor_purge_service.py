"""Delegated logic extracted from JsonEditor during structural purge."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from core.exceptions import EXPECTED_ERRORS
from core.domain_impl.json import document_io_service
from core.domain_impl.json import json_apply_commit_service
from core.domain_impl.json import json_path_service
from core.domain_impl.json import json_parse_feedback_service
from core.domain_impl.json import json_quoted_item_tail_service
from core.domain_impl.json import json_scalar_tail_service
from core.domain_impl.json import json_validation_feedback_service
from core.domain_impl.json import json_view_service
from core.domain_impl.json import json_diagnostics_service
from core.domain_impl.ui import footer_service
from core.domain_impl.ui import loader_service
from core.domain_impl.ui import toolbar_service
from core.domain_impl.ui import tree_mode_service
from core.domain_impl.ui import tree_policy_service
from core.domain_impl.ui import tree_view_service
from core.domain_impl.ui import ui_build_service
from core.domain_impl.ui import theme_service
from core.domain_impl.infra import runtime_log_service
from core.domain_impl.infra import update_headers_service
from core.domain_impl.infra import update_release_info_service
from core.domain_impl.infra import update_ui_service
from core.domain_impl.infra import windows_runtime_service
from core.domain_impl.infra import input_mode_service
from core.domain_impl.support import crash_offer_service
from core.domain_impl.support import bug_report_cooldown_service
from core.domain_impl.support import error_hook_service
from core.domain_impl.support import error_overlay_service
from core.domain_impl.support import error_service
from core.domain_impl.support import highlight_label_service
from core.domain_impl.json import validation_service

_LOG = logging.getLogger(__name__)


def _startup_wiring_sanity_issues(owner: Any) -> list[str]:
        """Return missing critical symbol paths that previously caused runtime NameError crashes."""
        checks = (
            ("json_diagnostics_service.os", json_diagnostics_service, "os"),
            ("json_diagnostics_service.datetime", json_diagnostics_service, "datetime"),
            ("theme_service.deque", theme_service, "deque"),
            ("editor_purge_service.input_mode_service", sys.modules[__name__], "input_mode_service"),
            ("editor_purge_service.json_path_service", sys.modules[__name__], "json_path_service"),
            ("editor_purge_service.bug_report_cooldown_service", sys.modules[__name__], "bug_report_cooldown_service"),
        )
        issues: list[str] = []
        for label, container, attr in checks:
            if container is None or not hasattr(container, attr):
                issues.append(label)
        return issues


def _run_startup_wiring_sanity_check(owner: Any) -> None:
        """Log and surface startup wiring gaps early so regressions do not fail deep in UI callbacks."""
        issues = _startup_wiring_sanity_issues(owner)
        owner._startup_wiring_sanity_issues = tuple(issues)
        if not issues:
            return
        joined = ", ".join(issues)
        _LOG.warning("startup_wiring_missing_symbols=%s", joined)
        try:
            owner.set_status(f"Startup wiring warning: missing {joined}")
        except EXPECTED_ERRORS:
            return


def _append_find_search_entries(owner: Any, path, value, entries):
        mode_is_input = str(getattr(owner, "_editor_mode", "JSON")).upper() == "INPUT"
        if isinstance(value, dict):
            hidden_keys_getter = getattr(owner, "_hidden_root_tree_keys_for_mode", None)
            hidden_keys = (
                hidden_keys_getter() if callable(hidden_keys_getter) else set(getattr(owner, "HIDDEN_ROOT_TREE_KEYS", set()))
            )
            keys = list(value.keys())
            if isinstance(path, list) and len(path) == 0:
                keys = sorted(
                    keys,
                    key=lambda raw: str(owner._tree_display_label_for_key(raw)).casefold(),
                )
            for key in keys:
                if (
                    isinstance(path, list)
                    and not path
                    and owner._normalize_root_tree_key(key) in hidden_keys
                ):
                    continue
                child_path = path + [key]
                child_text = owner._tree_display_label_for_key(key)
                if tuple(path or []) in (("Typewriter",),):
                    entry_value = value.get(key)
                    if isinstance(entry_value, dict):
                        type_value = entry_value.get("type")
                        if type_value:
                            child_text = str(type_value)
                child_value = value.get(key)
                summary_fn = getattr(owner, "_find_search_value_summary", None)
                summary_text = summary_fn(child_value) if callable(summary_fn) else ""
                searchable_text = f"{child_text} {summary_text}".strip().casefold()
                entries.append((child_path, searchable_text))
                should_recurse = isinstance(child_value, (dict, list)) and len(child_value) > 0
                if (
                    should_recurse
                    and mode_is_input
                    and isinstance(path, list)
                    and not path
                    and owner._normalize_root_tree_key(key) in set(getattr(owner, "INPUT_MODE_NO_EXPAND_ROOT_KEYS", set()))
                ):
                    # INPUT mode keeps locked roots collapsed; Find index should not force deep expansion.
                    should_recurse = False
                if should_recurse:
                    owner._append_find_search_entries(child_path, child_value, entries)
            return

        if isinstance(value, list) and owner._is_network_list(path, value):
            groups = {}
            for idx, item in enumerate(value):
                group = item.get("type") if isinstance(item, dict) else "UNKNOWN"
                groups.setdefault(group, []).append((idx, item))

            ordered_groups = [t for t in owner.network_types if t in groups]
            for group in sorted(g for g in groups.keys() if g not in owner.network_types_set):
                ordered_groups.append(group)

            for group in ordered_groups:
                if tree_policy_service.is_network_group_hidden_for_mode(owner, path, group):
                    continue
                items = groups[group]
                group_label = f"{group} ({len(items)})"
                entries.append((("__group__", list(path), group), group_label.casefold()))
                group_is_locked = (
                    mode_is_input
                    and str(path[0] if path else "").strip().casefold() == "network"
                    and str(group or "").strip().casefold() in set(getattr(owner, "INPUT_MODE_NETWORK_NO_EXPAND_GROUP_KEYS", set()))
                )
                for idx, item in items:
                    label = ""
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
                                if not name and group in ("ROUTER", "DEVICE"):
                                    name = item.get("type")
                            if ip is not None or name is not None:
                                ip_str = "" if ip is None else str(ip)
                                name_str = "" if name is None else str(name)
                                label = f"{ip_str} | {name_str}".strip(" |")
                            else:
                                extra = []
                                if "id" in item:
                                    extra.append(f"id={item['id']}")
                                if "ip" in item:
                                    extra.append(f"ip={item['ip']}")
                                if extra:
                                    label = " ".join(extra)
                        else:
                            extra = []
                            if "id" in item:
                                extra.append(f"id={item['id']}")
                            if "ip" in item:
                                extra.append(f"ip={item['ip']}")
                            if extra:
                                label = " ".join(extra)
                    if not label:
                        label = f"Item {idx + 1}"
                    child_path = path + [idx]
                    summary_fn = getattr(owner, "_find_search_value_summary", None)
                    summary_text = summary_fn(item) if callable(summary_fn) else ""
                    searchable_text = f"{label} {summary_text}".strip().casefold()
                    entries.append((child_path, searchable_text))
                    if not group_is_locked and isinstance(item, (dict, list)) and len(item) > 0:
                        owner._append_find_search_entries(child_path, item, entries)
            return

        if isinstance(value, list):
            labeler = owner._list_labelers.get(tuple(path))
            for idx, item in enumerate(value):
                if labeler:
                    label = labeler(idx, item)
                elif owner._is_database_table_rows_path(path):
                    label = owner._database_table_row_label(idx, item)
                else:
                    label = f"[{idx}]"
                child_path = path + [idx]
                summary_fn = getattr(owner, "_find_search_value_summary", None)
                summary_text = summary_fn(item) if callable(summary_fn) else ""
                searchable_text = f"{label} {summary_text}".strip().casefold()
                entries.append((child_path, searchable_text))
                if isinstance(item, (dict, list)) and len(item) > 0:
                    owner._append_find_search_entries(child_path, item, entries)


def _is_edit_allowed(owner: Any, path, new_value):
        # One-shot bypass used only after explicit "Continue" on highlight warning.
        if bool(getattr(owner, "_allow_highlight_key_change_once", False)):
            owner._allow_highlight_key_change_once = False
            return True
        try:
            current_value = owner._get_value(path)
        except EXPECTED_ERRORS:
            current_value = None
        payload = highlight_label_service.edit_allowed_payload(
            path=path,
            current_value=current_value,
            new_value=new_value,
            find_first_dict_key_change=owner._find_first_dict_key_change,
            format_path_for_display=owner._format_path_for_display,
        )
        if payload.get("allowed", False):
            return True
        owner._error_visual_mode = "guide"
        recommended_name = str(payload.get("recommended_name") or "").strip() or str(
            payload.get("path_label", "highlighted field")
        )
        entered_name = str(payload.get("entered_name") or "").strip()

        def _overlay_autofix():
            restore_index = ""
            try:
                restore_index = str(owner.text.index("insert") or "")
            except EXPECTED_ERRORS:
                restore_index = ""
            try:
                owner._destroy_error_overlay()
            except EXPECTED_ERRORS:
                pass
            try:
                owner._show_value(current_value, path=path)
            except EXPECTED_ERRORS:
                return
            if restore_index:
                try:
                    line_text = str(restore_index).split(".", 1)
                    line_no = max(1, int(line_text[0]))
                    col_no = max(0, int(line_text[1]))
                    max_line = max(1, int(str(owner.text.index("end-1c")).split(".", 1)[0]))
                    line_no = min(line_no, max_line)
                    live_line_text = str(owner._line_text(line_no) or "")
                    col_no = min(col_no, len(live_line_text))
                    restore_index = f"{line_no}.{col_no}"
                    owner.text.mark_set("insert", restore_index)
                    owner.text.see(restore_index)
                except EXPECTED_ERRORS:
                    pass
            try:
                owner.set_status(f'Auto-fixed: restored highlighted field "{recommended_name}".')
            except EXPECTED_ERRORS:
                pass

        def _overlay_continue():
            try:
                owner._destroy_error_overlay()
            except EXPECTED_ERRORS:
                pass
            owner._allow_highlight_key_change_once = True
            try:
                owner.set_status("Warning acknowledged: continuing highlighted field edit.")
            except EXPECTED_ERRORS:
                pass
            try:
                owner.apply_edit()
            except EXPECTED_ERRORS:
                owner._allow_highlight_key_change_once = False

        owner._show_error_overlay(
            "Warning",
            (
                "Warning : Editing Highlighted Columns Could Corrupt Game Data\n\n"
                f"Recommended : {recommended_name}"
            ),
            actions=(
                ("Auto-Fix", _overlay_autofix),
                ("Continue", _overlay_continue),
            ),
        )
        try:
            preferred_index = str(owner.text.index("insert") or "")
        except EXPECTED_ERRORS:
            preferred_index = ""
        # Warning anchor priority:
        # 1) exact changed-key token near caret (for example `"":` after deleting `x`)
        # 2) recommended/entered key fallback lookup
        anchor_index = ""
        if not entered_name:
            try:
                changed_token = '""'
                backward_hit = owner.text.search(
                    changed_token,
                    preferred_index or "insert",
                    stopindex="1.0",
                    nocase=False,
                    backwards=True,
                )
                if backward_hit:
                    anchor_index = str(backward_hit)
                else:
                    forward_hit = owner.text.search(
                        changed_token,
                        preferred_index or "1.0",
                        stopindex="end",
                        nocase=False,
                    )
                    if forward_hit:
                        anchor_index = str(forward_hit)
            except EXPECTED_ERRORS:
                anchor_index = ""
        try:
            if not anchor_index:
                anchor_index = owner._find_lock_anchor_index(recommended_name, preferred_index=preferred_index) or ""
        except EXPECTED_ERRORS:
            anchor_index = ""
        if not anchor_index and entered_name:
            try:
                anchor_index = owner._find_lock_anchor_index(entered_name, preferred_index=preferred_index) or ""
            except EXPECTED_ERRORS:
                anchor_index = ""
        if not anchor_index:
            anchor_index = preferred_index or "1.0"
        try:
            owner._error_focus_index = anchor_index
            owner._position_error_overlay(owner._line_number_from_index(anchor_index) or 1)
        except EXPECTED_ERRORS:
            pass
        try:
            status_text = "Warning: highlighted field key change detected."
            if entered_name:
                status_text = f'Warning: highlighted key "{entered_name}" differs from "{recommended_name}".'
            owner.set_status(status_text)
        except EXPECTED_ERRORS:
            pass
        return False


def _maybe_restore_locked_parse_error(owner: Any, path, diag, exc=None):
        # Parse-error lock handoff: key-quote parse failures on protected keys should restore via lock flow.
        note = str((diag or {}).get("note") or "").strip().lower()
        parse_lock_notes = {
            "missing_key_quote_before_colon",
            "symbol_wrong_property_key_symbol",
            "symbol_wrong_property_quote_char",
        }
        if note not in parse_lock_notes:
            return False
        use_path = list(path or [])
        policy = highlight_label_service.lock_policy_for_path(use_path)
        if policy is None:
            return False
        field_name = owner._locked_field_name_from_parse_diag(use_path, diag)
        if not field_name:
            return False
        try:
            insert_line = owner._line_number_from_index(owner.text.index("insert")) or 0
        except EXPECTED_ERRORS:
            insert_line = 0
        try:
            insert_line_text = str(owner._line_text(int(insert_line)) or "") if insert_line else ""
        except EXPECTED_ERRORS:
            insert_line_text = ""
        try:
            diag_line = int((diag or {}).get("line") or 0)
        except EXPECTED_ERRORS:
            diag_line = 0
        try:
            parse_line = int(getattr(exc, "lineno", 0) or 0)
        except EXPECTED_ERRORS:
            parse_line = 0
        if parse_line and diag_line and int(parse_line) != int(diag_line):
            return False
        if insert_line and diag_line and int(insert_line) != int(diag_line):
            return False
        if insert_line and diag_line and abs(int(insert_line) - int(diag_line)) > 1:
            return False
        if diag_line and not owner._diag_line_mentions_locked_field(diag_line, field_name):
            return False
        if diag_line:
            try:
                diag_line_text = str(owner._line_text(diag_line) or "")
            except EXPECTED_ERRORS:
                diag_line_text = ""
            has_key_quote_issue = False
            try:
                has_key_quote_issue = bool(
                    owner._line_has_missing_key_quote_before_colon(diag_line_text)
                    or owner._line_has_property_key_invalid_escape(diag_line_text)
                )
            except EXPECTED_ERRORS:
                has_key_quote_issue = False
            if not has_key_quote_issue:
                return False
            line_field = owner._extract_key_name_from_diag_line(diag_line_text)
            if line_field and str(line_field).casefold() != str(field_name).casefold():
                return False
        try:
            insert_has_key_quote_issue = bool(
                owner._line_has_missing_key_quote_before_colon(insert_line_text)
                or owner._line_has_property_key_invalid_escape(insert_line_text)
            )
        except EXPECTED_ERRORS:
            insert_has_key_quote_issue = False
        if not insert_has_key_quote_issue:
            return False
        insert_field = owner._extract_key_name_from_diag_line(insert_line_text)
        if insert_field and str(insert_field).casefold() != str(field_name).casefold():
            return False
        try:
            current_value = owner._get_value(use_path)
        except EXPECTED_ERRORS:
            return False

        try:
            previous_insert = owner.text.index("insert")
        except EXPECTED_ERRORS:
            previous_insert = "1.0"
        owner._show_value(current_value, path=use_path)
        owner._clear_json_error_highlight()
        owner._error_visual_mode = "guide"
        owner._show_error_overlay(
            "Not editable",
            f'Locked: "{field_name}" is a protected field. Line restored.',
        )
        anchor_index = owner._find_lock_anchor_index(field_name, preferred_index=previous_insert)
        if not anchor_index:
            try:
                anchor_index = str(previous_insert or owner.text.index("insert"))
            except EXPECTED_ERRORS:
                anchor_index = "1.0"
        owner._error_focus_index = anchor_index
        try:
            owner.text.mark_set("insert", anchor_index)
            owner.text.see(anchor_index)
        except EXPECTED_ERRORS:
            pass
        try:
            anchor_line = owner._line_number_from_index(anchor_index) or 1
            owner._position_error_overlay(anchor_line)
        except EXPECTED_ERRORS:
            pass
        try:
            owner._tag_json_locked_key_occurrences(field_name)
        except EXPECTED_ERRORS:
            pass
        try:
            owner.set_status(
                str(policy.get("status_restored") or "Auto-fixed: protected field restored.")
            )
        except EXPECTED_ERRORS:
            pass
        try:
            log_line = int((diag or {}).get("line") or 1)
            marker = type("E", (), {"msg": "Locked parse edit restored", "lineno": log_line, "colno": 1})
            owner._log_json_error(marker, log_line, note="locked_parse_auto_restore")
        except EXPECTED_ERRORS:
            pass
        return True


def _apply_input_edit(owner: Any):
        item_id = owner.tree.focus()
        if not item_id:
            owner._log_input_mode_apply_trace("no_selection", [], 0)
            messagebox.showwarning("No selection", "Select a node in the tree.")
            return
        tree_path = owner.item_to_path.get(item_id, [])
        if isinstance(tree_path, tuple) and tree_path[0] == "__group__":
            _, list_path, _group = tree_path
            path = list(list_path or [])
        else:
            path = list(getattr(owner, "_input_mode_current_path", []) or [])
            if not path:
                path = tree_path
        if isinstance(path, tuple) and path[0] == "__group__":
            _, list_path, _group = path
            path = list(list_path or [])
        if owner._is_input_mode_category_disabled(path):
            owner._log_input_mode_apply_trace("disabled_category", path, 0)
            messagebox.showwarning("Not editable", owner.INPUT_MODE_DISABLED_CATEGORY_MESSAGE)
            return
        specs = list(getattr(owner, "_input_mode_field_specs", []) or [])
        owner._log_input_mode_apply_trace("start", path, len(specs))
        if not specs:
            owner._log_input_mode_apply_trace("no_fields", path, 0)
            messagebox.showwarning("No fields", "No editable scalar fields for this node.")
            return
        value = owner._get_value(path)
        working = input_mode_service.deep_copy_json_compatible(value)
        working_root = input_mode_service.deep_copy_json_compatible(getattr(owner, "data", {}))
        try:
            for spec in specs:
                coerced = owner._coerce_input_field_value(spec)
                abs_path = list(spec.get("abs_path", []) or [])
                rel_path = list(spec.get("rel_path", []))
                if abs_path:
                    owner._set_nested_value(working_root, abs_path, coerced)
                    if (
                        isinstance(path, list)
                        and len(abs_path) >= len(path)
                        and abs_path[: len(path)] == path
                    ):
                        local_rel = abs_path[len(path) :]
                        if local_rel:
                            owner._set_nested_value(working, local_rel, coerced)
                        else:
                            working = coerced
                elif rel_path:
                    owner._set_nested_value(working, rel_path, coerced)
                    target_abs = list(path or []) + rel_path
                    owner._set_nested_value(working_root, target_abs, coerced)
                else:
                    working = coerced
                    if not path:
                        working_root = coerced
                    else:
                        owner._set_nested_value(working_root, list(path), coerced)
        except ValueError as exc:
            owner._log_input_mode_edit_issue(path, exc)
            owner._log_input_mode_apply_trace("value_error", path, len(specs))
            messagebox.showwarning("Invalid Entry", f"Could not apply INPUT edits: {exc}")
            return

        changed = working != value
        owner.data = working_root
        owner._reset_find_state()
        owner._log_input_mode_apply_result(path, changed)
        owner._log_input_mode_apply_trace("applied", path, len(specs), changed=changed)
        if owner._is_bank_input_style_path(path):
            owner._input_mode_last_render_item = item_id
            owner._input_mode_last_render_path_key = owner._input_mode_path_key(path)
            owner._input_mode_force_refresh = False
        else:
            owner._input_mode_force_refresh = True
            owner._populate_children(item_id)
            owner.on_select(None)
        owner.set_status("Edited")


def apply_edit(owner: Any):
        action = "auto_apply" if owner._auto_apply_in_progress else "apply_edit"
        owner._begin_diag_action(action)
        item_id = owner.tree.focus()
        if not item_id:
            messagebox.showwarning("No selection", "Select a node in the tree.")
            return
        path = owner.item_to_path.get(item_id, [])
        mode = str(getattr(owner, "_editor_mode", "JSON")).upper()
        if isinstance(path, tuple) and path[0] == "__group__" and mode != "INPUT":
            messagebox.showwarning("Not editable", "Select a specific item to edit.")
            return
        if mode == "INPUT":
            owner._apply_input_edit()
            return

        raw = owner.text.get("1.0", "end").strip()
        is_valid_input, input_reason = validation_service.validate_editor_text_payload(raw)
        if not is_valid_input:
            owner._show_error_overlay("Invalid Entry", input_reason)
            return
        try:
            new_value = json.loads(raw)
        except EXPECTED_ERRORS as exc:
            json_parse_feedback_service.handle_apply_parse_error(owner, exc, list(path) if isinstance(path, tuple) else path)
            return
        owner._clear_json_error_highlight()

        spacing_issue = owner._find_json_spacing_issue()
        if json_validation_feedback_service.show_spacing_issue(owner, spacing_issue):
            return

        email_validation = owner._find_invalid_email_in_value(path, new_value)
        if json_validation_feedback_service.show_email_issue(
            owner,
            email_validation,
            log_issue=True,
        ):
            return

        phone_issue = owner._find_phone_format_issue()
        if json_validation_feedback_service.show_phone_issue(
            owner,
            phone_issue,
            log_issue=True,
        ):
            return

        if not owner._is_json_edit_allowed(path, new_value, show_feedback=True, auto_restore=True):
            return
        owner._destroy_error_overlay()
        owner._error_visual_mode = "guide"
        if not owner._is_edit_allowed(path, new_value):
            return
        json_apply_commit_service.commit_json_edit(owner, item_id, path, new_value)


def _set_startup_loader_bar_fill(fill_widget, pct):
        if fill_widget is None:
            return
        payload = fill_widget
        if isinstance(payload, dict):
            track = payload.get("track")
            fill_label = payload.get("widget")
            owner = payload.get("owner")
            fill_color = payload.get("color", "#4f90bf")
            if (
                track is None
                or fill_label is None
                or owner is None
                or not track.winfo_exists()
                or not fill_label.winfo_exists()
            ):
                return
            fill_w, fill_h = loader_service.compute_loader_fill_dimensions(
                track.winfo_width(),
                track.winfo_height(),
                pct,
            )
            if fill_w <= 0:
                fill_label.place_forget()
                payload["last_w"] = 0
                return
            # NOTE: Keep fill updates lightweight; per-frame image redraws caused visible loader hitching.
            last_color = str(payload.get("last_color", ""))
            if last_color != str(fill_color):
                fill_label.configure(bg=fill_color, image="", text="")
                fill_label.image = None
                payload["last_color"] = str(fill_color)
            last_w = int(payload.get("last_w", -1) or -1)
            if last_w != fill_w or not bool(fill_label.winfo_ismapped()):
                fill_label.place(x=1, y=1, width=fill_w, height=fill_h)
                payload["last_w"] = fill_w
            return
        if not fill_widget.winfo_exists():
            return
        track = fill_widget.master
        if track is None or not track.winfo_exists():
            return
        fill_w, fill_h = loader_service.compute_loader_fill_dimensions(
            track.winfo_width(),
            track.winfo_height(),
            pct,
        )
        fill_widget.place(x=1, y=1, width=max(0, fill_w), height=max(1, fill_h))


def _show_live_error_feedback(owner: Any):
        item_id = owner.tree.focus()
        if not item_id:
            return
        path = owner.item_to_path.get(item_id, [])
        if isinstance(path, tuple) and path and path[0] == "__group__":
            return
        raw = owner.text.get("1.0", "end").strip()
        try:
            new_value = json.loads(raw)
        except EXPECTED_ERRORS as exc:
            json_parse_feedback_service.handle_live_parse_error(owner, exc, list(path) if isinstance(path, tuple) else path)
            return

        spacing_issue = owner._find_json_spacing_issue()
        if json_validation_feedback_service.show_spacing_issue(owner, spacing_issue):
            return

        email_validation = owner._find_invalid_email_in_value(path, new_value)
        if json_validation_feedback_service.show_email_issue(
            owner,
            email_validation,
            log_issue=False,
        ):
            return

        phone_issue = owner._find_phone_format_issue()
        if json_validation_feedback_service.show_phone_issue(
            owner,
            phone_issue,
            log_issue=False,
        ):
            return

        if not owner._is_json_edit_allowed(path, new_value, show_feedback=True):
            return


def export_hhsave(owner: Any):
        default_ext = ".hhsav"
        initialfile = None
        if owner.path:
            base = os.path.basename(owner.path)
            name, ext = os.path.splitext(base)
            if ext.lower() == ".hhsav":
                default_ext = ".hhsav"
                initialfile = base
            else:
                initialfile = f"{name}{default_ext}"
        path = filedialog.asksaveasfilename(
            title=str(getattr(owner, "EXPORT_HHSAV_DIALOG_TITLE", "Export As .hhsav (gzip)")),
            defaultextension=default_ext,
            filetypes=[("HackHub Save (.hhsav)", "*.hhsav")],
            initialfile=initialfile,
        )
        if not path:
            return
        if not path.lower().endswith(".hhsav"):
            path += default_ext
        try:
            payload = document_io_service.build_compact_json_bytes(owner.data)
            document_io_service.export_hhsav_bytes(
                payload,
                path,
                owner._commit_file_to_destination_with_retries,
            )
        except EXPECTED_ERRORS as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        owner.set_status(str(getattr(owner, "STATUS_EXPORTED_HHSAV", "Exported .hhsav")))


def _apply_json_view_key_highlights(owner: Any, path, line_limit=None):
        if str(getattr(owner, "_editor_mode", "JSON")).upper() != "JSON":
            return
        owner._tag_json_brace_tokens(line_limit=line_limit)
        owner._tag_json_boolean_literals(line_limit=line_limit)
        owner._tag_json_property_keys(line_limit=line_limit)
        use_path = list(path or [])
        xy_keys = ("x", "y") if len(use_path) == 1 else ()
        dimension_keys = ("width", "height")
        locked_path = bool(highlight_label_service.is_locked_field_path(use_path))
        locked_fields = tuple(highlight_label_service.locked_highlight_fields_for_path(use_path))
        if not locked_path:
            if owner._should_batch_tag_locked_keys(locked_fields):
                owner._tag_json_key_occurrences_batch(locked_fields, xy_key_names=xy_keys, line_limit=line_limit)
            else:
                for coord_key in xy_keys:
                    owner._tag_json_xy_key_occurrences(coord_key)
                for field_name in locked_fields:
                    owner._tag_json_locked_key_occurrences(field_name)
        for dim_key in dimension_keys:
            owner._tag_json_xy_key_occurrences(dim_key)
        owner._tag_json_string_value_literals(line_limit=line_limit)


def _apply_startup_loader_title_variant(owner: Any):
        prefix = getattr(owner, "_startup_loader_title_prefix_label", None)
        if prefix is None or not prefix.winfo_exists():
            return
        suffix = getattr(owner, "_startup_loader_title_suffix_label", None)
        variant = loader_service.normalize_title_variant(
            getattr(owner, "_startup_loader_title_variant", "SIINDBAD")
        )
        owner._startup_loader_title_variant = variant
        try:
            prefix.configure(
                text=variant,
                fg=owner._startup_loader_title_color_for_variant(variant),
            )
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        if suffix is not None and suffix.winfo_exists():
            try:
                suffix.configure(text=" SHELL SYSTEM SYNC")
            except (tk.TclError, RuntimeError, AttributeError):
                pass


def _tick_startup_loader_title(owner: Any):
        overlay = getattr(owner, "_startup_loader_overlay", None)
        if overlay is None or not overlay.winfo_exists():
            return
        prefix = getattr(owner, "_startup_loader_title_prefix_label", None)
        if prefix is None or not prefix.winfo_exists():
            return
        current = getattr(owner, "_startup_loader_title_variant", "SIINDBAD")
        owner._startup_loader_title_variant = loader_service.next_title_variant(current)
        owner._apply_startup_loader_title_variant()
        root = getattr(owner, "root", None)
        if root is None:
            return
        after_id = getattr(owner, "_startup_loader_title_after_id", None)
        if after_id:
            try:
                root.after_cancel(after_id)
            except (tk.TclError, RuntimeError, ValueError):
                pass
        cycle_ms = max(2200, int(getattr(owner, "_startup_loader_title_cycle_ms", 4200) or 4200))
        owner._startup_loader_title_after_id = root.after(cycle_ms, owner._tick_startup_loader_title)


def _install_update(owner: Any, new_path):
        exe_path = os.path.abspath(sys.executable)
        current_pid = os.getpid()
        return windows_runtime_service.install_update(
            new_path=new_path,
            exe_path=exe_path,
            current_pid=current_pid,
            asset_name=str(getattr(owner, "GITHUB_ASSET_NAME", "")).strip(),
            start_hidden_process_fn=owner._start_hidden_process,
            schedule_root_destroy_fn=lambda delay_ms: owner.root.after(int(delay_ms), owner.root.destroy),
            ps_escape_fn=owner._ps_escape,
            restart_notice_ms=max(
                1200,
                int(getattr(owner, "_update_restart_notice_ms", 4200) or 4200),
            ),
        )


def _ask_themed_update_confirm(owner: Any, title, message, include_startup_toggle=False):
        startup_state = None
        startup_callback = None
        if bool(include_startup_toggle):
            startup_state = bool(getattr(owner, "_startup_update_check_enabled", False))
            startup_callback = owner._set_startup_update_check_enabled
        return update_ui_service.show_themed_update_confirm(
            owner,
            title,
            message,
            tk=tk,
            messagebox=messagebox,
            startup_check_state=startup_state,
            on_startup_check_change=startup_callback,
        )


def _locked_field_name_from_parse_diag(owner: Any, path, diag):
        use_path = list(path or [])
        if highlight_label_service.is_locked_field_path(use_path) and use_path:
            return str(use_path[-1] or "").strip()
        locked_fields = tuple(highlight_label_service.locked_highlight_fields_for_path(use_path))
        if not locked_fields:
            return ""
        for key in ("after", "before"):
            field_name = owner._extract_key_name_from_diag_line((diag or {}).get(key))
            if not field_name:
                continue
            for locked_name in locked_fields:
                if str(locked_name).casefold() == str(field_name).casefold():
                    return str(locked_name)
        return ""


def _show_themed_update_info(owner: Any, title, message, include_startup_toggle=False):
        startup_state = None
        startup_callback = None
        if bool(include_startup_toggle):
            startup_state = bool(getattr(owner, "_startup_update_check_enabled", False))
            startup_callback = owner._set_startup_update_check_enabled
        update_ui_service.show_themed_update_info(
            owner,
            title,
            message,
            tk=tk,
            messagebox=messagebox,
            startup_check_state=startup_state,
            on_startup_check_change=startup_callback,
        )


def _handle_threading_excepthook(owner: Any, args):
        exc_type, exc_value, exc_tb = error_hook_service.resolve_thread_exception_args(args)
        owner._handle_unhandled_exception(
            "threading.excepthook",
            exc_type,
            exc_value,
            exc_tb,
        )
        error_hook_service.forward_previous_threading_hook(
            prev=getattr(owner, "_prev_threading_excepthook", None),
            current_handler=owner._handle_threading_excepthook,
            args=args,
            expected_errors=EXPECTED_ERRORS,
        )


def _apply_json_view_value_highlights(owner: Any, path):
        if str(getattr(owner, "_editor_mode", "JSON")).upper() != "JSON":
            return
        use_path = list(path or [])
        if highlight_label_service.is_locked_field_path(use_path):
            return
        for rule in highlight_label_service.locked_highlight_value_rules_for_path(use_path):
            field_name = str(rule.get("field") or "").strip()
            if not field_name:
                continue
            ignore_case = bool(rule.get("ignore_case", False))
            for literal in tuple(rule.get("values") or ()):
                owner._tag_json_locked_value_occurrences(field_name, literal, ignore_case=ignore_case)


def load_file(owner: Any, path):
        try:
            owner.data = document_io_service.load_document(path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
            messagebox.showerror("Load failed", str(exc))
            return

        owner.path = path
        owner.root.title(
            f"SIINDBAD's HackHub Editor - {os.path.basename(path)} - v{owner.APP_VERSION}"
        )
        owner._rebuild_tree()
        schedule_router_prewarm = getattr(owner, "_schedule_router_input_prewarm", None)
        if callable(schedule_router_prewarm):
            schedule_router_prewarm()
        owner.set_status(str(getattr(owner, "STATUS_LOADED", "Loaded")))


def _current_overlay_suggestion(owner: Any):
        overlay = getattr(owner, "error_overlay", None)
        try:
            has_overlay = bool(overlay is not None and overlay.winfo_exists())
        except EXPECTED_ERRORS:
            has_overlay = False
        line_no = owner._current_error_line_number()
        return error_service.build_overlay_suggestion_payload(
            has_overlay=has_overlay,
            message=getattr(owner, "_last_error_overlay_message", ""),
            line_no=line_no,
        )


def _siindbad_effective_style(owner: Any):
        style_map = getattr(owner, "_toolbar_style_variant_by_theme", None)
        if not isinstance(style_map, dict):
            style_map = {"SIINDBAD": "B", "KAMUE": "B"}
            owner._toolbar_style_variant_by_theme = style_map
        return toolbar_service.resolve_siindbad_effective_style(
            style_focus=getattr(owner, "_siindbad_style_focus", ""),
            show_toolbar_variant_controls=getattr(owner, "_show_toolbar_variant_controls", False),
            app_theme_variant=getattr(owner, "_app_theme_variant", "SIINDBAD"),
            style_map=style_map,
        )


def _handle_sys_excepthook(owner: Any, exc_type, exc_value, exc_tb):
        owner._handle_unhandled_exception("sys.excepthook", exc_type, exc_value, exc_tb)
        error_hook_service.forward_previous_sys_hook(
            prev=getattr(owner, "_prev_sys_excepthook", None),
            current_handler=owner._handle_sys_excepthook,
            exc_type=exc_type,
            exc_value=exc_value,
            exc_tb=exc_tb,
            expected_errors=EXPECTED_ERRORS,
        )


def save_file(owner: Any):
        if not owner.path:
            return owner.save_file_as()
        try:
            payload = document_io_service.build_pretty_json_payload(owner.data)
            owner._write_text_file_atomic(owner.path, payload, encoding="utf-8")
        except EXPECTED_ERRORS as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        owner.set_status(str(getattr(owner, "STATUS_SAVED", "Saved")))


def _offer_crash_report_if_available(owner: Any):
        if not bool(getattr(owner, "_startup_wiring_checked", False)):
            owner._startup_wiring_checked = True
            _run_startup_wiring_sanity_check(owner)
        owner._crash_report_offer_after_id = None
        if not crash_offer_service.should_offer_crash_report_for_process(env=os.environ):
            return
        payload = owner._pending_crash_report_payload()
        if not payload:
            return
        crash_offer_service.mark_crash_report_prompted_for_process()
        crash_offer_service.offer_crash_report_if_available(
            payload=payload,
            ui_call=owner._ui_call,
            askyesno_func=messagebox.askyesno,
            write_crash_prompt_state=owner._write_crash_prompt_state,
            open_bug_report_dialog=owner._open_bug_report_dialog,
        )


def _footer_visual_spec(owner: Any):
        mode = owner._footer_style_variant()
        spec = footer_service.footer_visual_spec(mode)
        return {
            "label_font": (owner._preferred_mono_family(), 9, "bold"),
            "chip_font": owner._footer_badge_chip_font(),
            **dict(spec),
        }


def _next_startup_loader_line(owner: Any, ready=False):
        pool_attr = "_startup_loader_line_pool_ready" if ready else "_startup_loader_line_pool_loading"
        line, next_pool = loader_service.pop_startup_loader_line(
            ready=ready,
            pool=getattr(owner, pool_attr, []),
        )
        setattr(owner, pool_attr, next_pool)
        return line


def _bug_report_submit_cooldown_remaining(owner: Any, now_monotonic=None):
        now_val = time.monotonic() if now_monotonic is None else float(now_monotonic)
        return bug_report_cooldown_service.submit_cooldown_remaining(
            last_submit_monotonic=getattr(owner, "_last_bug_report_submit_monotonic", 0.0),
            cooldown_seconds=getattr(owner, "BUG_REPORT_SUBMIT_COOLDOWN_SECONDS", 45),
            now_monotonic=now_val,
        )


def _fix_invalid_tail_after_quoted_item(owner: Any, line_text, lineno=None):
        next_line = owner._next_non_empty_line_number(lineno or 1) if lineno else None
        next_text = owner._line_text(next_line) if next_line else ""
        return json_quoted_item_tail_service.fix_invalid_tail_after_quoted_item(
            line_text=line_text,
            next_non_empty_line_text=next_text,
        )


def _fix_invalid_trailing_symbols_after_string_value(owner: Any, line_text, lineno=None):
        next_line = owner._next_non_empty_line_number(lineno or 1) if lineno else None
        next_text = owner._line_text(next_line) if next_line else ""
        return json_scalar_tail_service.fix_invalid_trailing_symbols_after_string_value(
            line_text=line_text,
            next_non_empty_line_text=next_text,
        )


def _show_json_no_file_message(owner: Any):
        text = getattr(owner, "text", None)
        if text is None:
            return
        owner._set_json_text_editable(True)
        owner._clear_json_lock_highlight()
        json_view_service.show_json_no_file_message(text)


def _selected_tree_path_text(owner: Any):
        try:
            item_id = owner.tree.focus()
        except (RuntimeError, tk.TclError, AttributeError):
            item_id = None
        return tree_view_service.selected_tree_path_text(item_id, owner.item_to_path)


def _build_input_mode_panel(owner: Any, parent, scroll_style):
        result = ui_build_service.build_input_mode_panel(owner, parent, scroll_style, tk=tk, ttk=ttk)
        owner._bind_input_mode_mousewheel()
        return result


def _fetch_latest_release_info(owner: Any):
        url = owner._latest_release_api_url()
        raw = owner._download_bytes_with_retries(url)
        return update_release_info_service.parse_latest_release_info(raw)


def _apply_tree_mode_style(owner: Any, mode=None):
        use_mode = str(mode or getattr(owner, "_editor_mode", "JSON")).upper()
        tree_mode_service.apply_tree_mode(owner, use_mode)


def _download_headers(owner: Any):
        token = owner._update_token_value()
        return update_headers_service.download_headers(token)


def _mark_bug_report_submit_now(owner: Any, now_monotonic=None):
        now_val = time.monotonic() if now_monotonic is None else float(now_monotonic)
        owner._last_bug_report_submit_monotonic = bug_report_cooldown_service.mark_submit_now(now_val)


def _read_diag_log_tail(owner: Any, max_chars=8000):
        path = owner._diag_log_path()
        return runtime_log_service.read_text_file_tail(path, max_chars)


def _set_value(owner: Any, path, new_value):
        owner.data = json_path_service.set_value(owner.data, path, new_value)
        owner._reset_find_state()


def _show_error_overlay(owner: Any, title, message, actions=None):
        owner._error_overlay_actions = tuple(actions or ()) or None
        error_overlay_service.show_error_overlay(owner, title, message)
