# src/agent_prompt.py
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def build_agent_prompt():
    system = (
        "You are a reconciliation agent. Goal: detect mismatches, classify the top items, and save a report.\n"
        "Use ONLY the registered tools. Follow this plan strictly:\n"
        "1) Call detect_tool with nbim_path, custody_path, and sample_size.\n"
        "2) From the returned payloads, select at most top_k by cash_impact (descending).\n"
        "3) Call classify_batch_tool ONCE with those selected payloads (JSON list).\n"
        "4) Call save_tool with the payloads and classification results. Then stop.\n\n"
        "Rules:\n"
        "- Never classify more than top_k items.\n"
        "- If detect_tool returns no payloads, do not call classify; end.\n"
        "- Use only the registered tools; do not invent tool names.\n"
        "- Keep cost low and steps minimal.\n"
    )
    human = (
        "Run end-to-end with these parameters (JSON):\n"
        "{input}\n"
        "Return a brief final summary after saving."
    )
    return ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", human),
        MessagesPlaceholder("agent_scratchpad"),
    ])

