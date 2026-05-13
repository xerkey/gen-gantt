from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

import yaml


class GanttError(Exception):
    pass


@dataclass
class Task:
    id: str
    name: str
    level: int
    start: date | None = None
    end: date | None = None
    role: str = ""
    assignee: str = ""
    children: list["Task"] = field(default_factory=list)

    def walk(self) -> Iterator["Task"]:
        yield self
        for child in self.children:
            yield from child.walk()


@dataclass
class Project:
    name: str
    start: date
    end: date
    week_start: str
    tasks: list[Task]

    def walk_tasks(self) -> Iterator[Task]:
        for t in self.tasks:
            yield from t.walk()


def _parse_date(value: Any, field_name: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise GanttError(f"{field_name} is not a valid ISO 8601 date: {value!r}") from exc
    raise GanttError(f"{field_name} must be an ISO 8601 date string, got {type(value).__name__}")


def _build_task(raw: dict[str, Any], parent_level: int | None) -> Task:
    if not isinstance(raw, dict):
        raise GanttError(f"Each task must be a mapping, got {type(raw).__name__}")
    for required in ("id", "name", "level"):
        if required not in raw:
            raise GanttError(f"Task is missing required field '{required}': {raw!r}")

    task_id = str(raw["id"])
    name = str(raw["name"])
    level = raw["level"]
    if not isinstance(level, int) or level not in (0, 1, 2):
        raise GanttError(f"Task '{task_id}' has invalid level {level!r}; must be 0, 1, or 2")
    if parent_level is not None and level != parent_level + 1:
        raise GanttError(
            f"Task '{task_id}' level {level} is invalid for parent level {parent_level}"
        )

    start = _parse_date(raw["start"], f"task '{task_id}'.start") if raw.get("start") is not None else None
    end = _parse_date(raw["end"], f"task '{task_id}'.end") if raw.get("end") is not None else None

    if level >= 1:
        if start is None or end is None:
            raise GanttError(
                f"Task '{task_id}' at level {level} requires both 'start' and 'end'"
            )
        if start > end:
            raise GanttError(f"Task '{task_id}' has start ({start}) after end ({end})")

    role = str(raw.get("role") or "")
    assignee = str(raw.get("assignee") or "")

    children_raw = raw.get("children") or []
    if not isinstance(children_raw, list):
        raise GanttError(f"Task '{task_id}'.children must be a list")

    children = [_build_task(c, level) for c in children_raw]

    if level == 0:
        if not children:
            raise GanttError(f"Phase '{task_id}' (level 0) must have at least one child task")
        start = min(c.start for c in children if c.start is not None)
        end = max(c.end for c in children if c.end is not None)

    return Task(
        id=task_id,
        name=name,
        level=level,
        start=start,
        end=end,
        role=role,
        assignee=assignee,
        children=children,
    )


def _check_unique_ids(tasks: list[Task]) -> None:
    seen: set[str] = set()
    for t in tasks:
        for node in t.walk():
            if node.id in seen:
                raise GanttError(f"Duplicate task id: '{node.id}'")
            seen.add(node.id)


def _check_in_range(project_start: date, project_end: date, tasks: list[Task]) -> None:
    for t in tasks:
        for node in t.walk():
            if node.start is None or node.end is None:
                continue
            if node.start < project_start or node.end > project_end:
                raise GanttError(
                    f"Task '{node.id}' range {node.start}..{node.end} is outside project range "
                    f"{project_start}..{project_end}"
                )


def load_project(path: str | Path) -> Project:
    p = Path(path)
    if not p.exists():
        raise GanttError(f"Input YAML not found: {p}")

    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise GanttError("Top-level YAML must be a mapping")

    project_raw = data.get("project")
    if not isinstance(project_raw, dict):
        raise GanttError("'project' section is required and must be a mapping")

    name = str(project_raw.get("name", ""))
    if not name:
        raise GanttError("project.name is required")

    if "start" not in project_raw or "end" not in project_raw:
        raise GanttError("project.start and project.end are required")

    start = _parse_date(project_raw["start"], "project.start")
    end = _parse_date(project_raw["end"], "project.end")
    if start > end:
        raise GanttError(f"project.start ({start}) is after project.end ({end})")

    week_start_raw = str(project_raw.get("week_start", "monday")).lower()
    if week_start_raw not in ("monday", "sunday"):
        raise GanttError(f"project.week_start must be 'monday' or 'sunday', got {week_start_raw!r}")

    tasks_raw = data.get("tasks") or []
    if not isinstance(tasks_raw, list):
        raise GanttError("'tasks' must be a list")

    tasks = [_build_task(t, None) for t in tasks_raw]
    for t in tasks:
        if t.level != 0:
            raise GanttError(f"Top-level task '{t.id}' must have level 0")

    _check_unique_ids(tasks)
    _check_in_range(start, end, tasks)

    return Project(name=name, start=start, end=end, week_start=week_start_raw, tasks=tasks)
