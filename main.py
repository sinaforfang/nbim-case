import os
import json
import pandas as pd
from pprint import pprint

from src.loader import load_csvs
from src.detector import pair_and_build_payloads
from src.classifier import classify_payloads

# Paths to your CSVs
NBIM_PATH = "data/NBIM_Dividend_Bookings.csv"
CUST_PATH = "data/CUSTODY_Dividend_Bookings.csv"

# Output folder
OUT_DIR = "outputs"
os.makedirs(OUT_DIR, exist_ok=True)

def main():
    # 1) Load and normalize
    nb, cu = load_csvs(NBIM_PATH, CUST_PATH)

    # 2) Build deterministic diffs (sample_size large -> take all)
    payloads = pair_and_build_payloads(nb, cu, sample_size=999999)
    if not payloads:
        print("No matched rows on event_key. Consider adding a fallback join on (ISIN, pay_date).")
        return

    # 3) LLM classify + explain + suggest fix
    results = classify_payloads(payloads)

    # 4) Build compact summary table
    rows = []
    for payload, res in zip(payloads, results):
        rows.append({
            "event_key": payload.get("event_key"),
            "account": payload.get("account"),
            "columns_different": payload.get("different_fields"),
            "cash_impact": payload.get("cash_impact"),
            "reason_code": res.reason_code,
            "priority": res.priority,
            "explanation": res.explanation,
            "suggested_fix": res.suggested_fix
        })
    summary = pd.DataFrame(rows).sort_values(["priority","cash_impact"], ascending=[False, False])

    # 5) Save outputs: CSV (summary) + JSONL (detailed)
    summary_csv = os.path.join(OUT_DIR, "recon_summary.csv")
    details_jsonl = os.path.join(OUT_DIR, "recon_details.jsonl")

    # CSV summary
    summary.to_csv(summary_csv, index=False)

    # JSONL details: include full payload (diffs, fields) + classification
    with open(details_jsonl, "w", encoding="utf-8") as f:
        for payload, res in zip(payloads, results):
            record = {
                "payload": payload,                    # deterministic event/row payload + diffs
                "classification": res.model_dump()     # reason_code, explanation, priority, etc.
            }
            f.write(json.dumps(record, default=str) + "\n")

    # 6) Console printout
    print("\n=== Reconciliation Summary ===")
    print(summary.to_string(index=False))
    print(f"\nSaved:\n- {summary_csv}\n- {details_jsonl}")

if __name__ == "__main__":
    main()
