"""CineTag reporting CLI. Run python -m app.catalog_cli --help for available commands."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from pydantic import ValidationError

from app.catalog.schema import (
    BreakdownQuery,
    Condition,
    ExportQuery,
    FileFormat,
    Operator,
    Order,
    Sorting,
    TableQuery,
)
from app.catalog_cli.client import CatalogClient, CatalogError
from app.catalog_cli.output import (
    atomic_write,
    render_diff,
    render_groups,
    render_quality,
    render_table,
    text_table,
)
from app.catalog_cli.snapshot import diff_reports, load_snapshot
from app.delivery.schema import DeliveryFormat


def positive(raw):
    value = int(raw)
    if value <= 0:
        raise argparse.ArgumentTypeError("Supply a positive integer")
    return value


def selection_flags(parser):
    parser.add_argument("dataset", help="Dataset ID, e.g. videos or tags")
    parser.add_argument("--search", default="", help="Literal text search")
    parser.add_argument("--preset", help="A named dataset preset")
    parser.add_argument(
        "--where",
        action="append",
        default=[],
        metavar="FIELD:OP[:VALUE]",
        help="Add a filter; may be repeated",
    )


def projection_flags(parser):
    selection_flags(parser)
    parser.add_argument("--columns", help="Comma-separated column IDs in output order")
    parser.add_argument("--sort", metavar="FIELD", help="Field used to order records")
    parser.add_argument(
        "--desc", action="store_true", help="Sort the selected field in descending order"
    )


def output_flags(parser, *, json_output=True):
    parser.add_argument("-o", "--output", type=Path, help="Write output atomically to this file")
    if json_output:
        parser.add_argument(
            "--json", action="store_true", help="Emit the full machine-readable response"
        )


def build_parser():
    parser = argparse.ArgumentParser(
        prog="cinetag-catalog", description="Query CineTag's catalog and export editorial metadata."
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("CINETAG_API_URL", "http://localhost:8000"),
        help="CineTag API origin (default: CINETAG_API_URL or http://localhost:8000)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    datasets = commands.add_parser("datasets", help="List available report datasets")
    output_flags(datasets)
    fields = commands.add_parser(
        "describe", help="Show columns, operators, and presets for a dataset"
    )
    fields.add_argument("dataset")
    output_flags(fields)
    rows = commands.add_parser("query", help="Query one page of records")
    projection_flags(rows)
    rows.add_argument("--page", type=positive, default=1)
    rows.add_argument("--page-size", type=positive, default=25)
    output_flags(rows)
    groups = commands.add_parser("groups", help="Count matching records by field")
    selection_flags(groups)
    groups.add_argument("--by", required=True, metavar="FIELD")
    groups.add_argument("--limit", type=positive, default=12)
    output_flags(groups)
    export = commands.add_parser(
        "export", help="Export all matching records within the server limit"
    )
    projection_flags(export)
    export.add_argument("--format", choices=list(FileFormat), default="csv")
    output_flags(export, json_output=False)
    quality = commands.add_parser(
        "quality", help="Report catalog quality findings or save a JSON baseline"
    )
    quality.add_argument(
        "--all", action="store_true", help="Include checks with zero findings in the text table"
    )
    output_flags(quality)
    diff = commands.add_parser(
        "diff", help="Compare a saved quality baseline to another snapshot or the live catalog"
    )
    diff.add_argument("baseline", type=Path)
    diff.add_argument(
        "--current", type=Path, help="Read a second snapshot for a fully offline comparison"
    )
    diff.add_argument(
        "--all", action="store_true", help="Include unchanged checks in the text report"
    )
    diff.add_argument(
        "--fail-on-increase",
        action="store_true",
        help="Return exit code 3 when an existing check gains findings",
    )
    output_flags(diff)
    compare = commands.add_parser(
        "compare", help="Compare metadata and approved tags for two assets"
    )
    compare.add_argument("left", type=positive)
    compare.add_argument("right", type=positive)
    output_flags(compare)
    delivery = commands.add_parser("delivery", help="List available sidecars or download a file")
    delivery.add_argument("video", type=positive)
    delivery.add_argument(
        "--file", choices=list(DeliveryFormat), help="Download this sidecar (requires --output)"
    )
    output_flags(delivery)
    return parser


def selection(args):
    filters = []
    for raw in args.where:
        parts = raw.split(":", 2)
        if len(parts) < 2:
            raise CatalogError("Use FIELD:OP:VALUE or FIELD:missing / FIELD:present.")
        try:
            operator = Operator(parts[1])
        except ValueError as exc:
            raise CatalogError(f"Unknown filter operator: {parts[1]}") from exc
        filters.append(
            Condition(field=parts[0], operator=operator, value=parts[2] if len(parts) > 2 else None)
        )
    return {"search": args.search, "preset": args.preset, "filters": filters}


def projection(args):
    if args.desc and not args.sort:
        raise CatalogError("--desc requires --sort FIELD")
    return {
        **selection(args),
        "columns": [s.strip() for s in args.columns.split(",")]
        if args.columns is not None
        else None,
        "sort": Sorting(
            field=args.sort, direction=Order.descending if args.desc else Order.ascending
        )
        if args.sort
        else None,
    }


def emit(args, data, stdout):
    if isinstance(data, str):
        encoded = data.encode()
    else:
        encoded = data
    if args.output:
        atomic_write(args.output, encoded)
    else:
        stdout.write(encoded)


def model_output(args, model, text, stdout):
    if args.json:
        emit(args, model.model_dump_json(indent=2) + "\n", stdout)
    else:
        emit(args, text(), stdout)


def run(args, client, stdout):
    if args.command in ("datasets", "describe"):
        schema = client.schema()
        if args.command == "datasets":
            model_output(
                args,
                schema,
                lambda: text_table(
                    ("Dataset", "Description"), [(d.id, d.description) for d in schema.datasets]
                ),
                stdout,
            )
        else:
            dataset = next((d for d in schema.datasets if d.id == args.dataset), None)
            if not dataset:
                raise CatalogError(f"Unknown dataset: {args.dataset}")

            def describe():
                fields = text_table(
                    ("Column", "Kind", "Operators"),
                    [
                        (f.id, f.kind.value, ", ".join(op.value for op in f.operators))
                        for f in dataset.fields
                    ],
                )
                presets = text_table(
                    ("Preset", "Description"), [(p.id, p.description) for p in dataset.presets]
                )
                return dataset.label + "\n" + fields + "\n" + presets

            model_output(args, dataset, describe, stdout)
    elif args.command == "query":
        result = client.table(
            args.dataset, TableQuery(**projection(args), page=args.page, page_size=args.page_size)
        )
        model_output(args, result, lambda: render_table(result), stdout)
    elif args.command == "groups":
        result = client.groups(
            args.dataset, BreakdownQuery(**selection(args), field=args.by, limit=args.limit)
        )
        model_output(args, result, lambda: render_groups(result), stdout)
    elif args.command == "export":
        emit(
            args,
            client.export(args.dataset, ExportQuery(**projection(args), format=args.format)),
            stdout,
        )
    elif args.command == "quality":
        report = client.quality()
        model_output(args, report, lambda: render_quality(report, all_checks=args.all), stdout)
    elif args.command == "diff":
        baseline = load_snapshot(args.baseline)
        current = load_snapshot(args.current) if args.current else client.quality()
        diff = diff_reports(baseline, current)
        model_output(args, diff, lambda: render_diff(diff, unchanged=args.all), stdout)
        if args.fail_on_increase and diff.has_increases():
            return 3
    elif args.command == "compare":
        comp = client.compare(args.left, args.right)
        model_output(
            args,
            comp,
            lambda: text_table(
                ("Metric", comp.left.title, comp.right.title),
                [(m.label, m.left, m.right) for m in comp.metrics],
            ),
            stdout,
        )
    elif args.command == "delivery":
        if args.file:
            if not args.output or args.json:
                raise CatalogError(
                    "Downloading a delivery file requires --output PATH and supports the original format only."
                )
            emit(args, client.file(args.video, DeliveryFormat(args.file)), stdout)
        else:
            preview = client.preview(args.video)
            model_output(
                args,
                preview,
                lambda: text_table(
                    ("Format", "Filename", "Availability"),
                    [(f.format.value, f.filename, f.reason or "Ready") for f in preview.files],
                ),
                stdout,
            )
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "diff" and args.current:
            return run(args, None, sys.stdout.buffer)
        with CatalogClient(args.api_url, os.environ.get("CINETAG_API_KEY")) as client:
            return run(args, client, sys.stdout.buffer)
    except (OSError, CatalogError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
