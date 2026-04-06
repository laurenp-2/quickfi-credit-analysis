"""
Spreadsheet Extractor
Reads the credit application "Input Data" spreadsheet (Excel or CSV) and returns
a normalized dict of applicant fields.
"""
import logging
from pathlib import Path
from typing import Any, Union

import pandas as pd

logger = logging.getLogger(__name__)

# Canonical field names → possible aliases in the spreadsheet header row
FIELD_ALIASES: dict[str, list[str]] = {
    "business_name":       ["business name", "company name", "legal name", "entity name"],
    "dba":                 ["dba", "doing business as", "trade name"],
    "ein":                 ["ein", "tax id", "employer identification number", "fein"],
    "business_address":    ["business address", "address", "street address"],
    "city":                ["city"],
    "state":               ["state"],
    "zip_code":            ["zip", "zip code", "postal code"],
    "phone":               ["phone", "phone number", "business phone", "telephone"],
    "owner_name":          ["owner name", "principal name", "guarantor name", "owner", "principal"],
    "owner_ssn_last4":     ["ssn last 4", "last 4 ssn", "ssn (last 4)", "last four ssn"],
    "owner_dob":           ["date of birth", "dob", "birth date"],
    "time_in_business":    ["time in business", "years in business", "business age"],
    "business_start_date": ["business start date", "start date", "date established", "inception date"],
    "annual_revenue":      ["annual revenue", "gross revenue", "yearly revenue", "revenue"],
    "requested_amount":    ["requested amount", "loan amount", "financing amount", "request amount"],
    "equipment_type":      ["equipment type", "collateral type", "asset type", "equipment"],
    "equipment_cost":      ["equipment cost", "asset cost", "collateral value"],
    "business_type":       ["business type", "entity type", "legal structure"],
    "industry":            ["industry", "naics", "sic", "business industry"],
    "credit_score":        ["credit score", "fico", "personal credit score"],
}


def _build_alias_map(columns: list[str]) -> dict[str, str]:
    """Map each spreadsheet column header → canonical field name."""
    alias_map: dict[str, str] = {}
    normalized_cols = {col.strip().lower(): col for col in columns}
    for canonical, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in normalized_cols:
                alias_map[normalized_cols[alias]] = canonical
                break
    return alias_map


class SpreadsheetExtractor:
    """
    Extract credit application data from an Excel (.xlsx, .xls) or CSV file.

    Usage:
        extractor = SpreadsheetExtractor("path/to/input_data.xlsx")
        records = extractor.extract()   # list of dicts, one per applicant row
    """

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.file_path}")

    def extract(self) -> list[dict[str, Any]]:
        """Return a list of applicant dicts (one per non-header row)."""
        df = self._load()
        alias_map = _build_alias_map(list(df.columns))

        if not alias_map:
            logger.warning(
                "No recognized column headers found in %s. "
                "Returning raw rows — check FIELD_ALIASES in spreadsheet_extractor.py.",
                self.file_path.name,
            )

        records: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            record: dict[str, Any] = {}
            for col, value in row.items():
                canonical = alias_map.get(str(col), str(col).strip().lower().replace(" ", "_"))
                record[canonical] = None if pd.isna(value) else value
            records.append(record)

        logger.info("Extracted %d applicant row(s) from %s", len(records), self.file_path.name)
        return records

    # ── private ────────────────────────────────────────────────────────────

    def _load(self) -> pd.DataFrame:
        suffix = self.file_path.suffix.lower()
        if suffix in {".xlsx", ".xls", ".xlsm"}:
            df = pd.read_excel(self.file_path, dtype=str)
        elif suffix == ".csv":
            df = pd.read_csv(self.file_path, dtype=str)
        else:
            raise ValueError(f"Unsupported file type: {suffix}. Expected .xlsx, .xls, or .csv")

        # Drop completely empty rows
        df.dropna(how="all", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
