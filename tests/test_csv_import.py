import pytest

from apps.validation.csv_import import MAX_BYTES, MAX_ROWS, REQUIRED_HEADERS, LabCsvError, parse_lab_csv

HEADER = "id,outfall,Analyte,value,unit,sample_date,method"


def csv_bytes(*rows, header=HEADER, eol="\n"):
    return (eol.join([header, *rows]) + eol).encode("utf-8")


def test_parses_valid_rows():
    records, row_numbers = parse_lab_csv(csv_bytes(
        "r1,1,TSS,27.5,mg/L,2026-03-05,SM2540D",
        "r2,1,TSS,30,mg/L,2026-03-12,SM2540D",
    ))
    assert records[0] == {"id": "r1", "outfall": 1, "Analyte": "TSS", "value": "27.5", "unit": "mg/L",
                          "sample_date": "2026-03-05", "method": "SM2540D"}
    assert len(records) == 2
    assert row_numbers == [1, 2]


def test_non_detect_passes_through_verbatim():
    records, _ = parse_lab_csv(csv_bytes("r1,1,TSS,<0.5,mg/L,2026-03-05,SM2540D"))
    assert records[0]["value"] == "<0.5"


def test_accepts_bom_and_crlf_and_trailing_blank_lines():
    data = b"\xef\xbb\xbf" + csv_bytes("r1,1,TSS,1,mg/L,2026-03-05,M", eol="\r\n") + b"\r\n,,,,,,\r\n\r\n"
    records, row_numbers = parse_lab_csv(data)
    assert [r["id"] for r in records] == ["r1"]
    assert row_numbers == [1]


def test_ignores_extra_columns():
    records, _ = parse_lab_csv(csv_bytes("r1,1,TSS,1,mg/L,2026-03-05,M,note", header=HEADER + ",comment"))
    assert set(records[0]) == set(REQUIRED_HEADERS)


def test_missing_headers_named_in_error():
    with pytest.raises(LabCsvError, match="Analyte"):
        parse_lab_csv(b"id,outfall,value,unit,sample_date,method\nr1,1,1,mg/L,2026-03-05,M\n")


def test_header_whitespace_or_case_names_expected_spelling():
    with pytest.raises(LabCsvError, match="id"):
        parse_lab_csv(csv_bytes("r1,1,TSS,1,mg/L,d,M", header=" id ,outfall,Analyte,value,unit,sample_date,method"))
    with pytest.raises(LabCsvError, match="Analyte"):
        parse_lab_csv(csv_bytes("r1,1,TSS,1,mg/L,d,M", header="id,outfall,analyte,value,unit,sample_date,method"))


def test_blank_required_value_reports_row_number():
    with pytest.raises(LabCsvError, match="row 2"):
        parse_lab_csv(csv_bytes("r1,1,TSS,1,mg/L,d,M", "r2,1,,1,mg/L,d,M"))


def test_blank_unit_date_method_allowed():
    records, _ = parse_lab_csv(csv_bytes("r1,1,TSS,1,,,"))
    assert (records[0]["unit"], records[0]["sample_date"], records[0]["method"]) == ("", "", "")


def test_non_integer_outfall_rejected():
    with pytest.raises(LabCsvError, match="row 1"):
        parse_lab_csv(csv_bytes("r1,one,TSS,1,mg/L,d,M"))


def test_duplicate_id_names_both_rows():
    with pytest.raises(LabCsvError, match="rows 1 and 3"):
        parse_lab_csv(csv_bytes("r1,1,TSS,1,mg/L,d,M", "r2,1,TSS,1,mg/L,d,M", "r1,1,TSS,1,mg/L,d,M"))


def test_non_utf8_rejected():
    with pytest.raises(LabCsvError, match="UTF-8"):
        parse_lab_csv(HEADER.encode() + b"\nr1,1,TSS,1,\xb5g/L,d,M\n")


def test_size_and_row_limits():
    with pytest.raises(LabCsvError, match="1 MB"):
        parse_lab_csv(b"x" * (MAX_BYTES + 1))
    rows = [f"r{i},1,TSS,1,mg/L,d,M" for i in range(MAX_ROWS + 1)]
    with pytest.raises(LabCsvError, match="5,000"):
        parse_lab_csv(csv_bytes(*rows))


def test_empty_file_rejected():
    with pytest.raises(LabCsvError):
        parse_lab_csv(b"")
    with pytest.raises(LabCsvError, match="no data rows"):
        parse_lab_csv(HEADER.encode() + b"\n")
