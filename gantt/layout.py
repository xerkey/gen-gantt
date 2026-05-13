from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .loader import Project, Task


COL_ROLE = 1
COL_ASSIGNEE = 2
COL_NAME = 3
COL_START = 4
COL_END = 5
COL_DATE_START = 6

ROW_MONTH = 1
ROW_WEEK = 2
ROW_DAY = 3
ROW_TASK_START = 4


@dataclass
class DateColumn:
    date: date
    col: int
    outline_level: int
    is_month_start: bool
    is_week_start: bool


@dataclass
class TaskRow:
    task: Task
    row: int
    outline_level: int


@dataclass
class Layout:
    project: Project
    date_columns: list[DateColumn]
    task_rows: list[TaskRow]

    @property
    def total_columns(self) -> int:
        return COL_DATE_START + len(self.date_columns) - 1

    @property
    def total_rows(self) -> int:
        return ROW_TASK_START + len(self.task_rows) - 1

    def col_for_date(self, d: date) -> int:
        idx = (d - self.project.start).days
        if idx < 0 or idx >= len(self.date_columns):
            raise IndexError(f"Date {d} is outside project range")
        return self.date_columns[idx].col


def _is_week_start(d: date, week_start: str) -> bool:
    if week_start == "monday":
        return d.weekday() == 0
    return d.weekday() == 6


def week_label(d: date, week_start: str) -> str:
    if week_start == "monday":
        wk = d.isocalendar()[1]
    else:
        wk = (d + timedelta(days=1)).isocalendar()[1]
    return f"W{wk}"


def _build_date_columns(project: Project) -> list[DateColumn]:
    cols: list[DateColumn] = []
    d = project.start
    col = COL_DATE_START
    while d <= project.end:
        is_month_start = (d == project.start) or d.day == 1
        is_week_start = (
            d == project.start
            or _is_week_start(d, project.week_start)
            or is_month_start
        )

        if is_month_start:
            level = 0
        elif is_week_start:
            level = 1
        else:
            level = 2

        cols.append(
            DateColumn(
                date=d,
                col=col,
                outline_level=level,
                is_month_start=is_month_start,
                is_week_start=is_week_start,
            )
        )
        d += timedelta(days=1)
        col += 1
    return cols


def _flatten_tasks(tasks: list[Task]) -> list[TaskRow]:
    rows: list[TaskRow] = []
    row_idx = ROW_TASK_START

    def visit(task: Task) -> None:
        nonlocal row_idx
        rows.append(TaskRow(task=task, row=row_idx, outline_level=task.level))
        row_idx += 1
        for child in task.children:
            visit(child)

    for t in tasks:
        visit(t)
    return rows


def build_layout(project: Project) -> Layout:
    return Layout(
        project=project,
        date_columns=_build_date_columns(project),
        task_rows=_flatten_tasks(project.tasks),
    )
