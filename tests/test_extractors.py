"""
Extractor smoke tests.
Run:  pytest tests/test_extractors.py -v
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors import SpreadsheetExtractor, CreditReportExtractor, FinancialDocExtractor

MOCK_DIR = Path(__file__).parent.parent / "data" / "mock"
INPUT_DIR = MOCK_DIR / "input_data"
CREDIT_DIR = MOCK_DIR / "credit_records"
FIN_DIR = MOCK_DIR / "financial_docs"


# ── SpreadsheetExtractor ─────────────────────────────────────────────────────

class TestSpreadsheetExtractor:
    def test_clean_application(self):
        path = INPUT_DIR / "clean_application.csv"
        if not path.exists():
            pytest.skip("Mock data not generated — run data/mock/generate_mock_data.py first")
        records = SpreadsheetExtractor(path).extract()
        assert len(records) == 1
        r = records[0]
        assert r.get("business_name") == "Apex Trucking LLC"
        assert r.get("ein") == "82-4567890"

    def test_mismatched_application(self):
        path = INPUT_DIR / "mismatched_application.csv"
        if not path.exists():
            pytest.skip("Mock data not generated")
        records = SpreadsheetExtractor(path).extract()
        assert len(records) == 1
        r = records[0]
        # Mismatched EIN
        assert r.get("ein") == "82-9999999"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            SpreadsheetExtractor("nonexistent.csv").extract()


# ── CreditReportExtractor ────────────────────────────────────────────────────

class TestCreditReportExtractor:
    def test_clean_credit_record(self):
        path = CREDIT_DIR / "credit_record_apex_trucking.txt"
        if not path.exists():
            pytest.skip("Mock data not generated")
        # Rename check — extractor expects PDF but works on any readable file
        # For testing we pass the txt directly; real use will be PDFs
        extractor = CreditReportExtractor(path)
        # Monkey-patch _extract_text to just read the txt
        extractor._extract_text = lambda: path.read_text()
        data = extractor.extract()
        assert data["fields"].get("ein") == "82-4567890"
        assert data["fields"].get("credit_score") == "724"

    def test_needs_ocr_flag(self):
        path = CREDIT_DIR / "credit_record_apex_trucking.txt"
        if not path.exists():
            pytest.skip("Mock data not generated")
        extractor = CreditReportExtractor(path)
        extractor._extract_text = lambda: ""  # simulate empty extraction
        data = extractor.extract()
        assert data["needs_ocr"] is True


# ── FinancialDocExtractor ────────────────────────────────────────────────────

class TestFinancialDocExtractor:
    def test_healthy_borrower_zip(self):
        path = FIN_DIR / "healthy_borrower.zip"
        if not path.exists():
            pytest.skip("Mock data not generated")
        docs = FinancialDocExtractor(path).extract()
        assert len(docs) == 3
        doc_types = {d["doc_type"] for d in docs}
        assert "profit_loss" in doc_types or "balance_sheet" in doc_types

    def test_distressed_borrower_zip(self):
        path = FIN_DIR / "distressed_borrower.zip"
        if not path.exists():
            pytest.skip("Mock data not generated")
        docs = FinancialDocExtractor(path).extract()
        assert len(docs) > 0

    def test_invalid_zip(self):
        with pytest.raises((ValueError, Exception)):
            FinancialDocExtractor(b"not a zip file").extract()

