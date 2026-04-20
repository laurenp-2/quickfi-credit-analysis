"""
Credit Summary Agent
Takes the unified output of ingest_documents() and calls OpenAI to produce a
structured credit summary with risk analysis, credit profile, suggestions, and
fraud detection.
"""
import json
import logging
from typing import Any

import openai

from config import OPENAI_API_KEY, OPENAI_MODEL
from prompts.summary import summary_prompt

logger = logging.getLogger(__name__)

# Max characters of raw document text to include per document.
# Keeps prompt size manageable while preserving the most relevant content.
_MAX_DOC_CHARS = 3000


# format the inputs

def _format_applicants(applicants: list) -> str:
    if not applicants:
        return "=== APPLICATION DATA ===\nNone provided.\n"
    lines = ["=== APPLICATION DATA ==="]
    for i, app in enumerate(applicants, 1):
        lines.append(f"\nApplicant {i}:")
        for k, v in app.items():
            if v is not None:
                lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def _format_ratios(ratios: dict) -> str:
    if not ratios:
        return "=== CALCULATED FINANCIAL RATIOS ===\nNone available.\n"
    lines = ["=== CALCULATED FINANCIAL RATIOS ==="]
    _skip = {"flags", "data_gaps", "overall_tier"}
    for name, result in ratios.items():
        if name in _skip:
            continue
        if isinstance(result, dict):
            val  = result.get("value")
            tier = result.get("tier", "unknown")
            lines.append(f"  {name}: {val}  (risk tier: {tier})")
    lines.append(f"\n  Overall Risk Tier : {ratios.get('overall_tier', 'unknown')}")
    if ratios.get("flags"):
        lines.append(f"  Flags             : {', '.join(ratios['flags'])}")
    if ratios.get("data_gaps"):
        lines.append(f"  Data Gaps         : {', '.join(ratios['data_gaps'])}")
    return "\n".join(lines)


def _format_credit_records(credit: list) -> str:
    if not credit:
        return "=== CREDIT RECORDS ===\nNone provided.\n"
    lines = ["=== CREDIT RECORDS ==="]
    for record in credit:
        lines.append(f"\nSource: {record.get('source_file', 'unknown')}")
        for k, v in record.get("fields", {}).items():
            if v is not None:
                lines.append(f"  {k}: {v}")
        trade_lines = record.get("trade_lines", [])
        if trade_lines:
            lines.append(f"  Trade Lines ({len(trade_lines)}):")
            for tl in trade_lines[:10]:
                lines.append(
                    f"    - {tl.get('creditor')}: "
                    f"balance {tl.get('balance')}, status {tl.get('status')}"
                )
    return "\n".join(lines)


def _format_documents(documents: list) -> str:
    if not documents:
        return "=== FINANCIAL DOCUMENTS ===\nNone provided.\n"
    lines = ["=== FINANCIAL DOCUMENTS ==="]
    for doc in documents:
        lines.append(
            f"\nDocument : {doc.get('filename')}  "
            f"(type: {doc.get('doc_type')}, "
            f"chars: {doc.get('char_count', 0)}, "
            f"ocr: {doc.get('used_ocr', False)})"
        )
        text = (doc.get("raw_text") or "")[:_MAX_DOC_CHARS]
        lines.append(text if text else "(no text extracted)")
    return "\n".join(lines)



def generate_credit_summary(ingest_result: dict) -> dict:
    """
    Generate a structured credit summary from the output of ingest_documents().

    Args:
        ingest_result: dict returned by utils.ingest.ingest_documents(), containing
                       keys: applicants, credit, documents, financials, ratios.

    Returns:
        Parsed dict with keys:
          "Risk Analysis", "Credit Profile", "Suggestions", "Fraud Detection"

    Raises:
        RuntimeError: if the OpenAI call fails or the response cannot be parsed.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set — cannot generate credit summary.")

    input_text = "\n\n".join([
        _format_applicants(ingest_result.get("applicants", [])),
        _format_ratios(ingest_result.get("ratios", {})),
        _format_credit_records(ingest_result.get("credit", [])),
        _format_documents(ingest_result.get("documents", [])),
    ])

    full_prompt = summary_prompt + input_text

    logger.info("generate_credit_summary: calling %s …", OPENAI_MODEL)

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {"role": "system", "content": full_prompt},
                {"role": "user",   "content": "Generate the credit summary now."},
            ],
        )
    except openai.OpenAIError as e:
        logger.error("generate_credit_summary: OpenAI call failed: %s", e)
        raise RuntimeError(f"OpenAI call failed: {e}") from e

    raw = response.choices[0].message.content

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("generate_credit_summary: could not parse JSON response: %s", e)
        raise RuntimeError(f"Failed to parse LLM response as JSON: {e}") from e

    logger.info(
        "generate_credit_summary: done — risk=%s",
        result.get("Risk Analysis", "unknown"),
    )
    return result
