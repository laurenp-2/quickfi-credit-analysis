# QuickFi Credit Agent

AI-powered credit validation and risk analysis for commercial equipment finance.

## What It Does

**Validation** — Compares a credit application's manually entered data against pulled credit records to catch mismatches (wrong EIN, inflated revenue, credit score discrepancies, etc.)

**Credit Summary** — Analyzes a borrower's financial documents to produce a risk report including:
- Risk Analysis (Low / Medium / High)
- Credit Profile (key datapoints driving the rating)
- Suggestions (missing docs, ways to improve the profile)
- Fraud / doctored document detection

## Quick Start

```bash
# 1. Copy and fill in your API key
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate mock test data
python data/mock/generate_mock_data.py

# 4. Run the app
streamlit run app.py
```

## Project Structure

```
quickfi/
├── app.py                    # Streamlit UI (Validation + Credit Summary modes)
├── config.py                 # Env vars, LLM settings, risk thresholds
├── requirements.txt
├── extractors/
│   ├── spreadsheet_extractor.py    # Reads credit application Excel/CSV
│   ├── credit_report_extractor.py  # Parses credit record PDFs
│   └── financial_doc_extractor.py  # Unpacks zip archives, OCR fallback
├── normalizers/
│   └── data_normalizer.py          # Standardizes EIN, names, currency, etc.
├── agents/                   # Validation + Credit Summary pipelines 
├── prompts/                  # LLM prompt templates 
├── data/mock/                # Generated test data (run generate_mock_data.py)
└── tests/                    # Pytest suite
```

## Running Tests

```bash
pytest tests/ -v
```

## Environment Variables

| Variable | Description |
|---|---|
| `LLM_PROVIDER` | `anthropic` or `openai` |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `OPENAI_MODEL` | Default: `gpt-4o` |

