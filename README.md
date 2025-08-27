# LLM-Powered Dividend Reconciliation System

> Agent that reconciles NBIM vs Custody dividend bookings, **detects** mismatches, **explains** the root cause, and **suggests** a fix by producing structured outputs saved to .

---

## Overview of the case

Given the two csv exports **NBIM_Dividend_Bookings.csv** and **CUSTODY_Dividend_Bookings.csv** reconcile dividend **entitlements** per event and account:

- An **event** is identified by `COAC_EVENT_KEY`.
- There may be **multiple accounts** per event (each is a separate entitlement line). An account is identified in NBIM by `BANK_ACCOUNT` and in CUSTODY by `CUSTODY`
- For each matched (event, account) line, **detect** differences (amounts, dates, currencies, positions), **classify** the mismatch with a reason code, **explain** briefly using only provided fields, and **suggest** a practical fix.
- Output a compact csv summary that highlights the key findings plus detailed jsonl that contain all underlaying data leading to the given result.

This repo implements that brief as an **agent-based** system with deterministic detection and LLM classification.

---

## Data & Canonical Schema

Two inputs:
- `data/NBIM_Dividend_Bookings.csv`
- `data/CUSTODY_Dividend_Bookings.csv`

The loader canonicalizes both files to the same columns:
- Keys: `event_key`, `isin`, `account`, `custodian`
- Dates: `ex_date`, `pay_date` (parsed as UTC datetimes)
- Currencies: `qc` (quotation), `sc` (settlement)
- Numerics: `nominal`, `div_ps`, `gross_qc`, `net_qc`, `net_sc`, `tax_amt`, `tax_rate`

See `src/schema.py` (`NBIM_MAP`, `CUST_MAP`) for the exact mapping. Headers are standardized, dates and numbers parsed, strings uppercased, and in qc only the first currency token is kept when more than one is listed (for example, "KRW USD" becomes "KRW")

---

## Detection (Deterministic Tool)

The detector joins NBIM and Custody **on (`event_key`, `account`)** using an **inner join** (matched pairs only).  
Per matched row it computes numeric diffs and flags:

- Amounts: `gross_qc_diff`, `net_qc_diff`, `net_sc_diff`, `tax_amt_diff`, `tax_rate_diff`, `nominal_diff`, `div_ps_diff`
- Currencies: `qc_mismatch`, `sc_mismatch` (boolean)
- Dates: `pay_date_days_diff`, `ex_date_days_diff` (in days)

The payload for the LLM includes both sides’ values, the diffs, `different_fields` list, and a coarse **`cash_impact`** proxy = **max absolute numeric diff**. 

See `src/detector.py`.

---

## Classification (LLM Tool)

We call OpenAI `gpt-4o-mini` with a strict Pydantic schema:

```json
{
  "reason_code": "string",
  "explanation": "string",
  "suggested_fix": "string",
  "priority": 3,
  "evidence_fields": ["net_qc", "tax_amt", "fx_rate"]
}
```

Here `reason_code` is the assigned mismatch tag from the allowed taxonomy described below, `explanation` is a short natural-language description of why the mismatch occurred based only on the provided fields, `suggested_fix` is a practical next step to resolve or investigate the issue, `priority` is an indicator of how to prioritize the investigation of the mismatches (3 = high cash impact, 2 = moderate, 1 = low), and `evidence_fields` lists the specific columns that showed differences and were used as supporting evidence for the classification. An example is displayed above.

### Reason Codes (Mismatch Taxonomy)

Each reconciliation is classified into one of the following **reason codes**. These tags provide a consistent vocabulary for analysts and make it possible to group, filter, and prioritize breaks:

- **PAY_DATE_MISMATCH** – Payment dates differ between the two sources.  
- **EXDATE_MISMATCH** – Ex-dates differ between the two sources.  
- **GROSS_QC_MISMATCH** – Gross dividend amounts in quotation currency differ.  
- **NET_AMOUNT_MISMATCH** – Net dividend amounts (after tax) differ.  
- **TAX_RATE_MISMATCH** – Withholding tax rate differs (e.g., 25% vs 20%).  
- **TAX_AMOUNT_MISMATCH** – Withholding tax amounts differ even if rates match.  
- **CURRENCY_CODE_MISMATCH** – Quotation or settlement currency codes differ.  
- **DIVIDEND_RATE_MISMATCH** – Dividend per share (DPS) differs.  
- **NOMINAL_POSITION_MISMATCH** – Shareholding quantity or nominal basis differs.  
- **MATCH** – No material differences detected; the records reconcile.  

---

## Prompt Design

The LLM is guided by a carefully constructed prompt that enforces structured, neutral, and consistent outputs.  
The prompt contains two parts:

- **System message** – Sets the role of the assistant as a cautious dividend reconciliation agent.  
  - Instructs the model to classify mismatches, explain briefly, and suggest a fix.  
  - Enforces rules such as:  
    - Use only values present in the payload.  
    - Do not hallucinate numbers or dates.  
    - Keep explanations to max 2 sentences.  
    - Assign `priority` based on `cash_impact`.  
  - Defines the **allowed reason_code tags** (e.g., `GROSS_QC_MISMATCH`, `TAX_RATE_MISMATCH`, `NOMINAL_POSITION_MISMATCH`).  

- **User message** – Supplies the JSON payload for a specific dividend event and asks for strict JSON output.  
  Example structure:  
  ```json
  {
    "reason_code": "NET_AMOUNT_MISMATCH",
    "explanation": "The net amounts differ between NBIM and Custody.",
    "suggested_fix": "Verify the tax rate and update records.",
    "priority": 3,
    "evidence_fields": ["net_qc", "tax_amt", "tax_rate"]
  }

The Pydantic schema (`ClassificationResult`) ensures the model adheres to this format.

---

## Agent Orchestration

This project is implemented as an **agent-based system** using LangChain. Instead of a static pipeline, an LLM orchestrates the reconciliation by calling dedicated tools:

- **`detect_tool`** – runs deterministic detection of mismatches by joining NBIM and Custody data and computing diffs  
- **`classify_batch_tool`** – classifies the top mismatches in a single batch call to the LLM using a strict schema  
- **`save_tool`** – saves the results to both CSV and JSONL for analyst triage and audit

The agent follows a fixed plan:  
1. Detect mismatches  
2. Select the top-K items by cash impact  
3. Classify mismatches with the LLM  
4. Save results and stop

This design enforces cost guardrails (limits LLM calls) while still producing structured, explainable outputs.

---

## Outputs

Two outputs are generated for each run:

- **`outputs/recon_summary.csv`**  
  A compact summary for triage containing:  
  `event_key`, `account`, `isin_nb`, `isin_cu`, `columns_different`, `cash_impact`, `reason_code`, `priority`, `explanation`, `suggested_fix`  

- **`outputs/recon_details.jsonl`**  
  A detailed log where each line contains both the **payload** (raw values, diffs) and the **classification** (reason code, explanation, fix, priority, evidence fields).  
  This format is machine-friendly and suitable reloading into pandas or doing further analysis.


---

## Repo Structure

```
├── main.py                     # Agent entrypoint (detect → classify → save)
├── requirements.txt            # Dependencies
├── .env                        # API key (not committed)
├── data/                       # Input CSV files
│   ├── NBIM_Dividend_Bookings.csv
│   └── CUSTODY_Dividend_Bookings.csv
├── outputs/                    # Generated reports (csv + jsonl)
└── src/
    ├── config.py               # model, tokens, defaults
    ├── schema.py               # canonicalization maps & parsing
    ├── loader.py               # read semicolon CSVs + canonicalize
    ├── detector.py             # join & diffs → payloads
    ├── classifier.py           # Pydantic schema + LLM call
    ├── prompt_templates.py     # classification prompt
    ├── agent_prompt.py         # orchestration prompt
    └── tools.py                # detect_tool, classify_batch_tool, save_tool

```

---

## Analysis & Recommendations

### Innovative Use Cases

While the current implementation focuses on dividend reconciliation, the same framework can be applied more broadly across NBIM’s operational processes:

- **Other corporate actions** – Extend to stock splits, mergers, or rights issues using the same canonical schema + detection + classification pipeline.  
- **Real-time monitoring** – Adapt the agent to run continuously on streaming custody feeds, flagging breaks in near real time.  
- **Cross-system reconciliations** – Apply the same approach to reconcile between additional internal systems/records and other external data providers.  
- **Create an autonomous system** – Use AI agent to go through the output created and take actions needed to correct the mistake. To reduse risk it can come with a suggestion that a human need to verify.
- **Other repetetative tasks** - Create similar AI agents to solve other repetetative tasks which are now done manually.

---

### Risk Assessment

Several risks arise when introducing a LLM-powered reconciliation system:

- **LLM-specific risks**  
  - Hallucinating or imprecise explanations  
  - Misclassification of root cause (e.g., tagging as `NET_AMOUNT_MISMATCH` instead of `TAX_RATE_MISMATCH`)  
  - High or unpredictable API costs  

- **Data risks**  
  - Incorrect join keys creating false mismatches  
  - Missing relevant data to make correct conclusions
  - Missing fields or inconsistent custody formats  

- **Operational risks**  
  - Over-reliance on AI for explanations without human validation  
  - Analysts losing trust if results appear inconsistent
  - Lack of reproducibility if prompts or models change over time  

- **Compliance risks**  
  - Audit requirements demand explainability and traceability  
  - Sensitive financial data must be handled securely (data privacy/leakage prevention)

---

### Mitigation Strategies

To address these risks, the following measures are recommended:

- **LLM control**  
  - Constrain outputs with a strict Pydantic schema.  
  - Keep LLM focused on classification/explanation, not raw diff detection (done deterministically).  
  - Use cost guardrails: classify only top-K mismatches, small max token size.  

- **Data quality**  
  - Continue canonicalization and validation of all key columns.  
  - Add tolerance rules for small rounding differences.  

- **Operational resilience**  
  - Always produce both summary (csv) and detailed (json) outputs for audit.  
  - Ensure a human-in-the-loop for high-priority mismatches.  
  - Version control prompts and schema so results are reproducible over time.  

- **Compliance & security**  
  - Keep sensitive data anonymized or masked in test runs.  
  - Document decisions in the audit log (jsonl serves this purpose).  

---

## Assumptions & Limitations
- **Only mapped columns** - Only columns found in both csv files are included. This means that some errors can be missed, and that some explainations may be wrong or lack relevant information.
- **Inner join only** – The reconciliation only considers matched `(event_key, account)` pairs. 
- **Cash impact** – Calculated as the maximum absolute numeric difference across fields. This is a simplified proxy and not normalized across currencies etc.  
- **FX handling** – Only basic QC/SC currency mismatches are flagged. No normalization or FX rate comparison is performed as they from my understanding are based on different currencies.  
- **Scope restrictions** – Fields such as shares on loan, restitution, and local tax are not included in the current implementation as they only occur in one df and therefore not causing a direct mismatch.  
- **LLM explanations** – Constrained to short, neutral sentences, but may occasionally produce imprecise wording (e.g., describing a gross difference as net).  
- **Improved AI agent** - The existing AI agent is following a strict and quite simple step by step guide. By having more information about the logic behind solving the mismatches it is possible to create a more complex and autonomous AI agent.

---

## Future Enhancements

- **Outer join support** – Include deterministic classifications for `MISSING_ON_NBIM` and `MISSING_ON_CUSTODY`.  
- **Cash impact normalization** – Express cash impact consistently in settlement currency rather than using a raw max-diff proxy.  
- **Tolerance rules** – Add configurable tolerances for small rounding differences.  
- **Expanded taxonomy** – Incorporate additional scenarios such as shares on loan, restitution, and local tax adjustments.  
- **Prompt refinement** – Guide the LLM to prioritize root cause tags (e.g., classify as `TAX_RATE_MISMATCH` instead of `NET_AMOUNT_MISMATCH` when the tax rate difference is the driver).  
- **Incorporate additional tools** - Provide the agent with additional tools to analyse what is causing the mistake and how to correct it. 

---

## Quickstart / How to Run 

1. **Setup environment**
   ```bash
   python -m venv venv
   source venv/bin/activate        # macOS/Linux
   venv\Scripts\activate           # Windows
   pip install -r requirements.txt
    ```
2. **Set API key**
    Create an OpenAI API key and create a .env file in the repo root:
    ```
    OPENAI_API_KEY=sk-...
    ```
3. **Run the agent**
    ```
    python main.py
    ```
By default, main.py uses the files in `data/`:
`data/NBIM_Dividend_Bookings.csv`
`data/CUSTODY_Dividend_Bookings.csv`
and writes outputs to the `outputs/` folder.

Good luck!!