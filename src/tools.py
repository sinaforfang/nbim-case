import os, json
import pandas as pd
from typing import List, Dict, Any
from langchain_core.tools import tool

from .config import OUT_DIR, DEFAULT_SAMPLE_SIZE, DEFAULT_TOP_K
from .loader import load_csvs
from .detector import pair_and_build_payloads
from .classifier import classify_payloads

def _ensure_out_dir(path: str):
    os.makedirs(path, exist_ok=True)

@tool
def detect_tool(params_json: str) -> str:
    """
    Run deterministic pairing+diffs and return a JSON list of payloads (sorted by cash_impact desc).
    params_json: {"nbim_path": str, "custody_path": str, "sample_size": int}
    """
    params = json.loads(params_json)
    nbim_path = params.get("nbim_path")
    custody_path = params.get("custody_path")
    sample_size = int(params.get("sample_size", DEFAULT_SAMPLE_SIZE))

    nb, cu = load_csvs(nbim_path, custody_path)

    payloads = pair_and_build_payloads(nb, cu, sample_size=sample_size)
    # sort already done in detector; ensure here too
    payloads.sort(key=lambda x: x.get("cash_impact") or 0.0, reverse=True)
    return json.dumps(payloads, default=str)

@tool
def classify_batch_tool(payloads_json: str) -> str:
    """
    Classify a list of payloads and return a JSON list of ClassificationResult dicts (aligned order).
    payloads_json: JSON list[dict]
    """
    payloads = json.loads(payloads_json)
    results = classify_payloads(payloads)
    return json.dumps([r.model_dump() for r in results], default=str)

@tool
def save_tool(report_json: str) -> str:
    """
    Persist summary CSV and details JSONL.
    report_json: {"payloads": list, "results": list, "out_dir": str}
    Writes:
      - out_dir/recon_summary.csv
      - out_dir/recon_details.jsonl
    Returns a short status string.
    """
    data = json.loads(report_json)
    payloads: List[Dict[str, Any]] = data.get("payloads", [])
    results:  List[Dict[str, Any]] = data.get("results", [])
    out_dir = data.get("out_dir", OUT_DIR)

    _ensure_out_dir(out_dir)

    # Build compact summary
    rows = []
    for p, r in zip(payloads, results):
        rows.append({
            "event_key": p.get("event_key"),
            "account": p.get("account"),
            "isin_nb": p.get("isin_nb"),
            "isin_cu": p.get("isin_cu"),
            "columns_different": p.get("different_fields"),
            "cash_impact": p.get("cash_impact"),
            "reason_code": r.get("reason_code"),
            "priority": r.get("priority"),
            "explanation": r.get("explanation"),
            "suggested_fix": r.get("suggested_fix"),
        })
    summary = pd.DataFrame(rows).sort_values(["priority","cash_impact"], ascending=[False, False])

    summary_csv = os.path.join(out_dir, "recon_summary.csv")
    details_jsonl = os.path.join(out_dir, "recon_details.jsonl")

    summary.to_csv(summary_csv, index=False)
    with open(details_jsonl, "w", encoding="utf-8") as f:
        for p, r in zip(payloads, results):
            f.write(json.dumps({"payload": p, "classification": r}, default=str) + "\n")

    return f"Saved: {summary_csv}, {details_jsonl}"
