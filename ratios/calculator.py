def dscr(noi, debt_service):
    if not noi or not debt_service: return {"value": None, "tier": "unknown"}
    val = round(noi / debt_service, 2)
    tier = "low" if val >= 1.25 else "medium" if val >= 1.0 else "high"
    return {"value": val, "tier": tier}

def current_ratio(current_assets, current_liabilities):
    if not current_assets or not current_liabilities: return {"value": None, "tier": "unknown"}
    val = round(current_assets / current_liabilities, 2)
    tier = "low" if val >= 1.5 else "medium" if val >= 1.0 else "high"
    return {"value": val, "tier": tier}

def debt_to_equity_ratio(total_liabilities, total_equity):
    if not total_liabilities or not total_equity: return {"value": None, "tier": "unknown"}
    val = round(total_liabilities / total_equity, 2)
    tier = "low" if val <= 2.0 else "medium" if val <= 4.0 else "high"
    return {"value": val, "tier": tier}

def gross_margin(revenue, cogs): 
    if not revenue or not cogs: return {"value": None, "tier": "unknown"}
    val = round((revenue - cogs) / revenue * 100, 2)
    tier = "low" if val >= 40 else "medium" if val >= 20 else "high"
    return {"value": val, "tier": tier}

def net_margin(net_income, revenue):
    if not net_income or not revenue: return {"value": None, "tier": "unknown"}
    val = round(net_income / revenue * 100, 2)
    tier = "low" if val >= 10 else "medium" if val >= 0 else "high"
    return {"value": val, "tier": tier}

def yoy_growth(current_year, prior_year):
    if not current_year or not prior_year: return {"value": None, "tier": "unknown"}
    val = round((current_year - prior_year) / prior_year *100, 2)
    tier = "low" if val >= 5 else "medium" if val >= -5 else "high"
    return {"value": val, "tier": tier}

def loan_to_revenue(loan_amount, revenue):
    if not loan_amount or not revenue: return {"value": None, "tier": "unknown"}
    val = round(loan_amount / revenue * 100, 2)
    tier = "low" if val <= 20 else "medium" if val <= 50 else "high"
    return {"value": val, "tier": tier}

def NSF_flag_avg_balance(nsf_count, avg_balance):
    if nsf_count is None or avg_balance is None: return {"value": None, "tier": "unknown"}
    val = {"nsf_count": nsf_count, "avg_balance": avg_balance}
    tier = "low" if nsf_count == 0 else "medium" if nsf_count <= 2 else "high"
    return {"value": val, "tier": tier}

def calculate_all(f: dict) -> dict:
    results = {}
    gaps = []
    flags = []

    results["dscr"] = dscr(f.get("net_operating_income"), f.get("total_debt_service"))
    if results["dscr"]["value"] is None: gaps.append("net_operating_income or debt_service")

    results["current_ratio"] = current_ratio(f.get("current_assets"), f.get("current_liabilities"))
    if results["current_ratio"]["value"] is None: gaps.append("current_assets or current_liabilities")

    results["debt_to_equity"] = debt_to_equity_ratio(f.get("total_liabilities"), f.get("total_equity"))
    if results["debt_to_equity"]["value"] is None: gaps.append("total_liabilities or total_equity")

    results["gross_margin"] = gross_margin(f.get("revenue"), f.get("cogs"))
    if results["gross_margin"]["value"] is None: gaps.append("revenue or cogs")

    results["net_margin"] = net_margin(f.get("net_income"), f.get("revenue"))       
    if results["net_margin"]["value"] is None: gaps.append("net_income or revenue")

    results["yoy_growth"] = yoy_growth(f.get("current_year_revenue"), f.get("prior_year_revenue"))
    if results["yoy_growth"]["value"] is None: gaps.append("current_year_revenue or prior_year_revenue")

    results["loan_to_revenue"] = loan_to_revenue(f.get("loan_amount"), f.get("revenue"))
    if results["loan_to_revenue"]["value"] is None: gaps.append("loan_amount or revenue")

    results["NSF_flag_avg_balance"] = NSF_flag_avg_balance(f.get("nsf_count"), f.get("avg_balance"))
    if results["NSF_flag_avg_balance"]["value"] is None: gaps.append("nsf_count or avg_balance")

    # NSF flag — direct check, no formula
    nsf = f.get("nsf_count", 0)
    if nsf >= 3: flags.append(f"{nsf}_nsfs")

    # overall tier = worst single ratio tier
    tiers = [r["tier"] for r in results.values() if r["tier"] != "unknown"]
    results["overall_tier"] = "high" if "high" in tiers else "medium" if "medium" in tiers else "low"
    results["flags"] = flags
    results["data_gaps"] = gaps
    return results
