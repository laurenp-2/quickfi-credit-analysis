"""
Data Normalizer 
Cleans and standardizes extracted values so the validation agent
can do apples-to-apples comparisons between application data and credit records.
"""
import re
from typing import Any, Optional, Union


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
