"""
Credit Report Extractor
Parses PDF credit records (business credit reports, personal credit reports,
D&B/Experian/Equifax-style documents) and returns structured data.

Flow:
  1. Try pdfplumber (best for text-based PDFs).
  2. If pdfplumber yields little text, fall back to PyMuPDF (fitz).
  3. If still sparse, flag for OCR (handled by FinancialDocExtractor's OCR path).
"""
import logging
import re
from pathlib import Path
from typing import Any, Union

import pdfplumber

logger = logging.getLogger(__name__)

# Regex patterns for common credit report fields
_PATTERNS: dict[str, re.Pattern] = {
    "business_name":    re.compile(r"(?:business name|company|legal name)[:\s]+([^\n]+)", re.I),
    "ein":              re.compile(r"(?:ein|tax id|fein)[:\s#]+([\d\-]{9,12})", re.I),
    "address":          re.compile(r"(?:address)[:\s]+([^\n]+)", re.I),
    "credit_score":     re.compile(r"(?:credit score|fico score|intelliscore)[:\s]+(\d{3})", re.I),
    "paydex_score":     re.compile(r"(?:paydex)[:\s]+(\d{1,3})", re.I),
    "days_beyond_terms":re.compile(r"(?:days beyond terms|dbt)[:\s]+(\d+)", re.I),
    "high_credit":      re.compile(r"(?:high credit|credit limit)[:\s]+\$?([\d,]+)", re.I),
    "balance_owed":     re.compile(r"(?:balance|amount owed)[:\s]+\$?([\d,]+)", re.I),
    "public_records":   re.compile(r"(?:public records?|judgments?|liens?)[:\s]+(\d+)", re.I),
    "inquiries":        re.compile(r"(?:inquiries?)[:\s]+(\d+)", re.I),
    "years_in_business":re.compile(r"(?:years? in business|business age|established)[:\s]+([\d.]+)", re.I),
    "payment_history":  re.compile(r"(?:payment history|payment record)[:\s]+([^\n]+)", re.I),
    "owner_name":       re.compile(r"(?:owner|principal|guarantor)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)", re.I),
    "ssn_last4":        re.compile(r"SSN[:\s]+\*{5,7}(\d{4})", re.I),
    "dob":              re.compile(r"(?:date of birth|dob)[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", re.I),
}


class CreditReportExtractor:
    """
    Extract structured fields from a PDF credit report.

    Usage:
        extractor = CreditReportExtractor("path/to/credit_report.pdf")
        data = extractor.extract()
        # data["fields"]    → parsed key-value pairs
        # data["raw_text"]  → full extracted text (for LLM prompts)
        # data["pages"]     → page count
    """

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Credit report not found: {self.file_path}")

    def extract(self) -> dict[str, Any]:
        raw_text = self._extract_text()
        fields = self._parse_fields(raw_text)
        trade_lines = self._parse_trade_lines(raw_text)

        result = {
            "source_file": self.file_path.name,
            "raw_text": raw_text,
            "fields": fields,
            "trade_lines": trade_lines,
            "char_count": len(raw_text),
            "needs_ocr": len(raw_text.strip()) < 200,
        }

        if result["needs_ocr"]:
            logger.warning(
                "%s yielded <200 chars — likely a scanned PDF. OCR recommended.",
                self.file_path.name,
            )

        logger.info(
            "Extracted credit report from %s: %d fields, %d trade lines",
            self.file_path.name, len(fields), len(trade_lines),
        )
        return result


    def _extract_text(self) -> str:
        text_parts: list[str] = []
        try:
            with pdfplumber.open(self.file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)
        except Exception as e:
            logger.warning("pdfplumber failed on %s: %s — trying PyMuPDF", self.file_path.name, e)
            text_parts = self._extract_text_pymupdf()

        return "\n".join(text_parts)

    def _extract_text_pymupdf(self) -> list[str]:
        try:
            import fitz  
            doc = fitz.open(str(self.file_path))
            return [page.get_text() for page in doc]
        except Exception as e:
            logger.error("PyMuPDF also failed on %s: %s", self.file_path.name, e)
            return []

    def _parse_fields(self, text: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for field_name, pattern in _PATTERNS.items():
            match = pattern.search(text)
            if match:
                fields[field_name] = match.group(1).strip()
        return fields

    def _parse_trade_lines(self, text: str) -> list[dict[str, str]]:
        """
        Attempt to extract trade line blocks.
        Trade lines often appear as repeated sections with creditor / balance / status.
        This is a best-effort heuristic; real report layouts vary by bureau.
        """
        trade_lines: list[dict[str, str]] = []

        block_pattern = re.compile(
            r"(?P<creditor>[A-Z][A-Z &,.\-]+)\s+"
            r"(?:balance|bal)[:\s]+\$?(?P<balance>[\d,]+)\s+"
            r"(?:status|rating)[:\s]+(?P<status>[^\n]+)",
            re.I,
        )
        for match in block_pattern.finditer(text):
            trade_lines.append({
                "creditor":  match.group("creditor").strip(),
                "balance":   match.group("balance").strip(),
                "status":    match.group("status").strip(),
            })

        return trade_lines
