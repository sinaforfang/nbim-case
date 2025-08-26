import pandas as pd

NBIM_MAP = {
    "COAC_EVENT_KEY": "event_key",
    "ISIN": "isin",
    "EXDATE": "ex_date",
    "PAYMENT_DATE": "pay_date",
    "CUSTODIAN": "custodian",
    "BANK_ACCOUNT": "account",
    "NOMINAL_BASIS": "nominal",
    "DIVIDENDS_PER_SHARE": "div_ps",
    "GROSS_AMOUNT_QUOTATION": "gross_qc",
    "NET_AMOUNT_QUOTATION": "net_qc",
    "NET_AMOUNT_SETTLEMENT": "net_sc",
    "WTHTAX_COST_QUOTATION": "tax_amt",
    #"WTHTAX_RATE": "tax_rate",
    "TOTAL_TAX_RATE": "tax_rate",
    #"AVG_FX_RATE_QUOTATION_TO_PORTFOLIO": "fx_rate",  uses NOK
    "QUOTATION_CURRENCY": "qc",
    "SETTLEMENT_CURRENCY": "sc",
}

CUST_MAP = {
    "COAC_EVENT_KEY": "event_key",
    "ISIN": "isin",
    #"EX_DATE": "ex_date",
    "EVENT_EX_DATE": "ex_date",
    #"PAY_DATE": "pay_date",
    "EVENT_PAYMENT_DATE": "pay_date",
    "CUSTODIAN": "custodian",
    "CUSTODY": "account",
    "NOMINAL_BASIS": "nominal",
    "DIV_RATE": "div_ps",
    "GROSS_AMOUNT": "gross_qc",
    "NET_AMOUNT_QC": "net_qc",
    "NET_AMOUNT_SC": "net_sc",
    "TAX": "tax_amt",
    "TAX_RATE": "tax_rate", 
    #"FX_RATE": "fx_rate", uses USD
    "CURRENCIES": "qc",
    "SETTLED_CURRENCY": "sc",
}

DATE_COLS = {"ex_date", "pay_date"}
NUM_COLS  = ["nominal","div_ps","gross_qc","net_qc","net_sc","tax_amt","tax_rate"]

def to_canonical(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    out = df.copy()
    out.columns = [c.strip().upper() for c in out.columns]
    use = [c for c in out.columns if c in mapping]
    out = out[use].rename(columns=mapping)
    # Fill missing expected columns
    for col in set(NBIM_MAP.values()) | set(CUST_MAP.values()):
        if col not in out.columns:
            out[col] = pd.NA
    # Parse dates
    for c in DATE_COLS:
        out[c] = pd.to_datetime(out[c], errors="coerce", utc=True, dayfirst=True)
    # Numeric coercion
    for c in NUM_COLS:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    # Strings tidy
    for c in ["qc","sc","custodian","isin"]:
        out[c] = out[c].astype(str).str.strip().str.upper()
    # Keep only the first currency as the other one is in sc
    if "qc" in out.columns:
        out["qc"] = out["qc"].str.split(" ").str[0]
        # turn empty strings into <NA>
        out["qc"] = out["qc"].where(out["qc"].str.len() > 0, pd.NA)
    
    return out
