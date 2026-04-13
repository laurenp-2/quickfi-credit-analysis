"""
Ingest Pipeline
Single entry point that wires all extractors, the normalizer, and the ratio
calculator together into four clean functions:

  ingest_application(source)        → list of normalized applicant dicts
  ingest_credit_records(sources)    → list of normalized credit record dicts
  ingest_financial_docs(source, …)  → {documents, financials, ratios}
  ingest_documents(…)               → unified result combining all three
"""
import io
import logging
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional, Union

from extractors.spreadsheet_extractor import SpreadsheetExtractor
from extractors.credit_report_extractor import CreditReportExtractor
from extractors.financial_doc_extractor import FinancialDocExtractor
from normalizers.data_normalizer import DataNormalizer

# Ratio calculator lives in ratios/calculator.py (Rinah's module)
sys.path.insert(0, str(Path(__file__).parent.parent))
from ratios.calculator import calculate_all  # noqa: E402

logger = logging.getLogger(__name__)
_norm = DataNormalizer()




def _to_path_or_bytes(source: Any) -> Union[Path, bytes]:
    """
    Accept a file path (str/Path), raw bytes, or a Streamlit UploadedFile
    and return either a Path or bytes.
    """
    if isinstance(source, (str, Path)):
        return Path(source)
    if isinstance(source, bytes):
        return source
    # Streamlit UploadedFile (or any file-like with .read())
    if hasattr(source, "read"):
        return source.read()
    raise TypeError(f"Unsupported source type: {type(source)}")


def _bytes_to_temp_file(data: bytes, suffix: str) -> Path:
    """Write bytes to a named temp file and return its path."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(data)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


#  pull numeric values out of raw doc text to feed calculate_all().

def _parse_currency_from_text(text: str, *labels: str) -> Optional[float]:
    """
    Search `text` for the first label match and return the dollar value on
    the same line.  Handles commas, dollar signs, and parenthesised negatives.
    Labels are tried in order; first match wins.
    """
    for label in labels:
        pattern = re.compile(
            rf"{re.escape(label)}\s*[:\-]?\s*\(?\$?([\d,]+(?:\.\d+)?)\)?",
            re.I,
        )
        m = pattern.search(text)
        if m:
            raw = m.group(0)
            negative = "(" in raw and ")" in raw
            value = float(m.group(1).replace(",", ""))
            return -value if negative else value
    return None


def _parse_int_from_text(text: str, *labels: str) -> Optional[int]:
    """Find a plain integer on the same line as any of the labels."""
    for label in labels:
        pattern = re.compile(
            rf"{re.escape(label)}\s*[:\-]?\s*(\d+)",
            re.I,
        )
        m = pattern.search(text)
        if m:
            return int(m.group(1))
    return None


def _parse_financials_from_docs(docs: list, loan_amount: Optional[float] = None) -> dict:
    """
    Walk through extracted doc dicts and pull all numeric fields that
    ratios/calculator.py's calculate_all() needs.

    Returns a dict with keys matching calculate_all()'s expected input.
    Missing values are left as None; calculate_all() handles those gracefully.
    """
    # Merge all text by doc type so we search the most relevant document first
    by_type: dict[str, str] = {}
    for doc in docs:
        dt = doc.get("doc_type", "unknown")
        by_type[dt] = by_type.get(dt, "") + "\n" + doc.get("raw_text", "")

    pl   = by_type.get("profit_loss", "")
    bs   = by_type.get("balance_sheet", "")
    bank = by_type.get("bank_statement", "")
    all_text = "\n".join(by_type.values())


    revenue = _parse_currency_from_text(
        pl or all_text,
        "Total Revenue", "Gross Revenue", "Net Revenue", "Revenue",
        "Total Sales", "Gross Sales",
    )
    cogs = _parse_currency_from_text(
        pl or all_text,
        "Cost of Goods Sold", "COGS", "Cost of Sales",
        "Total Cost of Revenue",
    )
    net_income = _parse_currency_from_text(
        pl or all_text,
        "Net Income", "Net Profit", "Net Loss",
        "Net Earnings",
    )
    total_expenses = _parse_currency_from_text(
        pl or all_text,
        "Total Expenses", "Total Operating Expenses",
    )
    debt_service = _parse_currency_from_text(
        pl or all_text,
        "Loan/Finance Payments", "Loan Payments", "Finance Payments",
        "Lease/Finance Payments", "Debt Service", "Annual Debt Service",
        "Total Debt Payments",
    )
    depreciation = _parse_currency_from_text(
        pl or all_text, "Depreciation", "Depreciation & Amortization",
    )


    current_assets = _parse_currency_from_text(
        bs or all_text,
        "Total Current Assets", "Current Assets",
    )
    current_liabilities = _parse_currency_from_text(
        bs or all_text,
        "Total Current Liabilities", "Current Liabilities",
    )
    total_liabilities = _parse_currency_from_text(
        bs or all_text,
        "Total Liabilities", "TOTAL LIABILITIES",
    )
    total_equity = _parse_currency_from_text(
        bs or all_text,
        "Owner Equity", "Owners Equity", "Owner's Equity",
        "Total Equity", "Stockholders Equity", "Net Worth",
    )


    nsf_count = _parse_int_from_text(
        bank or all_text, "NSF Items", "NSF", "Non-Sufficient Funds",
    )
    avg_balance = _parse_currency_from_text(
        bank or all_text,
        "Average Daily Balance", "Average Balance", "Avg Daily Balance",
    )

    #  Derived: Net Operating Income 
    # NOI = Net Income + Depreciation + Interest (simple add-back when
    # interest isn't separately broken out).
    noi: Optional[float] = None
    if net_income is not None:
        noi = net_income
        if depreciation is not None:
            noi += depreciation

    # default to 0 if bank statement present but no NSF line 
    if nsf_count is None and bank:
        # Presence of "No NSF" / "0 NSF" → treat as 0
        if re.search(r"no\s+nsf|0\s+nsf", bank, re.I):
            nsf_count = 0

    financials = {
        # P&L
        "revenue":              revenue,
        "cogs":                 cogs,
        "net_income":           net_income,
        "total_expenses":       total_expenses,
        "net_operating_income": noi,
        "total_debt_service":   debt_service,
        "depreciation":         depreciation,
        # Balance sheet
        "current_assets":       current_assets,
        "current_liabilities":  current_liabilities,
        "total_liabilities":    total_liabilities,
        "total_equity":         total_equity,
        # Bank statement
        "nsf_count":            nsf_count,
        "avg_balance":          avg_balance,
        # Application / passed in
        "loan_amount":          loan_amount,
        # YoY: not yet populated (requires multi-year docs — Week 3+)
        "current_year_revenue": revenue,
        "prior_year_revenue":   None,
    }

    logger.info(
        "Parsed financials — revenue=%s, net_income=%s, noi=%s, "
        "current_ratio_inputs=(%s/%s), d_e_inputs=(%s/%s), nsf=%s",
        revenue, net_income, noi,
        current_assets, current_liabilities,
        total_liabilities, total_equity,
        nsf_count,
    )
    return financials




def ingest_application(source: Any) -> list:
    """
    Extract and normalize all applicant rows from a credit application
    spreadsheet (Excel or CSV).

    Args:
        source: file path (str/Path), raw bytes, or Streamlit UploadedFile.

    Returns:
        List of normalized applicant dicts, one per spreadsheet row.
    """
    resolved = _to_path_or_bytes(source)

    if isinstance(resolved, bytes):
        # Need a real path for SpreadsheetExtractor — detect extension from
        # original filename if it was an UploadedFile, else default to .csv.
        suffix = ".csv"
        if hasattr(source, "name"):
            suffix = Path(source.name).suffix or ".csv"
        tmp_path = _bytes_to_temp_file(resolved, suffix)
    else:
        tmp_path = resolved

    try:
        raw_records = SpreadsheetExtractor(tmp_path).extract()
    finally:
        if isinstance(resolved, bytes):
            tmp_path.unlink(missing_ok=True)

    normalized = [_norm.normalize_record(r) for r in raw_records]
    logger.info("ingest_application: %d applicant row(s) ingested.", len(normalized))
    return normalized


def ingest_credit_records(sources: list) -> list:
    """
    Extract and normalize one or more credit record PDFs.

    Args:
        sources: list of file paths (str/Path), raw bytes, or Streamlit
                 UploadedFiles.  Each element is one credit report.

    Returns:
        List of dicts, one per report:
        {
            "source_file": str,
            "raw_text":    str,
            "fields":      dict,   # normalized key-value pairs
            "trade_lines": list,
            "needs_ocr":   bool,
        }
    """
    results = []
    for source in sources:
        resolved = _to_path_or_bytes(source)

        if isinstance(resolved, bytes):
            suffix = ".pdf"
            if hasattr(source, "name"):
                suffix = Path(source.name).suffix or ".pdf"
            tmp_path = _bytes_to_temp_file(resolved, suffix)
        else:
            tmp_path = resolved

        try:
            raw = CreditReportExtractor(tmp_path).extract()
        finally:
            if isinstance(resolved, bytes):
                tmp_path.unlink(missing_ok=True)

        raw["fields"] = _norm.normalize_record(raw.get("fields", {}))
        results.append(raw)

    logger.info("ingest_credit_records: %d record(s) ingested.", len(results))
    return results


def ingest_financial_docs(
    source: Any,
    loan_amount: Optional[float] = None,
) -> dict:
    """
    Extract, classify, parse, and score all financial documents from a
    zip archive.

    Args:
        source:      zip file path (str/Path), raw bytes, or Streamlit
                     UploadedFile.
        loan_amount: requested loan amount from the application (passed
                     through to loan_to_revenue ratio).

    Returns:
        {
            "documents":  list of extracted doc dicts from FinancialDocExtractor,
            "financials": dict of parsed numeric fields,
            "ratios":     dict from ratios/calculator.calculate_all(),
        }
    """
    resolved = _to_path_or_bytes(source)
    docs = FinancialDocExtractor(resolved).extract()

    financials = _parse_financials_from_docs(docs, loan_amount=loan_amount)
    ratios     = calculate_all(financials)

    logger.info(
        "ingest_financial_docs: %d doc(s), overall_tier=%s, gaps=%s",
        len(docs), ratios.get("overall_tier"), ratios.get("data_gaps"),
    )
    return {
        "documents":  docs,
        "financials": financials,
        "ratios":     ratios,
    }


def ingest_documents(
    application_source: Optional[Any] = None,
    credit_sources: Optional[list] = None,
    financial_zip: Optional[Any] = None,
    loan_amount: Optional[float] = None,
) -> dict:
    """
    Unified entry point — wires all three extractors together in one call.

    Args:
        application_source: spreadsheet file (path, bytes, or UploadedFile).
        credit_sources:     list of credit report PDFs (paths, bytes, or UploadedFiles).
        financial_zip:      zip archive of financial docs (path, bytes, or UploadedFile).
        loan_amount:        requested loan amount, forwarded to ratio calculator.

    Returns:
        {
            "applicants":  list of normalized applicant dicts   (or [] if not provided),
            "credit":      list of normalized credit record dicts (or [] if not provided),
            "documents":   list of extracted financial doc dicts  (or [] if not provided),
            "financials":  parsed numeric fields dict             (or {} if not provided),
            "ratios":      ratio results from calculate_all()     (or {} if not provided),
        }
    """
    result: dict = {
        "applicants": [],
        "credit":     [],
        "documents":  [],
        "financials": {},
        "ratios":     {},
    }

    if application_source is not None:
        result["applicants"] = ingest_application(application_source)

    if credit_sources:
        result["credit"] = ingest_credit_records(credit_sources)

    if financial_zip is not None:
        fin = ingest_financial_docs(financial_zip, loan_amount=loan_amount)
        result["documents"]  = fin["documents"]
        result["financials"] = fin["financials"]
        result["ratios"]     = fin["ratios"]

    logger.info(
        "ingest_documents: %d applicant(s), %d credit record(s), %d financial doc(s), overall_tier=%s",
        len(result["applicants"]),
        len(result["credit"]),
        len(result["documents"]),
        result["ratios"].get("overall_tier", "n/a"),
    )
    return result
