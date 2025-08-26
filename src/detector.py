import pandas as pd

def _diff_val(a, b):
    # find the difference between to values
    if pd.isna(a) or pd.isna(b):
        return None
    try:
        return float(b - a)
    except Exception:
        return None

def pair_by_event_key(nb: pd.DataFrame, cu: pd.DataFrame) -> pd.DataFrame:
    # merge on event_key (COAC_EVENT_KEY) and account (custody: CUSTODY, nbim: BANK_ACCOUNT) to have unique combinations
    return nb.merge(cu, on=["event_key", "account"], suffixes=("_nb","_cu"), how="outer", indicator=True)

def diffs_for_row(r: pd.Series) -> dict:
    # compute numeric differences between nbim and custody
    diff = {
        "gross_qc_diff": _diff_val(r.get("gross_qc_nb"), r.get("gross_qc_cu")),
        "net_qc_diff":   _diff_val(r.get("net_qc_nb"),   r.get("net_qc_cu")),
        "net_sc_diff":   _diff_val(r.get("net_sc_nb"),   r.get("net_sc_cu")),
        "tax_amt_diff":  _diff_val(r.get("tax_amt_nb"),  r.get("tax_amt_cu")),
        "tax_rate_diff": _diff_val(r.get("tax_rate_nb"), r.get("tax_rate_cu")),
        "nominal_diff":  _diff_val(r.get("nominal_nb"),  r.get("nominal_cu")),
        "div_ps_diff":   _diff_val(r.get("div_ps_nb"),   r.get("div_ps_cu")),
    }
    # save which fields that have differnt values in the dfs
    different_fields = [k.replace("_diff","") for k,v in diff.items() if isinstance(v, float) and abs(v) > 1e-9]
    return {"diffs": diff, "different_fields": different_fields}

def compact_payload(r: pd.Series) -> dict:
    # assembles a compact dictionary of key identifiers and values from both nbim and custody
    base = {
        "event_key": int(r["event_key"]) if pd.notna(r["event_key"]) else None,
        "isin_nb": r.get("isin_nb"), "isin_cu": r.get("isin_cu"),
        "ex_date_nb": str(r.get("ex_date_nb")), "ex_date_cu": str(r.get("ex_date_cu")),
        "pay_date_nb": str(r.get("pay_date_nb")), "pay_date_cu": str(r.get("pay_date_cu")),
        "qc_nb": r.get("qc_nb"), "qc_cu": r.get("qc_cu"),
        "sc_nb": r.get("sc_nb"), "sc_cu": r.get("sc_cu"),
        "nominal_nb": r.get("nominal_nb"), "nominal_cu": r.get("nominal_cu"),
        "div_ps_nb": r.get("div_ps_nb"), "div_ps_cu": r.get("div_ps_cu"),
        "gross_qc_nb": r.get("gross_qc_nb"), "gross_qc_cu": r.get("gross_qc_cu"),
        "net_qc_nb": r.get("net_qc_nb"), "net_qc_cu": r.get("net_qc_cu"),
        "net_sc_nb": r.get("net_sc_nb"), "net_sc_cu": r.get("net_sc_cu"),
        "tax_amt_nb": r.get("tax_amt_nb"), "tax_amt_cu": r.get("tax_amt_cu"),
        "tax_rate_nb": r.get("tax_rate_nb"), "tax_rate_cu": r.get("tax_rate_cu"),
    }
    # add diffs and fields
    base.update(diffs_for_row(r))
    # simple cash_impact proxy (max abs numeric diff)
    diffs = base["diffs"]
    # calculate the biggest cash difference to see an estimate of potential impact
    base["cash_impact"] = max(abs(d) for d in [v for v in diffs.values() if isinstance(v, float)] or [0.0])
    return base # full payload dict

def pair_and_build_payloads(nb: pd.DataFrame, cu: pd.DataFrame, sample_size: int = 5):
    # join dfs by event + account, compute diffs and within what field, pack everything to payloads for the LLM
    pairs = pair_by_event_key(nb, cu)
    both = pairs[pairs["_merge"] == "both"].head(sample_size).copy() # keep only mateched lines
    payloads = [compact_payload(row) for _, row in both.iterrows()]
    return payloads # dict with key/value pairs from both dfs, diffs, different_fields and cash_impact
