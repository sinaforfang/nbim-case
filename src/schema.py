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
    #"EX_DATE": "ex_date", two of ex date
    "EVENT_EX_DATE": "ex_date",
    #"PAY_DATE": "pay_date", two of pay date
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
    # return a df with consistent canonical schema based on nbim and custody using mapping
    out = df.copy()
    out.columns = [c.strip().upper() for c in out.columns]
    use = [c for c in out.columns if c in mapping] # keep only the ones in mapping
    out = out[use].rename(columns=mapping) # rename the columns
    # fill missing expected columns
    for col in set(NBIM_MAP.values()) | set(CUST_MAP.values()):
        if col not in out.columns:
            out[col] = pd.NA
    # parse dates to datetime
    for c in DATE_COLS:
        out[c] = pd.to_datetime(out[c], errors="coerce", utc=True, dayfirst=True) # errors invalid values become NaT
    # numeric coercion
    for c in NUM_COLS:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    # strings tidy
    for c in ["qc","sc","custodian","isin"]:
        out[c] = out[c].astype(str).str.strip().str.upper()
    # keep only the first currency as the other one is in sc
    if "qc" in out.columns:
        out["qc"] = out["qc"].str.split(" ").str[0]
        # turn empty strings into <NA>
        out["qc"] = out["qc"].where(out["qc"].str.len() > 0, pd.NA)
    
    return out
