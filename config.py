"""
Central configuration. All env vars are read here; nothing else imports os.environ directly.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM ────────────────────────────────────────────────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic").lower()
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# ── App ─────────────────────────────────────────────────────────────────────
APP_ENV: str = os.getenv("APP_ENV", "development")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
OCR_ENABLED: bool = os.getenv("OCR_ENABLED", "true").lower() == "true"

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MOCK_DIR = os.path.join(DATA_DIR, "mock")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# ── Risk thresholds (commercial equipment finance defaults — adjust as needed) ──
RISK_THRESHOLDS = {
    "dscr": {
        "low_risk": 1.35,      # >= 1.35x  → low risk
        "medium_risk": 1.10,   # 1.10–1.34 → medium risk
        # below 1.10            → high risk
    },
    "credit_score": {
        "low_risk": 700,
        "medium_risk": 620,
    },
    "time_in_business_years": {
        "low_risk": 5,
        "medium_risk": 2,
    },
    "debt_to_equity": {
        "low_risk": 2.0,       # <= 2.0x   → low risk
        "medium_risk": 4.0,    # 2.0–4.0   → medium risk
    },
    "current_ratio": {
        "low_risk": 1.5,
        "medium_risk": 1.0,
    },
}
