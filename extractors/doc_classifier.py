"""
LLM Document Classifier
Uses OpenAI to classify financial document types from extracted text.
Falls back to keyword matching when the LLM is unavailable or returns an
unrecognized label.
"""
import logging
from typing import Optional

import openai

from config import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

VALID_DOC_TYPES = [
    "tax_return",
    "bank_statement",
    "profit_loss",
    "balance_sheet",
    "accounts_receivable",
    "accounts_payable",
    "equipment_invoice",
    "personal_financial_statement",
    "unknown",
]

# Keyword fallback — mirrors financial_doc_extractor.DOC_TYPE_KEYWORDS
_KEYWORD_MAP: dict[str, list[str]] = {
    "tax_return":                    ["1040", "1120", "1065", "schedule c", "tax return", "irs form"],
    "bank_statement":                ["bank statement", "account statement", "checking", "savings", "deposit"],
    "profit_loss":                   ["profit & loss", "profit and loss", "p&l", "income statement", "statement of operations"],
    "balance_sheet":                 ["balance sheet", "statement of financial position", "assets and liabilities"],
    "accounts_receivable":           ["accounts receivable", "aging report", "a/r aging"],
    "accounts_payable":              ["accounts payable", "a/p aging"],
    "equipment_invoice":             ["invoice", "purchase order", "equipment quote", "bill of sale"],
    "personal_financial_statement":  ["personal financial statement", "pfs", "net worth statement"],
}

_SYSTEM_PROMPT = """\
You are a financial document classifier for a commercial equipment lending company.
Given a document's filename and a text excerpt, classify it into exactly one of these types:

  tax_return                  — IRS tax forms (1040, 1120, 1065, Schedule C, etc.)
  bank_statement              — Bank account statements (deposits, withdrawals, balances)
  profit_loss                 — P&L / income statement / statement of operations
  balance_sheet               — Balance sheet / statement of financial position
  accounts_receivable         — A/R aging reports
  accounts_payable            — A/P aging reports
  equipment_invoice           — Invoices, purchase orders, equipment quotes, bills of sale
  personal_financial_statement — Personal financial statements / net worth statements
  unknown                     — Cannot be determined from the provided text

Rules:
- Respond with ONLY the doc_type label from the list above — no punctuation, no explanation.
- If the text is empty or too short to classify, respond with: unknown
"""


def _keyword_classify(text: str, filename: str) -> str:
    combined = (text + " " + filename).lower()
    for doc_type, keywords in _KEYWORD_MAP.items():
        if any(kw in combined for kw in keywords):
            return doc_type
    return "unknown"


def classify_document(
    text: str,
    filename: str = "",
    max_chars: int = 2000,
) -> str:
    """
    Classify a financial document using OpenAI, falling back to keyword matching.

    Args:
        text:       Extracted text from the document.
        filename:   Original filename (used as an additional signal).
        max_chars:  How many characters of text to send to the LLM (keeps cost low).

    Returns:
        One of the VALID_DOC_TYPES strings.
    """
    # Fast path: keyword match before making an API call
    keyword_result = _keyword_classify(text, filename)
    if keyword_result != "unknown":
        logger.debug("doc_classifier: keyword match → %s (%s)", keyword_result, filename)
        return keyword_result

    # LLM path
    if not OPENAI_API_KEY:
        logger.warning("doc_classifier: OPENAI_API_KEY not set — returning keyword result.")
        return keyword_result

    excerpt = text[:max_chars].strip() if text else ""
    user_message = f"Filename: {filename}\n\nDocument excerpt:\n{excerpt}" if excerpt else f"Filename: {filename}\n\n(No text extracted)"

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=16,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
        )
        label = response.choices[0].message.content.strip().lower()

        if label in VALID_DOC_TYPES:
            logger.debug("doc_classifier: LLM → %s (%s)", label, filename)
            return label

        logger.warning(
            "doc_classifier: LLM returned unrecognized label %r for %s — defaulting to 'unknown'.",
            label, filename,
        )
        return "unknown"

    except Exception as e:
        logger.error("doc_classifier: LLM call failed for %s: %s — falling back to keyword result.", filename, e)
        return keyword_result
