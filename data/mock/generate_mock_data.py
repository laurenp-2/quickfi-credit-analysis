"""
Generate all mock test data for extractor testing.
Run from project root:  python data/mock/generate_mock_data.py

Creates:
  - data/mock/input_data/clean_application.csv
  - data/mock/input_data/mismatched_application.csv
  - data/mock/credit_records/  (text files simulating PDF content)
  - data/mock/financial_docs/  (zip files with mock financial statements as text/PDFs)
"""
import csv
import io
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
INPUT_DIR = ROOT / "input_data"
CREDIT_DIR = ROOT / "credit_records"
FIN_DIR = ROOT / "financial_docs"

for d in [INPUT_DIR, CREDIT_DIR, FIN_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ── 1. Input Data Spreadsheets ──────────────────────────────────────────────

HEADERS = [
    "Business Name", "DBA", "EIN", "Business Address", "City", "State", "Zip Code",
    "Phone", "Owner Name", "SSN Last 4", "Date of Birth", "Time in Business",
    "Business Start Date", "Annual Revenue", "Requested Amount", "Equipment Type",
    "Equipment Cost", "Business Type", "Industry", "Credit Score",
]

CLEAN_ROW = [
    "Apex Trucking LLC", "Apex Freight", "82-4567890",
    "4400 Industrial Blvd", "Dallas", "TX", "75247",
    "214-555-0192", "James R. Mitchell", "7731", "03/14/1978",
    "8 years", "01/15/2016", "2,400,000", "185,000",
    "Semi-Truck (Peterbilt 579)", "210,000", "LLC", "Trucking / Transportation", "724",
]

# Mismatched row: EIN, credit score, and revenue deliberately differ from "credit record"
MISMATCHED_ROW = [
    "Apex Trucking LLC", "Apex Freight", "82-9999999",   # ← wrong EIN
    "4400 Industrial Blvd", "Dallas", "TX", "75247",
    "214-555-0192", "James R. Mitchell", "7731", "03/14/1978",
    "8 years", "01/15/2016", "3,800,000",               # ← inflated revenue
    "185,000", "Semi-Truck (Peterbilt 579)", "210,000",
    "LLC", "Trucking / Transportation", "689",           # ← lower credit score
]

def write_csv(path: Path, headers: list, row: list):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(row)
    print(f"  Created: {path.relative_to(ROOT.parent.parent)}")

write_csv(INPUT_DIR / "clean_application.csv", HEADERS, CLEAN_ROW)
write_csv(INPUT_DIR / "mismatched_application.csv", HEADERS, MISMATCHED_ROW)


# ── 2. Credit Records (mock PDF text content) ───────────────────────────────
# In real usage these are PDFs; here we write .txt files with the same structure
# so the extractors can be tested without PDF generation dependencies.

CREDIT_RECORDS = {
    "credit_record_apex_trucking.txt": """
BUSINESS CREDIT REPORT
Source: Experian Business Credit

Business Name: Apex Trucking LLC
EIN: 82-4567890
Address: 4400 Industrial Blvd, Dallas, TX 75247
Business Type: LLC
Industry: Trucking / Transportation
Years in Business: 8
Date Established: January 2016

CREDIT SUMMARY
Credit Score: 724
Paydex Score: 78
Days Beyond Terms (DBT): 4

TRADE LINES
BANK OF AMERICA COMMERCIAL LENDING
  Balance: $142,000  Status: Current  High Credit: $185,000
WELLS FARGO EQUIPMENT FINANCE
  Balance: $67,000   Status: Current  High Credit: $90,000
PACCAR FINANCIAL
  Balance: $28,000   Status: Current  High Credit: $35,000

PUBLIC RECORDS: 0
INQUIRIES: 3 (last 12 months)

OWNER / PRINCIPAL
Owner: James R. Mitchell
SSN: *****7731
Date of Birth: 03/14/1978
Personal Credit Score: 724
""",

    "credit_record_mismatched.txt": """
BUSINESS CREDIT REPORT
Source: Experian Business Credit

Business Name: Apex Trucking LLC
EIN: 82-4567890          <- NOTE: application submitted EIN 82-9999999
Address: 4400 Industrial Blvd, Dallas, TX 75247
Business Type: LLC
Industry: Trucking / Transportation
Years in Business: 8
Date Established: January 2016

CREDIT SUMMARY
Credit Score: 724         <- NOTE: application stated 689
Paydex Score: 78
Days Beyond Terms (DBT): 4

FINANCIAL HIGHLIGHTS
Annual Revenue (reported): $2,400,000  <- NOTE: application stated $3,800,000

OWNER / PRINCIPAL
Owner: James R. Mitchell
SSN: *****7731
Date of Birth: 03/14/1978
""",
}

for fname, content in CREDIT_RECORDS.items():
    path = CREDIT_DIR / fname
    path.write_text(content.strip())
    print(f"  Created: {path.relative_to(ROOT.parent.parent)}")


# ── 3. Financial Document Zip Files ─────────────────────────────────────────

def make_zip(zip_path: Path, files: dict[str, str]):
    """files: {filename: text_content}"""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    print(f"  Created: {zip_path.relative_to(ROOT.parent.parent)}")


# ── Healthy Borrower ────────────────────────────────────────────────────────
make_zip(FIN_DIR / "healthy_borrower.zip", {
    "profit_loss_2023.txt": """
PROFIT & LOSS STATEMENT
Business: Apex Trucking LLC
Period: January 1 – December 31, 2023

REVENUE
  Freight Revenue:           $2,400,000
  Fuel Surcharge Income:       $180,000
  Total Revenue:             $2,580,000

EXPENSES
  Driver Wages & Benefits:     $980,000
  Fuel:                        $420,000
  Maintenance & Repairs:        $95,000
  Insurance:                   $112,000
  Depreciation:                 $88,000
  Lease/Finance Payments:      $156,000
  Administrative:               $62,000
  Total Expenses:            $1,913,000

NET INCOME:                    $667,000
""",
    "balance_sheet_2023.txt": """
BALANCE SHEET
Business: Apex Trucking LLC
As of December 31, 2023

ASSETS
  Cash & Equivalents:          $312,000
  Accounts Receivable:         $198,000
  Prepaid Expenses:             $24,000
  Total Current Assets:        $534,000

  Equipment (net of depreciation): $820,000
  Real Property:               $0
  Total Long-Term Assets:      $820,000

TOTAL ASSETS:                $1,354,000

LIABILITIES
  Accounts Payable:             $68,000
  Current Portion Long-Term Debt: $104,000
  Total Current Liabilities:   $172,000

  Long-Term Debt:              $338,000
  Total Long-Term Liabilities: $338,000

TOTAL LIABILITIES:             $510,000
OWNER EQUITY:                  $844,000
TOTAL LIABILITIES + EQUITY:  $1,354,000
""",
    "bank_statement_oct_2023.txt": """
BANK STATEMENT
Institution: Bank of America
Account: Business Checking ****4821
Period: October 1–31, 2023

Opening Balance:   $287,450.00
Total Deposits:    $214,800.00
Total Withdrawals: $190,250.00
Closing Balance:   $312,000.00

Average Daily Balance: $295,680.00

No NSF items. No overdrafts.
""",
})


# ── Borderline Borrower ─────────────────────────────────────────────────────
make_zip(FIN_DIR / "borderline_borrower.zip", {
    "profit_loss_2023.txt": """
PROFIT & LOSS STATEMENT
Business: SunState Landscaping LLC
Period: January 1 – December 31, 2023

REVENUE
  Service Revenue:             $740,000
  Total Revenue:               $740,000

EXPENSES
  Labor:                       $320,000
  Equipment Lease:              $96,000
  Insurance:                    $48,000
  Fuel & Supplies:              $72,000
  Administrative:               $44,000
  Depreciation:                 $38,000
  Loan Payments:               $108,000
  Total Expenses:              $726,000

NET INCOME:                     $14,000
""",
    "balance_sheet_2023.txt": """
BALANCE SHEET
Business: SunState Landscaping LLC
As of December 31, 2023

ASSETS
  Cash:                         $22,000
  Accounts Receivable:          $68,000
  Total Current Assets:         $90,000

  Equipment (net):             $184,000
  Total Assets:                $274,000

LIABILITIES
  Accounts Payable:             $41,000
  Current Debt:                 $88,000
  Total Current Liabilities:   $129,000

  Long-Term Debt:              $102,000
TOTAL LIABILITIES:             $231,000
OWNER EQUITY:                   $43,000
""",
    "bank_statement_oct_2023.txt": """
BANK STATEMENT
Institution: First National Bank
Account: Business Checking ****2209
Period: October 1–31, 2023

Opening Balance:    $18,200.00
Total Deposits:     $62,400.00
Total Withdrawals:  $58,600.00
Closing Balance:    $22,000.00

NSF Items: 2
Average Daily Balance: $19,840.00
""",
})


# ── Distressed Borrower ─────────────────────────────────────────────────────
make_zip(FIN_DIR / "distressed_borrower.zip", {
    "profit_loss_2023.txt": """
PROFIT & LOSS STATEMENT
Business: Redrock Construction Inc
Period: January 1 – December 31, 2023

REVENUE
  Contract Revenue:            $920,000
  Total Revenue:               $920,000

EXPENSES
  Labor:                       $510,000
  Materials:                   $220,000
  Equipment Lease:             $144,000
  Insurance:                    $68,000
  Administrative:               $58,000
  Depreciation:                 $62,000
  Loan/Finance Payments:       $168,000
  Total Expenses:            $1,230,000

NET LOSS:                     ($310,000)
""",
    "balance_sheet_2023.txt": """
BALANCE SHEET
Business: Redrock Construction Inc
As of December 31, 2023

ASSETS
  Cash:                          $8,200
  Accounts Receivable:         $142,000
  Total Current Assets:        $150,200

  Equipment (net):             $320,000
  Total Assets:                $470,200

LIABILITIES
  Accounts Payable:            $188,000
  Current Debt:                $210,000
  Total Current Liabilities:   $398,000

  Long-Term Debt:              $290,000
TOTAL LIABILITIES:             $688,000
OWNER EQUITY:                 ($217,800)   <- Negative equity
""",
    "bank_statement_oct_2023.txt": """
BANK STATEMENT
Institution: Chase Business Banking
Account: Business Checking ****7704
Period: October 1–31, 2023

Opening Balance:     $3,100.00
Total Deposits:     $74,200.00
Total Withdrawals:  $69,100.00
Closing Balance:     $8,200.00

NSF Items: 7
Average Daily Balance: $5,420.00
""",
})


# ── Doctored Document (fraudulent — revenue numbers inconsistent) ───────────
make_zip(FIN_DIR / "doctored_document.zip", {
    "profit_loss_2023_ALTERED.txt": """
PROFIT & LOSS STATEMENT
Business: Granite Peak Logistics LLC
Period: January 1 – December 31, 2023

NOTE FOR REVIEWERS: Metadata indicates this document was last modified
in Adobe Acrobat on 2024-02-14, 11 months after the statement period end date.
Font inconsistencies detected on revenue line items.

REVENUE
  Freight Revenue:           $4,200,000   <- (bank deposits suggest ~$1.1M actual)
  Total Revenue:             $4,200,000

EXPENSES
  Driver Wages:              $1,800,000
  Fuel:                        $680,000
  Insurance:                   $210,000
  Admin:                        $95,000
  Total Expenses:            $2,785,000

NET INCOME:                  $1,415,000

--- FRAUD INDICATORS ---
1. Revenue figure ($4.2M) is inconsistent with bank statement deposits ($1.1M).
2. Document modified date is 11 months post-period.
3. Font on revenue rows differs from expense rows (metadata mismatch).
4. No tax return provided to corroborate revenue claim.
""",
    "bank_statement_oct_2023.txt": """
BANK STATEMENT
Institution: Lone Star Credit Union
Account: Business Checking ****5581
Period: October 1–31, 2023

Opening Balance:    $41,200.00
Total Deposits:     $91,800.00     <- annualized ~$1.1M, far below P&L claim
Total Withdrawals:  $88,400.00
Closing Balance:    $44,600.00

Average Daily Balance: $43,100.00
""",
})

print("\nAll mock data generated successfully.")
