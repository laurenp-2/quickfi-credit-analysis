"""
Data Normalizer
Cleans and standardizes extracted values so the validation agent
can do apples-to-apples comparisons between application data and credit records.
"""
import re
from typing import Any, Optional, Union


_MATCH    = "match"
_MISMATCH = "mismatch"
_MISSING  = "missing"


class DataNormalizer:
    """Normalize common field types to a canonical form."""

# Business name: uppercase, strip legal suffixes, remove extra spaces
    @staticmethod
    def business_name(name: str) -> str:
        if not name:
            return ""
        name = name.upper().strip()
        # Strip legal suffixes for fuzzy comparison
        for suffix in [" LLC", " INC", " CORP", " LTD", " LP", " LLP", " CO", " COMPANY", "."]:
            name = name.replace(suffix, "")
        return " ".join(name.split())

 #EIN
    @staticmethod
    def ein(value: str) -> str:
        """Return EIN as 'XX-XXXXXXX'."""
        digits = re.sub(r"\D", "", str(value or ""))
        if len(digits) == 9:
            return f"{digits[:2]}-{digits[2:]}"
        return digits

# Phone number
    @staticmethod
    def phone(value: str) -> str:
        """Return 10-digit string."""
        return re.sub(r"\D", "", str(value or ""))[-10:]

# Currency → float
    @staticmethod
    def currency(value: Any) -> Optional[float]:
        if value is None:
            return None
        cleaned = re.sub(r"[^\d.\-]", "", str(value))
        try:
            return float(cleaned)
        except ValueError:
            return None

# Credit score → int (300-850)
    @staticmethod
    def credit_score(value: Any) -> Optional[int]:
        try:
            score = int(re.sub(r"\D", "", str(value)))
            return score if 300 <= score <= 850 else None
        except (ValueError, TypeError):
            return None

# Address normalization: uppercase, abbreviate common terms, remove extra spaces
    @staticmethod
    def address(value: str) -> str:
        if not value:
            return ""
        abbrevs = {
            "STREET": "ST", "AVENUE": "AVE", "BOULEVARD": "BLVD",
            "DRIVE": "DR", "ROAD": "RD", "LANE": "LN", "COURT": "CT",
            "SUITE": "STE", "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
        }
        upper = value.upper().strip()
        for long, short in abbrevs.items():
            upper = re.sub(rf"\b{long}\b", short, upper)
        return " ".join(upper.split())

    # ------------------------------------------------------------------ #
    #  Field-level comparators                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def compare_business_name(a: str, b: str) -> dict:
        """Exact match after normalization (suffixes already stripped)."""
        na, nb = DataNormalizer.business_name(a), DataNormalizer.business_name(b)
        status = _MATCH if na == nb else _MISMATCH
        return {"status": status, "application": na, "credit_record": nb}

    @staticmethod
    def compare_ein(a: str, b: str) -> dict:
        """Exact match after formatting."""
        na, nb = DataNormalizer.ein(a), DataNormalizer.ein(b)
        status = _MATCH if na == nb else _MISMATCH
        return {"status": status, "application": na, "credit_record": nb}

    @staticmethod
    def compare_phone(a: str, b: str) -> dict:
        """Exact match on 10-digit string."""
        na, nb = DataNormalizer.phone(a), DataNormalizer.phone(b)
        status = _MATCH if na == nb else _MISMATCH
        return {"status": status, "application": na, "credit_record": nb}

    @staticmethod
    def compare_currency(a: Any, b: Any, tolerance: float = 0.05) -> dict:
        """Match if values are within `tolerance` (default 5%) of each other."""
        na, nb = DataNormalizer.currency(a), DataNormalizer.currency(b)
        if na is None or nb is None:
            return {"status": _MISSING, "application": na, "credit_record": nb}
        if na == nb == 0.0:
            status = _MATCH
        else:
            pct_diff = abs(na - nb) / max(abs(na), abs(nb))
            status = _MATCH if pct_diff <= tolerance else _MISMATCH
        return {"status": status, "application": na, "credit_record": nb}

    @staticmethod
    def compare_credit_score(a: Any, b: Any) -> dict:
        """Exact match after normalization."""
        na, nb = DataNormalizer.credit_score(a), DataNormalizer.credit_score(b)
        if na is None or nb is None:
            return {"status": _MISSING, "application": na, "credit_record": nb}
        status = _MATCH if na == nb else _MISMATCH
        return {"status": status, "application": na, "credit_record": nb}

    @staticmethod
    def compare_address(a: str, b: str) -> dict:
        """Exact match after normalization (abbreviated, uppercased)."""
        na, nb = DataNormalizer.address(a), DataNormalizer.address(b)
        status = _MATCH if na == nb else _MISMATCH
        return {"status": status, "application": na, "credit_record": nb}

    # ------------------------------------------------------------------ #
    #  Record-level compare                                                #
    # ------------------------------------------------------------------ #

    def compare_records(self, application: dict, credit_record: dict) -> dict:
        """
        Compare a normalized application record against a normalized credit
        record field by field.

        Returns:
            {
                "overall": "match" | "mismatch" | "missing",
                "fields": {
                    "<field>": {"status": ..., "application": ..., "credit_record": ...},
                    ...
                },
                "discrepancies": [list of field names that mismatched],
            }
        """
        _currency_fields = {"annual_revenue", "requested_amount", "equipment_cost"}
        comparators = {
            "business_name": self.compare_business_name,
            "ein":           self.compare_ein,
            "phone":         self.compare_phone,
            "credit_score":  self.compare_credit_score,
            "business_address": self.compare_address,
        }

        results = {}
        shared_keys = set(application) & set(credit_record)

        for key in shared_keys:
            av, cv = application[key], credit_record[key]
            if av is None and cv is None:
                results[key] = {"status": _MISSING, "application": av, "credit_record": cv}
            elif key in comparators:
                results[key] = comparators[key](av, cv)
            elif key in _currency_fields:
                results[key] = self.compare_currency(av, cv)
            else:
                # Generic equality for any other shared field
                status = _MATCH if av == cv else _MISMATCH
                results[key] = {"status": status, "application": av, "credit_record": cv}

        discrepancies = [k for k, v in results.items() if v["status"] == _MISMATCH]
        overall = _MISMATCH if discrepancies else (
            _MISSING if all(v["status"] == _MISSING for v in results.values()) else _MATCH
        )
        return {"overall": overall, "fields": results, "discrepancies": discrepancies}

 # Main normalization method that applies type-specific normalization to each field
    def normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Apply type-appropriate normalization to each field in a record."""
        out = {}
        for key, val in record.items():
            if val is None:
                out[key] = None
            elif key in {"business_name"}:
                out[key] = self.business_name(str(val))
            elif key in {"ein"}:
                out[key] = self.ein(str(val))
            elif key in {"phone"}:
                out[key] = self.phone(str(val))
            elif key in {"annual_revenue", "requested_amount", "equipment_cost"}:
                out[key] = self.currency(val)
            elif key in {"credit_score"}:
                out[key] = self.credit_score(val)
            elif key in {"business_address"}:
                out[key] = self.address(str(val))
            else:
                out[key] = val
        return out
