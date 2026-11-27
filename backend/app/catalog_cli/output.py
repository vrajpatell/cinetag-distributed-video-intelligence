"""Text and file output for interactive sessions and pipelines."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from app.catalog.schema import BreakdownResult, QualityReport, TableResult
from app.catalog_cli.snapshot import QualityDiff, Trend


def atomic_write(path: Path, content: bytes):
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".cinetag-", delete=False) as file:
            temp = Path(file.name)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        if temp:
            temp.unlink(missing_ok=True)


def clean_cell(value, width):
    if value is None:
        return "—"
    text = " ".join(str(value).split())
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    return text if len(text) <= width else text[: width - 1] + "…"


def text_table(headings, rows, *, max_width=44):
    headers = [clean_cell(h, max_width) for h in headings]
    body = [[clean_cell(value, max_width) for value in row] for row in rows]
    widths = [
        max(len(head), *(len(row[i]) for row in body)) if body else len(head)
        for i, head in enumerate(headers)
    ]

    def line(row):
        return "  ".join(
            value.ljust(width) for value, width in zip(row, widths, strict=True)
        ).rstrip()

    return (
        "\n".join(
            [line(headers), line(["─" * width for width in widths]), *(line(row) for row in body)]
        )
        + "\n"
    )


def render_table(result: TableResult):
    rows = [[r.cells[key] for key in result.columns] for r in result.rows]
    return (
        text_table(result.columns, rows) + f"{result.total} matching records · page {result.page}\n"
    )


def render_groups(result: BreakdownResult):
    rows = [
        (group.value, group.count, f"{group.count / result.total:.1%}") for group in result.groups
    ]
    if result.remaining:
        rows.append(("Other groups", result.remaining, f"{result.remaining / result.total:.1%}"))
    return text_table((result.field, "Records", "Share"), rows)


def render_quality(report: QualityReport, *, all_checks=False):
    rows = [
        (check.dataset, check.preset, check.count)
        for check in report.checks
        if all_checks or check.count
    ]
    return f"Checked {report.checked_at.isoformat()}\n" + text_table(
        ("Dataset", "Check", "Findings"), rows
    )


def render_diff(diff: QualityDiff, *, unchanged=False):
    rows = [
        (c.dataset, c.preset, c.before, c.after, c.trend.value)
        for c in diff.changes
        if unchanged or c.trend != Trend.unchanged
    ]
    return text_table(("Dataset", "Check", "Before", "After", "Change"), rows)
