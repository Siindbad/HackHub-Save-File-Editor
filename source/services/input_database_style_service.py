"""Database INPUT style helpers for Grades table rendering.

Keeps Database-specific INPUT matrix extraction/rendering in the service layer
so layout iterations do not bloat the main editor module.
"""

import tkinter as tk


def collect_database_grades_matrix(value, max_rows=40):
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


def render_database_grades_matrix(owner, host, normalized_path, matrix_payload):
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

    table_frame = tk.Frame(
        host,
        bg=panel_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=table_edge,
    )
    table_frame.pack(fill="x", padx=8, pady=(6, 0))

    subjects = list(matrix_payload.get("subjects", []) or [])
    rows = list(matrix_payload.get("rows", []) or [])

    # Keep student labels untouched while reducing matrix gap so right-most subjects stay visible.
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
            font=(label_family, 8, "bold"),
        )
        label.pack(fill="both", expand=True)

    _header_tab(
        table_frame,
        "Students",
        0,
        anchor="w",
        justify="left",
        sticky="ew",
        padx=(1, 2),
    )

    for col_idx, subject in enumerate(subjects, start=1):
        _header_tab(
            table_frame,
            str(subject),
            col_idx,
            anchor="center",
            justify="center",
            sticky="ew",
            padx=(1, 1),
        )

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
        student_label = tk.Label(
            row_frame,
            text=student_name,
            bg=panel_bg,
            fg=student_fg,
            anchor="w",
            justify="left",
            padx=4,
            pady=4,
            font=(label_family, 9, "bold"),
        )
        student_label.grid(row=0, column=0, sticky="w")

        cells = list(row.get("cells", []) or [])
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
                    font=(input_family, 8, "bold"),
                )
                # Align editable inputs with non-editable numeric labels in the same row.
                entry.pack(anchor="center", pady=(4, 0), ipady=1)
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
                    font=(input_family, 9, "bold"),
                )
                value_label.pack(anchor="center")
