"""Generate the fictional DOCX evidence fixture used for manual upload testing."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


OUTPUT = Path(__file__).resolve().parents[1] / "test-data" / "attesta_test_compliance_evidence.docx"


def paragraph(text: str, *, style: str | None = None) -> str:
    properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f'<w:p>{properties}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def table(headers: list[str], rows: list[list[str]]) -> str:
    def cell(value: str, header: bool = False) -> str:
        run_properties = "<w:rPr><w:b/></w:rPr>" if header else ""
        return (
            '<w:tc><w:tcPr><w:tcW w:w="1800" w:type="dxa"/></w:tcPr>'
            f'<w:p><w:r>{run_properties}<w:t>{escape(value)}</w:t></w:r></w:p></w:tc>'
        )

    header_row = "<w:tr>" + "".join(cell(value, True) for value in headers) + "</w:tr>"
    data_rows = "".join(
        "<w:tr>" + "".join(cell(value) for value in row) + "</w:tr>" for row in rows
    )
    return (
        '<w:tbl><w:tblPr><w:tblBorders>'
        '<w:top w:val="single" w:sz="4"/><w:left w:val="single" w:sz="4"/>'
        '<w:bottom w:val="single" w:sz="4"/><w:right w:val="single" w:sz="4"/>'
        '<w:insideH w:val="single" w:sz="4"/><w:insideV w:val="single" w:sz="4"/>'
        f"</w:tblBorders></w:tblPr>{header_row}{data_rows}</w:tbl>"
    )


body = "".join(
    [
        paragraph("Attesta Test Compliance Evidence", style="Title"),
        paragraph("Monthly Discharge Monitoring Summary", style="Subtitle"),
        paragraph("TEST DOCUMENT — FICTIONAL DATA — NOT FOR REGULATORY SUBMISSION"),
        paragraph("Document ID: TEST-EVIDENCE-2026-09-001"),
        paragraph("Facility and reporting details", style="Heading1"),
        table(
            ["Field", "Value"],
            [
                ["Facility", "Attesta Demo Wastewater Treatment Plant"],
                ["Permit", "PA0000000 (fictional placeholder)"],
                ["Outfall", "001"],
                ["Reporting period", "September 2026"],
                ["Prepared by", "Jordan Test, Environmental Compliance Coordinator"],
                ["Prepared date", "October 15, 2026"],
            ],
        ),
        paragraph("Analytical results", style="Heading1"),
        paragraph(
            "The following fictional readings intentionally contain potential compliance concerns "
            "to exercise extraction, matching, and human-review workflows."
        ),
        table(
            ["Sample date", "Analyte", "Result", "Unit", "Method", "Qualifier"],
            [
                ["2026-09-03", "TSS", "24.5", "mg/L", "SM 2540 D", "None"],
                ["2026-09-17", "TSS", "71.2", "mg/L", "SM 2540 D", "Potential daily-max exceedance"],
                ["2026-09-02", "pH", "7.2", "s.u.", "SM 4500-H+ B", "None"],
                ["2026-09-09", "pH", "8.1", "s.u.", "SM 4500-H+ B", "None"],
                ["2026-09-16", "pH", "9.4", "s.u.", "SM 4500-H+ B", "Above range"],
                ["2026-09-23", "pH", "7.0", "s.u.", "SM 4500-H+ B", "None"],
                ["2026-09-30", "pH", "6.8", "s.u.", "SM 4500-H+ B", "None"],
                ["2026-09-03", "Flow", "0.42", "MGD", "Totalizer", "Report only"],
                ["2026-09-17", "Flow", "0.57", "MGD", "Totalizer", "Report only"],
            ],
        ),
        paragraph("Quality assurance and review notes", style="Heading1"),
        paragraph("1. Instrument calibration records were reviewed for the reporting period."),
        paragraph("2. Laboratory results were transcribed from fictional bench sheets for testing only."),
        paragraph("3. The chain-of-custody signature for the September 17 sample is intentionally absent."),
        paragraph("4. TSS of 71.2 mg/L is above the fictional 60 mg/L daily maximum."),
        paragraph("5. pH of 9.4 s.u. is outside the fictional permitted range of 6.0–9.0 s.u."),
        paragraph("Attestation", style="Heading1"),
        paragraph(
            "I certify that this synthetic document is intended only for Attesta application testing. "
            "It does not describe an actual facility, permit, discharge, or laboratory analysis."
        ),
        paragraph("Signature: Jordan Test     Date: October 15, 2026"),
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" '
        'w:right="1080" w:bottom="1080" w:left="1080"/></w:sectPr>',
    ]
)

document_xml = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    f"<w:body>{body}</w:body></w:document>"
)

content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

document_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:sz w:val="22"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:rPr><w:i/><w:sz w:val="26"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="240" w:after="100"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>
</w:styles>"""

core_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Attesta Test Compliance Evidence</dc:title>
  <dc:creator>Attesta Test Fixture Generator</dc:creator>
  <dc:description>Fictional compliance evidence for manual upload testing.</dc:description>
  <dcterms:created xsi:type="dcterms:W3CDTF">2026-10-15T12:00:00Z</dcterms:created>
</cp:coreProperties>"""

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
    archive.writestr("[Content_Types].xml", content_types)
    archive.writestr("_rels/.rels", root_rels)
    archive.writestr("word/document.xml", document_xml)
    archive.writestr("word/_rels/document.xml.rels", document_rels)
    archive.writestr("word/styles.xml", styles_xml)
    archive.writestr("docProps/core.xml", core_xml)

print(OUTPUT)
