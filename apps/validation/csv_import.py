"""Strict lab CSV parser.

Only moves bytes into the record shape the Racket pipeline expects. It does
no unit, date, or non-detect interpretation: `"<0.5"` passes through
verbatim and the engine decides what it means.
"""

import csv
import io

MAX_BYTES = 1_048_576
MAX_ROWS = 5000
REQUIRED_HEADERS = ("id", "outfall", "Analyte", "value", "unit", "sample_date", "method")
# Blank here is rejected up front; the others are left for the pipeline's
# require-field step so its rejection is persisted by the engine.
_NOT_BLANK = ("id", "outfall", "Analyte", "value")


class LabCsvError(Exception):
    """Raised with a message that is safe to show to the user."""


def parse_lab_csv(file_bytes: bytes) -> tuple[list[dict], list[int]]:
    """Return (records, row_numbers); row_numbers are 1-based data rows."""
    if len(file_bytes) > MAX_BYTES:
        raise LabCsvError("The file is larger than 1 MB.")
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise LabCsvError("The file is not UTF-8. Re-export it as CSV UTF-8.")
    if not text.strip():
        raise LabCsvError("The file is empty.")

    reader = csv.DictReader(io.StringIO(text, newline=""))
    missing = [h for h in REQUIRED_HEADERS if h not in (reader.fieldnames or [])]
    if missing:
        raise LabCsvError(
            "Missing required column(s): " + ", ".join(missing)
            + ". Headers must be spelled exactly: " + ", ".join(REQUIRED_HEADERS) + "."
        )

    records: list[dict] = []
    row_numbers: list[int] = []
    first_row_of_id: dict[str, int] = {}
    for row_number, row in enumerate(reader, start=1):
        if all(not (v or "").strip() for v in row.values() if not isinstance(v, list)):
            continue
        record = {h: (row.get(h) or "").strip() for h in REQUIRED_HEADERS}
        for header in _NOT_BLANK:
            if not record[header]:
                raise LabCsvError(f"row {row_number}: '{header}' is blank.")
        try:
            record["outfall"] = int(record["outfall"])
        except ValueError:
            raise LabCsvError(f"row {row_number}: 'outfall' must be a whole number, got {record['outfall']!r}.")
        if record["id"] in first_row_of_id:
            raise LabCsvError(f"Duplicate id {record['id']!r} in rows {first_row_of_id[record['id']]} and {row_number}.")
        first_row_of_id[record["id"]] = row_number
        if len(records) == MAX_ROWS:
            raise LabCsvError("The file has more than 5,000 data rows.")
        records.append(record)
        row_numbers.append(row_number)

    if not records:
        raise LabCsvError("The file has no data rows.")
    return records, row_numbers
