from __future__ import annotations

from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .layout import (
    COL_DATE_START,
    COL_END,
    COL_NAME,
    COL_START,
    ROW_DAY,
    ROW_MONTH,
    ROW_TASK_START,
    ROW_WEEK,
    Layout,
    week_label,
)


HEADER_FILL = PatternFill("solid", fgColor="FFE6E6E6")
BAR_FILLS = {
    0: PatternFill("solid", fgColor="FF1F4E78"),
    1: PatternFill("solid", fgColor="FF4472C4"),
    2: PatternFill("solid", fgColor="FFB4C7E7"),
}
LEVEL_FONTS = {
    0: Font(bold=True),
    1: Font(),
    2: Font(color="FF808080"),
}
HEADER_FONT = Font(bold=True)
CENTER = Alignment(horizontal="center", vertical="center")
LEFT = Alignment(horizontal="left", vertical="center")


def _write_headers(ws: Worksheet, layout: Layout) -> None:
    name_header = ws.cell(row=ROW_DAY, column=COL_NAME, value="タスク名")
    name_header.font = HEADER_FONT
    name_header.alignment = LEFT
    start_header = ws.cell(row=ROW_DAY, column=COL_START, value="開始日")
    start_header.font = HEADER_FONT
    start_header.alignment = CENTER
    end_header = ws.cell(row=ROW_DAY, column=COL_END, value="終了日")
    end_header.font = HEADER_FONT
    end_header.alignment = CENTER

    for r in (ROW_MONTH, ROW_WEEK, ROW_DAY):
        for c in (COL_NAME, COL_START, COL_END):
            ws.cell(row=r, column=c).fill = HEADER_FILL

    prev_month: tuple[int, int] | None = None
    for dc in layout.date_columns:
        d = dc.date
        month_key = (d.year, d.month)
        if month_key != prev_month:
            ws.cell(row=ROW_MONTH, column=dc.col, value=f"{d.year}-{d.month:02d}")
            prev_month = month_key

        if dc.is_week_start:
            ws.cell(
                row=ROW_WEEK,
                column=dc.col,
                value=week_label(d, layout.project.week_start),
            )

        ws.cell(row=ROW_DAY, column=dc.col, value=d.day)

        for r in (ROW_MONTH, ROW_WEEK, ROW_DAY):
            cell = ws.cell(row=r, column=dc.col)
            cell.fill = HEADER_FILL
            cell.alignment = CENTER
            cell.font = HEADER_FONT


def _write_task_rows(ws: Worksheet, layout: Layout) -> None:
    for tr in layout.task_rows:
        task = tr.task
        indent = "  " * task.level
        name_cell = ws.cell(row=tr.row, column=COL_NAME, value=f"{indent}{task.name}")
        name_cell.font = LEVEL_FONTS[task.level]
        name_cell.alignment = LEFT

        if task.start is not None:
            start_cell = ws.cell(row=tr.row, column=COL_START, value=task.start)
            start_cell.number_format = "yyyy-mm-dd"
            start_cell.alignment = CENTER
            start_cell.font = LEVEL_FONTS[task.level]
        if task.end is not None:
            end_cell = ws.cell(row=tr.row, column=COL_END, value=task.end)
            end_cell.number_format = "yyyy-mm-dd"
            end_cell.alignment = CENTER
            end_cell.font = LEVEL_FONTS[task.level]


def _draw_bars(ws: Worksheet, layout: Layout) -> None:
    for tr in layout.task_rows:
        task = tr.task
        if task.start is None or task.end is None:
            continue
        fill = BAR_FILLS[task.level]
        start_col = layout.col_for_date(task.start)
        end_col = layout.col_for_date(task.end)
        for c in range(start_col, end_col + 1):
            ws.cell(row=tr.row, column=c).fill = fill


def _apply_dimensions(ws: Worksheet, layout: Layout) -> None:
    ws.column_dimensions[get_column_letter(COL_NAME)].width = 30
    ws.column_dimensions[get_column_letter(COL_START)].width = 12
    ws.column_dimensions[get_column_letter(COL_END)].width = 12

    for dc in layout.date_columns:
        letter = get_column_letter(dc.col)
        cd = ws.column_dimensions[letter]
        cd.width = 3
        if dc.outline_level > 0:
            cd.outline_level = dc.outline_level
            cd.hidden = False


def _apply_row_outline(ws: Worksheet, layout: Layout) -> None:
    for tr in layout.task_rows:
        if tr.outline_level > 0:
            rd = ws.row_dimensions[tr.row]
            rd.outline_level = tr.outline_level
            rd.hidden = False


def _apply_outline_properties(ws: Worksheet) -> None:
    ws.sheet_properties.outlinePr.summaryBelow = False
    ws.sheet_properties.outlinePr.summaryRight = False


def _freeze_panes(ws: Worksheet) -> None:
    ws.freeze_panes = "D4"


def write_workbook(layout: Layout, output_path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Gantt"

    _apply_outline_properties(ws)
    _write_headers(ws, layout)
    _write_task_rows(ws, layout)
    _draw_bars(ws, layout)
    _apply_dimensions(ws, layout)
    _apply_row_outline(ws, layout)
    _freeze_panes(ws)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
