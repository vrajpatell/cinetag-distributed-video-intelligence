"""Portable, deterministic exports of the user's selected columns."""

import csv
import io
import json

from app.catalog.schema import FileFormat, TableResult

MEDIA_TYPES = {
    FileFormat.csv: "text/csv",
    FileFormat.json: "application/json",
    FileFormat.ndjson: "application/x-ndjson",
}


def spreadsheet_value(value):
    if isinstance(value, str) and (
        value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(("=", "+", "-", "@"))
    ):
        return "'" + value
    return value


def encode_table(result: TableResult, file_format: FileFormat) -> bytes:
    records = [row.cells for row in result.rows]
    if file_format == FileFormat.csv:
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(result.columns)
        for record in records:
            writer.writerow(spreadsheet_value(record[key]) for key in result.columns)
        return stream.getvalue().encode("utf-8-sig")
    if file_format == FileFormat.ndjson:
        return "".join(
            json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n" for record in records
        ).encode()
    return (json.dumps(records, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
