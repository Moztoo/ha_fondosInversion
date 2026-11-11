"""Unit tests for AnaquelParser."""
import os
import pytest
from app.parser import AnaquelParser

TEST_PDF_PATH = "/tmp/bbva_00003776.pdf"

def test_parser_with_sample_pdf():
    """Verify that the parser correctly extracts records and report date."""
    if not os.path.exists(TEST_PDF_PATH):
        pytest.skip(f"Test PDF not found at {TEST_PDF_PATH}")

    with open(TEST_PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    parser = AnaquelParser()
    report = parser.parse_pdf(pdf_bytes)

    assert report.total_records > 400
    assert report.report_date is not None
    assert "Personas Físicas" in report.segments_found
    assert len(report.categories_found) >= 5

    # Check a well-known fund (e.g. BBVALIQ)
    bbvaliq_records = [r for r in report.records if r.ticker == "BBVALIQ"]
    assert len(bbvaliq_records) > 0
    sample = bbvaliq_records[0]
    assert sample.precio > 0
    assert sample.rendimiento_1a is not None
