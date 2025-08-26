import pandas as pd
from typing import Dict, Any, List

NUM_COLS = ["nominal","div_ps","gross_qc","net_qc","net_sc","tax_amt","tax_rate"]

def assert_or_aggregate_unique(df: pd.DataFrame, side: str) -> pd.DataFrame:
    """
    Ensure (event_key, account) is unique per side.
    If duplicates exist, aggregate by summing numeric columns and taking first non-null of the rest.
    """
    if df.duplicated(subset=["event_key","account"], keep=False).any():
        agg_num = {c: "sum" for c in NUM_COLS if c in df.columns}
        agg_rest = {c: "first" for c in df.columns if c not in agg_num and c not in ["event_key","account"]}
        grouped = df.groupby(["event_key","account"], dropna=False).agg({**agg_num, **agg_rest}).reset_index()
        return grouped
    return df

def _diff_val(a, b):
    # find the difference between two values
    if pd.isna(a) or pd.isna(b):
        return None
    try:
        return float(b - a)
    except Exception:
        return None

def _days_diff(a, b):
    # find the difference between dates
    if pd.isna(a) or pd.isna(b):
        return None
    try:
        a = pd.to_datetime(a)
        b = pd.to_datetime(b)
        return int((b - a).days)
    except Exception:
        return None

def pair_by_event_account(nb: pd.DataFrame, cu: pd.DataFrame) -> pd.DataFrame:
    # merge on event_key (COAC_EVENT_KEY) and account (custody: CUSTODY, nbim: BANK_ACCOUNT) to have unique combinations
    return nb.merge(
        cu,
        on=["event_key","account"],
        suffixes=("_nb","_cu"),
        how="inner" #TODO outer? is this before or after change of column names?
    )

def diffs_for_row(r: pd.Series) -> dict:
    # compute numeric differences between nbim and custody for each row
    diff = {
        "gross_qc_diff": _diff_val(r.get("gross_qc_nb"), r.get("gross_qc_cu")),
        "net_qc_diff":   _diff_val(r.get("net_qc_nb"),   r.get("net_qc_cu")),
        "net_sc_diff":   _diff_val(r.get("net_sc_nb"),   r.get("net_sc_cu")),
        "tax_amt_diff":  _diff_val(r.get("tax_amt_nb"),  r.get("tax_amt_cu")),
        "tax_rate_diff": _diff_val(r.get("tax_rate_nb"), r.get("tax_rate_cu")),
        "nominal_diff":  _diff_val(r.get("nominal_nb"),  r.get("nominal_cu")),
        "div_ps_diff":   _diff_val(r.get("div_ps_nb"),   r.get("div_ps_cu")),
        # compare string currency codes, 0=match, 1=differ
        "qc_mismatch": None if pd.isna(r.get("qc_nb")) or pd.isna(r.get("qc_cu"))
            else (0.0 if r.get("qc_nb") == r.get("qc_cu") else 1.0),
        "sc_mismatch": None if pd.isna(r.get("sc_nb")) or pd.isna(r.get("sc_cu"))
            else (0.0 if r.get("sc_nb") == r.get("sc_cu") else 1.0),
        # date differences in days (string-safe)
        "pay_date_days_diff": _days_diff(r.get("pay_date_nb"), r.get("pay_date_cu")),
        "ex_date_days_diff":  _days_diff(r.get("ex_date_nb"),  r.get("ex_date_cu")),
    }
    # numeric differences
    different_fields = [k.replace("_diff","") for k,v in diff.items() if k.endswith("_diff") and isinstance(v, float) and abs(v) > 1e-9]
    # flags for currencies
    for k in ["qc_mismatch","sc_mismatch"]:
        if diff.get(k) == 1.0:
            different_fields.append(k)
    # date diffs if non-zero days
    for k in ["pay_date_days_diff","ex_date_days_diff"]:
        if isinstance(diff.get(k), int) and diff[k] != 0:
            different_fields.append(k)
    return {"diffs": diff, "different_fields": different_fields}

def compact_payload(r: pd.Series) -> dict:
    # assembles a compact dictionary of key identifiers and values from both nbim and custody
    base = {
        "event_key": int(r["event_key"]) if pd.notna(r["event_key"]) else None,
        "account": r.get("account"),
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
    # simple cash impact proxy: max abs numeric diffs (exclude boolean/flags and date diffs)
    numeric_diffs = [v for k,v in base["diffs"].items() if k.endswith("_diff") and isinstance(v, float)]
    # calculate the biggest cash difference to see an estimate of potential impact
    base["cash_impact"] = max([abs(d) for d in numeric_diffs] or [0.0])
    return base # full payload dict

def pair_and_build_payloads(nb: pd.DataFrame, cu: pd.DataFrame, sample_size: int = 5):
    # TODO join dfs by event + account, compute diffs and within what field, pack everything to payloads for the LLM
    nb_u = assert_or_aggregate_unique(nb, "NBIM")
    cu_u = assert_or_aggregate_unique(cu, "Custody")
    pairs = pair_by_event_account(nb_u, cu_u)
    subset = pairs.head(sample_size).copy()   # already matched only
    payloads = [compact_payload(row) for _, row in subset.iterrows()]
    # sort by impact so agent can take top-K
    payloads.sort(key=lambda x: x.get("cash_impact") or 0.0, reverse=True)
    return payloads # dict with key/value pairs from both dfs, diffs, different_fields and cash_impact

