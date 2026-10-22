"""Build fictional evidence files for manually testing the upload + review flow.

Run:  uv run --no-sync python tests/fixtures/sample_evidence/build_samples.py

Standard library only (the app itself reads .docx/.xlsx with zipfile + XML).
Everything here is FICTIONAL: permit PA0000000, the lab, the people and every
value. It matches the placeholder permit in dsl/permit/permits/pa0000000.rkt
(TSS monthly-avg 30 / daily-max 60 mg/L, pH 6.0-9.0 s.u., Flow monthly-avg 0.5 MGD).
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent

BANNER = "FICTIONAL TEST DATA - not a real permit, laboratory or sample."

# ---------------------------------------------------------------- xlsx

_COLS = "ABCDEFGHIJKLMNOP"


def _cell(ref: str, value) -> str:
    if value is None or value == "":
        # Keep the cell so a missing value stays in its column when the app
        # flattens the sheet to tab-separated text.
        return f'<c r="{ref}" t="inlineStr"><is><t></t></is></c>'
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def _sheet(rows: list[list]) -> str:
    body = []
    for r, row in enumerate(rows, start=1):
        cells = "".join(_cell(f"{_COLS[c]}{r}", v) for c, v in enumerate(row))
        body.append(f'<row r="{r}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(body)}</sheetData></worksheet>'
    )


def write_xlsx(path: Path, sheets: dict[str, list[list]]) -> None:
    names = list(sheets)
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(1, len(names) + 1)
        )
        + "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
        + "".join(
            f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(names, start=1)
        )
        + "</sheets></workbook>"
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(names) + 1)
        )
        + "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        for i, n in enumerate(names, start=1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _sheet(sheets[n]))


# ---------------------------------------------------------------- docx

def _p(text: str, bold: bool = False) -> str:
    run_props = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:p><w:r>{run_props}<w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def _table(rows: list[list[str]]) -> str:
    out = ["<w:tbl>"]
    for row in rows:
        out.append("<w:tr>" + "".join(f"<w:tc>{_p(c)}</w:tc>" for c in row) + "</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def write_docx(path: Path, body_xml: str) -> None:
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body_xml}</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("word/document.xml", document)


# ---------------------------------------------------------------- content

HEADER = ["Sample ID", "Collected", "Analyte", "Result", "Unit", "Method", "Reporting limit", "Analyst"]


def complete_lab_report() -> dict[str, list[list]]:
    results = [
        HEADER,
        ["S-0302-PH", "2026-03-02", "pH", 7.4, "s.u.", "SM 4500-H+ B", "", "A. Tester"],
        ["S-0305-TSS", "2026-03-05", "TSS", 27.5, "mg/L", "SM 2540 D", 2.5, "A. Tester"],
        ["S-0305-FLW", "2026-03-05", "Flow", 0.31, "MGD", "Flow meter log", "", "A. Tester"],
        ["S-0309-PH", "2026-03-09", "pH", 7.1, "s.u.", "SM 4500-H+ B", "", "A. Tester"],
        ["S-0312-TSS", "2026-03-12", "TSS", 31.0, "mg/L", "SM 2540 D", 2.5, "A. Tester"],
        ["S-0312-FLW", "2026-03-12", "Flow", 0.29, "MGD", "Flow meter log", "", "A. Tester"],
        ["S-0316-PH", "2026-03-16", "pH", 7.8, "s.u.", "SM 4500-H+ B", "", "A. Tester"],
        ["S-0319-TSS", "2026-03-19", "TSS", "<2.5", "mg/L", "SM 2540 D", 2.5, "A. Tester"],
        ["S-0323-PH", "2026-03-23", "pH", 7.3, "s.u.", "SM 4500-H+ B", "", "A. Tester"],
    ]
    cover = [
        ["Discharge monitoring - laboratory results"],
        [BANNER],
        ["Facility", "Example Wastewater Treatment Plant (fictional)"],
        ["Permit", "PA0000000 (placeholder)"],
        ["Outfall", "001"],
        ["Monitoring period", "2026-03"],
        ["Laboratory", "Example Analytical Laboratory (fictional)"],
        ["Laboratory accreditation ID", "TEST-0000 (fictional)"],
        [],
        ["Note", "A result shown as <2.5 is a non-detect; 2.5 mg/L is the reporting limit for TSS."],
    ]
    certification = [
        ["Laboratory certification"],
        [BANNER],
        ["I certify that the results in this report were produced using the methods listed, and that "
         "samples were received and analysed within their holding times."],
        ["Name", "A. Tester (fictional)"],
        ["Title", "Laboratory Manager"],
        ["Date signed", "2026-04-02"],
        ["Signature", "A. Tester [signed]"],
    ]
    return {"Cover": cover, "Results": results, "Certification": certification}


def incomplete_lab_report() -> dict[str, list[list]]:
    results = [
        ["Sample", "Date", "Analyte", "Value", "Units", "Method", "Analyst"],
        ["S-0305-TSS", "2026-03-05", "TSS", 27.5, "mg/L", "", ""],
        ["S-0312-TSS", "", "TSS", 31.0, "mg/L", "SM 2540 D", ""],
        ["S-0316-TSS", "2026-03-16", "TSS", 18200, "ug/L", "", ""],
        ["S-0309-PH", "2026-03-09", "pH", 9.4, "", "SM 4500-H+ B", ""],
        ["S-0323-PH", "2026-03-23", "pH", 7.2, "s.u.", "", ""],
        ["S-0305-FLW", "2026-03-05", "Flow", 0.31, "MGD", "", ""],
    ]
    cover = [
        ["Lab results - March"],
        [BANNER],
        ["Facility", "Example Wastewater Treatment Plant (fictional)"],
        ["Outfall", "001"],
        ["Note", "Sheet exported from internal tracker. No permit number, laboratory ID or certification on this sheet."],
    ]
    return {"Cover": cover, "Results": results}


def chain_of_custody() -> str:
    body = [
        _p("Chain of Custody Record", bold=True),
        _p(BANNER),
        _p("Facility: Example Wastewater Treatment Plant (fictional)    Permit: PA0000000 (placeholder)    Outfall: 001"),
        _p("Sampler: B. Collector (fictional)    Project: March 2026 DMR sampling"),
        _p(""),
        _table([
            ["Sample ID", "Collected", "Container", "Preservative", "Temp on receipt", "Holding time met"],
            ["S-0305-TSS", "2026-03-05 09:10", "1 L HDPE", "None, iced", "3.8 C", "Yes"],
            ["S-0312-TSS", "2026-03-12 09:25", "1 L HDPE", "None, iced", "9.1 C", "Not recorded"],
            ["S-0319-TSS", "2026-03-19 09:05", "1 L HDPE", "None, iced", "4.2 C", "Yes"],
        ]),
        _p(""),
        _p("Transfers", bold=True),
        _table([
            ["Date", "Relinquished by", "Received by", "Notes"],
            ["2026-03-05", "B. Collector [signed]", "A. Tester [signed]", ""],
            ["2026-03-12", "", "A. Tester [signed]", "Relinquisher signature missing"],
            ["2026-03-19", "B. Collector [signed]", "A. Tester [signed]", ""],
        ]),
        _p(""),
        _p("Comments: The 2026-03-12 cooler arrived warm; ice had melted. Analyst proceeded with analysis."),
    ]
    return "".join(body)


def main() -> int:
    write_xlsx(OUT / "01_lab_results_complete.xlsx", complete_lab_report())
    write_xlsx(OUT / "02_lab_results_incomplete.xlsx", incomplete_lab_report())
    write_docx(OUT / "03_chain_of_custody_gaps.docx", chain_of_custody())
    for name in sorted(p.name for p in OUT.iterdir() if p.suffix in {".xlsx", ".docx"}):
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
