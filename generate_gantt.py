from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from gantt.layout import build_layout
from gantt.loader import GanttError, load_project
from gantt.writer import write_workbook


def _slugify(name: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]", "_", name).strip()
    return cleaned or "project"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a collapsible Gantt chart Excel file from a YAML definition."
    )
    parser.add_argument("input", help="Path to input YAML file")
    parser.add_argument(
        "--output",
        default=".",
        help="Output directory (default: current directory)",
    )
    args = parser.parse_args(argv)

    try:
        project = load_project(args.input)
        layout = build_layout(project)
        out_dir = Path(args.output)
        out_path = out_dir / f"{_slugify(project.name)}_gantt.xlsx"
        write_workbook(layout, out_path)
    except GanttError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
