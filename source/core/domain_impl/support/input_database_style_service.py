"""Database INPUT style helpers for Grades table rendering.

Keeps Database-specific INPUT matrix extraction/rendering in the service layer
so layout iterations do not bloat the main editor module.
"""

import tkinter as tk
from typing import Any


def _matrix_shape_key(matrix_payload: Any) -> tuple[Any, ...]:
    subjects = tuple(matrix_payload.get("subjects", []) or [])
    rows = list(matrix_payload.get("rows", []) or [])
    editable_grid = tuple(
        tuple(bool(cell.get("editable") is True) for cell in list(row.get("cells", []) or []))
        for row in rows
    )
    return (subjects, editable_grid)


def reset_database_render_pool(owner: Any) -> None:
    pool = getattr(owner, "_input_mode_database_pool", None)
    if not isinstance(pool, dict):
        owner._input_mode_database_pool = None
        return
    table = pool.get("table_frame")
    owner._input_mode_database_pool = None
    if table is None:
        return
    try:
        table.destroy()
    except (tk.TclError, RuntimeError, AttributeError):
        return


def _is_live_widget(widget: Any) -> bool:
    if widget is None:
        return False
    try:
        return bool(widget.winfo_exists())
    except (tk.TclError, RuntimeError, AttributeError):
        return False


def suspend_database_render_host(owner: Any, host: Any) -> set[Any]:
    pool = getattr(owner, "_input_mode_database_pool", None)
    if not isinstance(pool, dict):
        return set()
    if pool.get("host") is not host:
        return set()
    table = pool.get("table_frame")
    if not _is_live_widget(table):
        owner._input_mode_database_pool = None
        return set()
    try:
        if table.winfo_manager() == "pack":
            table.pack_forget()
    except (tk.TclError, RuntimeError, AttributeError):
        return set()
    return {table}


def database_pool_children(owner: Any, host: Any) -> set[Any]:
    pool = getattr(owner, "_input_mode_database_pool", None)
    if not isinstance(pool, dict):
        return set()
    if pool.get("host") is not host:
        return set()
    table = pool.get("table_frame")
    if not _is_live_widget(table):
        owner._input_mode_database_pool = None
        return set()
    return {table}


def collect_database_grades_matrix(value: Any, max_rows: Any=40) -> Any:
    # Detect Grades rows from either:
    # 1) direct Database->tables->Grades list, or
    # 2) root Database list containing entries with tables.Grades.
    source_rows = _resolve_grades_rows(value)
    if source_rows is None:
        return None

    first_row = source_rows[0]
    student_cell = first_row.get("student")
    if not isinstance(student_cell, dict) or "value" not in student_cell:
        return None

    subjects = []
    for key, cell in first_row.items():
        if key == "student":
            continue
        if isinstance(cell, dict) and "value" in cell:
            subjects.append(key)
    if not subjects:
        return None

    rows = []
    for idx, row in enumerate(source_rows):
        if len(rows) >= max_rows:
            break
        if not isinstance(row, dict):
            continue
        student_obj = row.get("student", {})
        student_name = ""
        if isinstance(student_obj, dict):
            student_name = str(student_obj.get("value", "") or "")
        row_cells = []
        for subject in subjects:
            cell = row.get(subject, {})
            if not isinstance(cell, dict):
                row_cells.append(
                    {
                        "subject": subject,
                        "value": "",
                        "editable": False,
                        "rel_path": [idx, subject, "value"],
                    }
                )
                continue
            row_cells.append(
                {
                    "subject": subject,
                    "value": cell.get("value"),
                    "editable": bool(cell.get("editable") is True),
                    "rel_path": [idx, subject, "value"],
                    "max_length": cell.get("maxLength"),
                    "value_type": type(cell.get("value")),
                }
            )
        rows.append(
            {
                "row_index": idx,
                "student_name": student_name,
                "cells": row_cells,
            }
        )

    return {"subjects": subjects, "rows": rows}


def _resolve_grades_rows(value):
    if not isinstance(value, list) or not value:
        return None
    if not all(isinstance(item, dict) for item in value):
        return None
    if _looks_like_grades_rows(value):
        return value
    # Root Database node payload: scan database records for tables.Grades list.
    for item in value:
        tables = item.get("tables")
        if not isinstance(tables, dict):
            continue
        grades = tables.get("Grades")
        if _looks_like_grades_rows(grades):
            return grades
    return None


def _looks_like_grades_rows(rows):
    if not isinstance(rows, list) or not rows:
        return False
    if not all(isinstance(row, dict) for row in rows):
        return False
    first_row = rows[0]
    student_cell = first_row.get("student")
    return isinstance(student_cell, dict) and "value" in student_cell


def render_database_grades_matrix(owner: Any, host: Any, normalized_path: Any, matrix_payload: Any) -> Any:
    # Render Concept-1 style matrix: only editable=true cells get input boxes.
    theme = getattr(owner, "_theme", {})
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    panel_bg = theme.get("panel", "#161b24")
    if variant == "KAMUE":
        # KAMUE matching palette for Database INPUT matrix while preserving SIINDBAD layout behavior.
        table_edge = "#6a4697"
        tab_edge = "#8f6ad1"
        header_fg = "#e2cbff"
        student_fg = "#C8A8FF"
        value_fg = "#70e58a"
        plain_fg = "#d6c8e8"
        input_bg = "#1b1230"
        input_edge = "#8a5bc4"
    else:
        table_edge = "#2f5f85"
        tab_edge = "#33cfff"
        header_fg = "#a8c9e6"
        student_fg = "#f2ad5e"
        value_fg = "#62d67a"
        plain_fg = "#b7c2ce"
        input_bg = "#071322"
        input_edge = "#2e8fd4"
    label_family = owner._resolve_font_family(
        ["Tektur SemiBold", "Tektur", "Segoe UI Semibold", "Segoe UI"],
        owner._credit_name_font()[0],
    )
    input_family = owner._resolve_font_family(
        ["Segoe UI", "Bahnschrift", "Segoe UI Semibold"],
        owner._credit_name_font()[0],
    )
    header_size = owner._input_mode_font_size(8, min_size=7, max_size=16)
    student_size = owner._input_mode_font_size(9, min_size=8, max_size=18)
    input_size = owner._input_mode_font_size(8, min_size=7, max_size=16)
    value_size = owner._input_mode_font_size(9, min_size=8, max_size=18)
    style_key = (
        panel_bg,
        table_edge,
        tab_edge,
        header_fg,
        student_fg,
        value_fg,
        plain_fg,
        input_bg,
        input_edge,
        label_family,
        input_family,
        header_size,
        student_size,
        input_size,
        value_size,
    )

    subjects = list(matrix_payload.get("subjects", []) or [])
    rows = list(matrix_payload.get("rows", []) or [])
    shape_key = _matrix_shape_key(matrix_payload)

    pool = getattr(owner, "_input_mode_database_pool", None)
    table_frame = pool.get("table_frame") if isinstance(pool, dict) else None
    reusable = bool(
        isinstance(pool, dict)
        and pool.get("host") is host
        and pool.get("shape_key") == shape_key
        and _is_live_widget(table_frame)
    )
    if not reusable:
        reset_database_render_pool(owner)
        pool = _build_database_matrix_pool(
            owner,
            host,
            subjects,
            rows,
            shape_key,
            panel_bg,
            table_edge,
            tab_edge,
            header_fg,
            label_family,
            header_size,
            student_fg,
            student_size,
            input_bg,
            value_fg,
            input_edge,
            input_family,
            input_size,
            plain_fg,
            value_size,
        )
        owner._input_mode_database_pool = pool

    table_frame = pool.get("table_frame")
    if table_frame is not None:
        try:
            if table_frame.winfo_manager() != "pack":
                table_frame.pack(fill="x", padx=8, pady=(6, 0))
            table_frame.configure(
                bg=panel_bg,
                highlightbackground=table_edge,
            )
        except (tk.TclError, RuntimeError, AttributeError):
            return

    _update_database_matrix_pool(
        owner,
        pool,
        normalized_path,
        rows,
        style_key=style_key,
        panel_bg=panel_bg,
        table_edge=table_edge,
        tab_edge=tab_edge,
        header_fg=header_fg,
        student_fg=student_fg,
        value_fg=value_fg,
        plain_fg=plain_fg,
        input_bg=input_bg,
        input_edge=input_edge,
        label_family=label_family,
        input_family=input_family,
        header_size=header_size,
        student_size=student_size,
        input_size=input_size,
        value_size=value_size,
    )

def _build_database_matrix_pool(
    owner: Any,
    host: Any,
    subjects: list[Any],
    rows: list[Any],
    shape_key: tuple[Any, ...],
    panel_bg: str,
    table_edge: str,
    tab_edge: str,
    header_fg: str,
    label_family: str,
    header_size: int,
    student_fg: str,
    student_size: int,
    input_bg: str,
    value_fg: str,
    input_edge: str,
    input_family: str,
    input_size: int,
    plain_fg: str,
    value_size: int,
) -> dict[str, Any]:
    table_frame = tk.Frame(
        host,
        bg=panel_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=table_edge,
    )
    table_frame.pack(fill="x", padx=8, pady=(6, 0))

    table_frame.grid_columnconfigure(0, minsize=170, weight=0)
    for col_idx in range(1, len(subjects) + 1):
        table_frame.grid_columnconfigure(col_idx, minsize=64, weight=1)

    def _header_tab(parent, text, col, anchor="center", justify="center", sticky="ew", padx=(1, 1)):
        tab = tk.Frame(
            parent,
            bg=panel_bg,
            bd=0,
            highlightthickness=1,
            highlightbackground=tab_edge,
        )
        tab.grid(row=0, column=col, sticky=sticky, padx=padx, pady=(1, 2))
        label = tk.Label(
            tab,
            text=text,
            bg=panel_bg,
            fg=header_fg,
            anchor=anchor,
            justify=justify,
            padx=4 if col == 0 else 2,
            pady=2,
            font=(label_family, header_size, "bold"),
        )
        label.pack(fill="both", expand=True)
        return tab, label

    header_tabs = []
    header_labels = []
    tab, label = _header_tab(
        table_frame,
        "Students",
        0,
        anchor="w",
        justify="left",
        sticky="ew",
        padx=(1, 2),
    )
    header_tabs.append(tab)
    header_labels.append(label)

    for col_idx, subject in enumerate(subjects, start=1):
        tab, label = _header_tab(
            table_frame,
            str(subject),
            col_idx,
            anchor="center",
            justify="center",
            sticky="ew",
            padx=(1, 1),
        )
        header_tabs.append(tab)
        header_labels.append(label)

    row_widgets = []
    for row_idx, row in enumerate(rows, start=1):
        row_frame = tk.Frame(
            table_frame,
            bg=panel_bg,
            bd=0,
            highlightthickness=1,
            highlightbackground=table_edge,
        )
        row_frame.grid(
            row=row_idx,
            column=0,
            columnspan=len(subjects) + 1,
            sticky="ew",
            padx=(1, 1),
            pady=(1, 1),
        )
        row_frame.grid_columnconfigure(0, minsize=170, weight=0)
        for col_idx in range(1, len(subjects) + 1):
            row_frame.grid_columnconfigure(col_idx, minsize=64, weight=1)

        student_name = str(row.get("student_name", "") or "")
        student_var = tk.StringVar(value=student_name)
        student_label = tk.Entry(
            row_frame,
            textvariable=student_var,
            bg=panel_bg,
            fg=student_fg,
            relief="flat",
            bd=0,
            highlightthickness=0,
            readonlybackground=panel_bg,
            justify="left",
            font=(label_family, student_size, "bold"),
            state="readonly",
        )
        student_label.grid(row=0, column=0, sticky="w")
        bind_input_widget = getattr(owner, "_bind_input_context_widget", None)
        if callable(bind_input_widget):
            bind_input_widget(student_label, allow_paste=False)

        cells = list(row.get("cells", []) or [])
        cell_widgets = []
        for col_idx, cell in enumerate(cells, start=1):
            cell_host = tk.Frame(row_frame, bg=panel_bg, bd=0, highlightthickness=0)
            cell_host.grid(row=0, column=col_idx, sticky="nsew", padx=0, pady=2)

            value = cell.get("value")
            value_text = "" if value is None else str(value)
            editable = bool(cell.get("editable") is True)
            if editable:
                var = tk.StringVar(value=value_text)
                entry = tk.Entry(
                    cell_host,
                    textvariable=var,
                    width=5,
                    justify="center",
                    bg=input_bg,
                    fg=value_fg,
                    insertbackground=value_fg,
                    relief="flat",
                    bd=0,
                    highlightthickness=1,
                    highlightbackground=input_edge,
                    highlightcolor=input_edge,
                    font=(input_family, input_size, "bold"),
                )
                # Align editable inputs with non-editable numeric labels in the same row.
                entry.pack(anchor="center", pady=(4, 0), ipady=1)
                bind_input_widget = getattr(owner, "_bind_input_context_widget", None)
                if callable(bind_input_widget):
                    bind_input_widget(entry, allow_paste=True)
                cell_widgets.append(
                    {
                        "editable": True,
                        "host": cell_host,
                        "var": var,
                        "entry": entry,
                    }
                )
            else:
                value_label = tk.Label(
                    cell_host,
                    text=value_text,
                    bg=panel_bg,
                    fg=plain_fg,
                    anchor="center",
                    justify="center",
                    padx=1,
                    pady=4,
                    font=(input_family, value_size, "bold"),
                )
                value_label.pack(anchor="center")
                cell_widgets.append(
                    {
                        "editable": False,
                        "host": cell_host,
                        "label": value_label,
                    }
                )
        row_widgets.append(
            {
                "row_frame": row_frame,
                "student_label": student_label,
                "student_var": student_var,
                "cells": cell_widgets,
            }
        )

    return {
        "host": host,
        "shape_key": shape_key,
        "table_frame": table_frame,
        "header_tabs": header_tabs,
        "header_labels": header_labels,
        "row_widgets": row_widgets,
    }


def _update_database_matrix_pool(
    owner: Any,
    pool: dict[str, Any],
    normalized_path: Any,
    rows: list[Any],
    *,
    style_key: tuple[Any, ...],
    panel_bg: str,
    table_edge: str,
    tab_edge: str,
    header_fg: str,
    student_fg: str,
    value_fg: str,
    plain_fg: str,
    input_bg: str,
    input_edge: str,
    label_family: str,
    input_family: str,
    header_size: int,
    student_size: int,
    input_size: int,
    value_size: int,
) -> None:
    owner._input_mode_field_specs = []
    style_changed = pool.get("style_key") != style_key
    pool["style_key"] = style_key
    header_tabs = list(pool.get("header_tabs", []) or [])
    header_labels = list(pool.get("header_labels", []) or [])
    if style_changed:
        for tab in header_tabs:
            try:
                tab.configure(bg=panel_bg, highlightbackground=tab_edge)
            except (tk.TclError, RuntimeError, AttributeError):
                continue
        for label in header_labels:
            try:
                label.configure(
                    bg=panel_bg,
                    fg=header_fg,
                    font=(label_family, header_size, "bold"),
                )
            except (tk.TclError, RuntimeError, AttributeError):
                continue

    row_widgets = list(pool.get("row_widgets", []) or [])
    for row_widget, row in zip(row_widgets, rows):
        row_frame = row_widget.get("row_frame")
        student_label = row_widget.get("student_label")
        student_var = row_widget.get("student_var")
        cells = list(row_widget.get("cells", []) or [])
        if style_changed:
            try:
                if row_frame is not None:
                    row_frame.configure(bg=panel_bg, highlightbackground=table_edge)
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        student_name = str(row.get("student_name", "") or "")
        try:
            if student_label is not None:
                student_text_changed = row_widget.get("last_student_name") != student_name
                if student_text_changed and student_var is not None:
                    student_var.set(student_name)
                kwargs: dict[str, Any] = {}
                if style_changed:
                    kwargs.update(
                        readonlybackground=panel_bg,
                        fg=student_fg,
                        font=(label_family, student_size, "bold"),
                    )
                if kwargs:
                    student_label.configure(**kwargs)
                row_widget["last_student_name"] = student_name
        except (tk.TclError, RuntimeError, AttributeError):
            pass

        for cell_widget, cell in zip(cells, list(row.get("cells", []) or [])):
            host = cell_widget.get("host")
            if style_changed:
                try:
                    if host is not None:
                        host.configure(bg=panel_bg)
                except (tk.TclError, RuntimeError, AttributeError):
                    pass
            value = cell.get("value")
            value_text = "" if value is None else str(value)
            if bool(cell_widget.get("editable")):
                var = cell_widget.get("var")
                entry = cell_widget.get("entry")
                if var is not None:
                    try:
                        if var.get() != value_text:
                            var.set(value_text)
                    except (tk.TclError, RuntimeError, AttributeError):
                        pass
                if style_changed:
                    try:
                        if entry is not None:
                            entry.configure(
                                bg=input_bg,
                                fg=value_fg,
                                insertbackground=value_fg,
                                highlightbackground=input_edge,
                                highlightcolor=input_edge,
                                font=(input_family, input_size, "bold"),
                            )
                    except (tk.TclError, RuntimeError, AttributeError):
                        pass
                owner._input_mode_field_specs.append(
                    {
                        "rel_path": list(cell.get("rel_path", [])),
                        "abs_path": list(normalized_path) + list(cell.get("rel_path", [])),
                        "initial": value,
                        "type": cell.get("value_type", type(value)),
                        "var": var,
                        "widget": entry,
                    }
                )
                continue
            label = cell_widget.get("label")
            try:
                if label is not None:
                    value_text_changed = cell_widget.get("last_text") != value_text
                    kwargs: dict[str, Any] = {}
                    if value_text_changed:
                        kwargs["text"] = value_text
                    if style_changed:
                        kwargs.update(
                            bg=panel_bg,
                            fg=plain_fg,
                            font=(input_family, value_size, "bold"),
                        )
                    if kwargs:
                        label.configure(**kwargs)
                    cell_widget["last_text"] = value_text
            except (tk.TclError, RuntimeError, AttributeError):
                continue
