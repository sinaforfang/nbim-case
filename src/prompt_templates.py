from langchain_core.prompts import ChatPromptTemplate

def build_classify_prompt(parser):
    # overall system message 
    system = (
        "You are a cautious dividend reconciliation assistant for an institutional investor.\n"
        "Tasks:\n"
        "1) Classify the core reason for the mismatch using allowed tags.\n"
        "2) Explain briefly with provided fields only.\n"
        "3) Suggest one practical next step to fix the mismatch.\n"
        "4) Priority 1-3 based on cash_impact (3 if high), else 2 if moderate, else 1.\n\n"
        "Rules:\n"
        "- Do NOT invent numbers/dates. Use only values in payload.\n"
        "- If nothing material differs give reason_code='MATCH'.\n"
        "- Keep outputs neutral and max 2 sentences per explanation/fix.\n\n"
        "Allowed reason_code tags:\n"
        "PAY_DATE_MISMATCH, EXDATE_MISMATCH,\n"
        "GROSS_QC_MISMATCH, NET_AMOUNT_MISMATCH,\n"
        "TAX_RATE_MISMATCH, TAX_AMOUNT_MISMATCH, CURRENCY_CODE_MISMATCH,\n"
        "DIVIDEND_RATE_MISMATCH, NOMINAL_POSITION_MISMATCH,\n"
        "MATCH\n"
        "{format_instructions}"
    )

    # prompts with inforamtion about a spescific case
    user = (
        "Classify the mismatch, explain briefly, and suggest a fix.\n"
        "Return STRICT JSON for a single payload.\n\n"
        "PAYLOAD:\n{payload_json}"
    )

    # combine system + human into a template with placeholders
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", user)])
    # fills in the format_instructions based on  the class ClassificationResult
    prompt = prompt.partial(format_instructions=parser.get_format_instructions())
    return prompt
