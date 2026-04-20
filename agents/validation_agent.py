# agents/validation_agent.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from extractors import SpreadsheetExtractor, CreditReportExtractor


@dataclass
class MatchResult:
    source_file: str
    score: int
    confidence: str
    matched_fields: list[str]
    mismatched_fields: list[str]
    missing_fields: list[str]


class ValidationAgent:
    """
    Compare application input data against one or more credit records
    to validate that the correct record was pulled.
    """

    IDENTITY_FIELDS = [
        "ein",
        "business_name",
        "owner_name",
        "business_address",
        "phone",
    ]

    COMPARISON_FIELDS = [
        "ein",
        "business_name",
        "owner_name",
        "business_address",
        "phone",
        "annual_revenue",
        "year_founded",
    ]

    FIELD_WEIGHTS = {
        "ein": 50,
        "business_name": 25,
        "owner_name": 15,
        "business_address": 10,
        "phone": 10,
    }

    def run(
        self,
        application_file: str | Path,
        credit_record_files: list[str | Path],
    ) -> dict[str, Any]:
        application_data = self._extract_application_data(application_file)

        if not credit_record_files:
            raise ValueError("credit_record_files must contain at least one file")

        extracted_credit_records = [
            CreditReportExtractor(file_path).extract()
            for file_path in credit_record_files
        ]

        scored_matches: list[tuple[dict[str, Any], MatchResult]] = []
        for credit_record in extracted_credit_records:
            match_result = self._score_credit_record(application_data, credit_record)
            scored_matches.append((credit_record, match_result))

        best_credit_record, best_match = max(scored_matches, key=lambda x: x[1].score)
        best_credit_fields = best_credit_record.get("fields", {})

        field_comparisons = self._compare_fields(application_data, best_credit_fields)
        overall_result = self._determine_overall_result(best_match.score, field_comparisons)

        return {
            "application_source_file": str(application_file),
            "matched_credit_record": best_match.source_file,
            "match_score": best_match.score,
            "match_confidence": best_match.confidence,
            "overall_result": overall_result,
            "application_data": application_data,
            "matched_credit_record_data": best_credit_fields,
            "field_comparisons": field_comparisons,
            "identity_match_summary": {
                "matched_fields": best_match.matched_fields,
                "mismatched_fields": best_match.mismatched_fields,
                "missing_fields": best_match.missing_fields,
            },
        }

    def _extract_application_data(self, application_file: str | Path) -> dict[str, Any]:
        path = Path(application_file)
        suffix = path.suffix.lower()

        if suffix in {".csv", ".xlsx", ".xls"}:
            records = SpreadsheetExtractor(path).extract()
            if not records:
                raise ValueError(f"No application records found in {path}")
            return records[0]

        raise ValueError(
            f"Unsupported application file type: {suffix}. "
            "Use CSV or Excel with SpreadsheetExtractor."
        )

    def _score_credit_record(
        self,
        application_data: dict[str, Any],
        credit_record: dict[str, Any],
    ) -> MatchResult:
        credit_fields = credit_record.get("fields", {})
        source_file = credit_record.get("source_file", "unknown")

        score = 0
        matched_fields: list[str] = []
        mismatched_fields: list[str] = []
        missing_fields: list[str] = []

        for field in self.IDENTITY_FIELDS:
            app_val = self._normalize_value(field, application_data.get(field))
            credit_val = self._normalize_value(field, credit_fields.get(field))

            if not app_val or not credit_val:
                missing_fields.append(field)
                continue

            if self._values_match(field, app_val, credit_val):
                score += self.FIELD_WEIGHTS.get(field, 0)
                matched_fields.append(field)
            else:
                mismatched_fields.append(field)

        confidence = self._score_to_confidence(score)

        return MatchResult(
            source_file=source_file,
            score=score,
            confidence=confidence,
            matched_fields=matched_fields,
            mismatched_fields=mismatched_fields,
            missing_fields=missing_fields,
        )

    def _compare_fields(
        self,
        application_data: dict[str, Any],
        credit_fields: dict[str, Any],
    ) -> list[dict[str, Any]]:
        comparisons: list[dict[str, Any]] = []

        for field in self.COMPARISON_FIELDS:
            app_val_raw = application_data.get(field)
            credit_val_raw = credit_fields.get(field)

            app_val = self._normalize_value(field, app_val_raw)
            credit_val = self._normalize_value(field, credit_val_raw)

            if self._is_blank(app_val_raw) and self._is_blank(credit_val_raw):
                status = "missing_both"
            elif self._is_blank(app_val_raw):
                status = "missing_in_application"
            elif self._is_blank(credit_val_raw):
                status = "missing_in_credit_record"
            elif self._values_match(field, app_val, credit_val):
                status = "match"
            else:
                status = "mismatch"

            comparisons.append(
                {
                    "field": field,
                    "application_value": app_val_raw,
                    "credit_value": credit_val_raw,
                    "status": status,
                }
            )

        return comparisons

    def _determine_overall_result(
        self,
        match_score: int,
        field_comparisons: list[dict[str, Any]],
    ) -> str:
        mismatches = [row for row in field_comparisons if row["status"] == "mismatch"]

        if match_score < 50:
            return "likely_wrong_credit_record"
        if mismatches:
            return "matched_with_discrepancies"
        return "matched_cleanly"

    def _score_to_confidence(self, score: int) -> str:
        if score >= 80:
            return "high"
        if score >= 50:
            return "medium"
        return "low"

    def _values_match(self, field: str, left: Any, right: Any) -> bool:
        if left is None or right is None:
            return False
        return left == right

    def _normalize_value(self, field: str, value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return value

        text = str(value).strip()
        if not text:
            return None

        if field == "ein":
            digits = "".join(ch for ch in text if ch.isdigit())
            return digits or None

        if field == "phone":
            digits = "".join(ch for ch in text if ch.isdigit())
            return digits or None

        if field in {"business_name", "owner_name"}:
            text = text.upper().replace(",", "").replace(".", "").replace("&", "AND")
            text = " ".join(text.split())
            for suffix in [" LLC", " INC", " LTD", " CORP", " CORPORATION", " CO"]:
                if text.endswith(suffix):
                    text = text[: -len(suffix)].strip()
            return text

        if field == "business_address":
            text = text.upper().replace(",", "").replace(".", "")
            return " ".join(text.split())

        if field == "annual_revenue":
            cleaned = "".join(ch for ch in text if ch.isdigit() or ch == ".")
            try:
                return float(cleaned) if cleaned else None
            except ValueError:
                return None

        if field == "year_founded":
            digits = "".join(ch for ch in text if ch.isdigit())
            try:
                return int(digits) if digits else None
            except ValueError:
                return None

        return " ".join(text.split()).upper()

    def _is_blank(self, value: Any) -> bool:
        return value is None or str(value).strip() == ""