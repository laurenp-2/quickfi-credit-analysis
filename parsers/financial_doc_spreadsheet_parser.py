from pydoc import text
import extractors
import re
from datetime import date

def get_financial_info(file_financial_docs: str, file_spreadsheet: str) -> dict[str, Any]:
    financial_info = {}
    parse_financial_docs(file_financial_docs, financial_info)
    parse_spreadsheet(file_spreadsheet, financial_info)
    return financial_info

def parse_financial_docs(file_path: str, financial_info: dict[str, Any]) -> None:
    data = extractors.FinancialDocExtractor(file_path)
    docs = data.extract()
    

    P_and_L_parse(docs, financial_info)
    balance_sheet_parse(docs, financial_info)
    bank_statement_parse(docs, financial_info)
    tax_return_parse(docs, financial_info)
    personal_financial_statement_parse(docs, financial_info)

def parse_spreadsheet(file_path: str, financial_info: dict[str, Any]) -> None:
    data = extractors.SpreadsheetExtractor(file_path)
    result = data.extract()

    financial_info["loan_amount"] = result.get('requested_amount')
    financial_info["annual_revenue"] = result.get('annual_revenue')



def P_and_L_parse(docs: list[dict[str, Any]], financial_info: dict[str, Any]) -> None:
    for doc in docs: 
        if doc['doc_type'] == 'profit_loss': 
            text = doc['raw_text'].lower()
            
            financial_info['gross_revenue'] = search(r"gross revenue|total revenue|net sales", text)
            financial_info['cogs'] = search(r"cost of goods sold", text)
            financial_info['net_income'] = search(r"net income|net profit|net earnings", text)
            financial_info["net_operating_income"] = search(r"operating income|income from operations|ebit", text)
            financial_info["prior_year_revenue"] = search(f"{date.today().year - 1}", text)
            financial_info["prior_year_net_income"] = search(f"{date.today().year - 1}", text)

def balance_sheet_parse(docs: list[dict[str, Any]], financial_info: dict[str, Any]) -> None:
    for doc in docs: 
        if doc['doc_type'] == 'balance_sheet': 
            text = doc['raw_text'].lower()
            
            financial_info['current_assets'] = search(r"current assets", text)
            financial_info['current_liabilities'] = search(r"current liabilities", text)
            financial_info['total_debt'] = search(r"total debt", text)
            financial_info['total_equity'] = search(r"total equity", text)

def bank_statement_parse(docs: list[dict[str, Any]], financial_info: dict[str, Any]) -> None:
    for doc in docs: 
        if doc['doc_type'] == 'bank_statement': 
            text = doc['raw_text'].lower()
            
            financial_info['avg_balance'] = search(r"average (?:daily )?balance|avg (?:daily )?balance", text)
            financial_info['nsf_count'] = len(
            re.findall(
                r"nsf fee|non.sufficient funds|returned item",
                text
            )
            )            
            financial_info['total_debt_service'] = search(r"total debt service", text)


#fallbacks 
def tax_return_parse(docs: list[dict[str, Any]], financial_info: dict[str, Any]) -> None:
    for doc in docs: 
        if doc['doc_type'] == 'tax_return': 
            text = doc['raw_text'].lower()
            
            if not financial_info.get('gross_revenue'):
                financial_info['gross_revenue'] = search(r"gross revenue|total revenue|net sales|gross receipts", text) 
            if not financial_info.get('net_income'):
                financial_info['net_income'] = search(r"net income|net profit|net earnings", text)
            if not financial_info.get('cogs'):
                financial_info['cogs'] = search(r"cost of goods sold", text) or search(r"cost of sales", text)
            if not financial_info.get('total_debt'):
                financial_info['total_debt'] = search(r"total debt", text) or search(r"debt", text)
            if not financial_info.get('total_debt_service'):
                financial_info['total_debt_service'] = search(r"total debt service", text) or search(r"debt service", text)
def personal_financial_statement_parse(docs: list[dict[str, Any]], financial_info: dict[str, Any]) -> None:
    for doc in docs: 
        if doc['doc_type'] == 'personal_financial_statement': 
            text = doc['raw_text'].lower()
            
            if not financial_info.get('total_equity'):
                financial_info['total_equity'] = search(r"total equity", text) or search(r"net worth", text)
            if not financial_info.get('total_debt'):
                financial_info['total_debt'] = search(r"total debt", text) or search(r"debt", text)
            if not financial_info.get('current_assets'):
                financial_info['current_assets'] = search(r"current assets", text) or search(r"assets", text)
#helpers 
def clean(text) -> Optional[float]:
  val = text.group(1).replace(",","").replace("$","").strip()
  try: return float(val)
  except ValueError: return None

def search(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern + "[^\n]*?([\$]?\s*[\d,]+(?:\.\d+)?)", text)
    return clean(match) if match else None