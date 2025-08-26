import json
import argparse
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor

from .config import MODEL_NAME, TEMPERATURE, DEFAULT_TOP_K, DEFAULT_SAMPLE_SIZE, OUT_DIR
from .tools import detect_tool, classify_batch_tool, save_tool
from .agent_prompt import build_agent_prompt

def parse_args():
    ap = argparse.ArgumentParser(description="NBIM Reconciliation Agent")
    ap.add_argument("--nbim", required=True, help="Path to NBIM_Dividend_Bookings.csv")
    ap.add_argument("--cust", required=True, help="Path to CUSTODY_Dividend_Bookings.csv")
    ap.add_argument("--sample_size", type=int, default=DEFAULT_SAMPLE_SIZE, help="Rows to consider from detect step")
    ap.add_argument("--top_k", type=int, default=DEFAULT_TOP_K, help="Max items to classify")
    ap.add_argument("--out_dir", default=OUT_DIR, help="Output directory")
    return ap.parse_args()

def main():
    args = parse_args()

    llm = ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE)
    tools = [detect_tool, classify_batch_tool, save_tool]
    prompt = build_agent_prompt()

    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # The agent reads all parameters from the human message
    human_vars = {
        "nbim_path": args.nbim,
        "custody_path": args.cust,
        "sample_size": args.sample_size,
        "top_k": args.top_k,
        "out_dir": args.out_dir,
    }

    # Build the top-level plan: detect -> classify (batch) -> save
    # The prompt instructs the agent exactly what to do.
    final = executor.invoke(human_vars)
    print("\n=== Agent finished ===")
    print(final.get("output", ""))

if __name__ == "__main__":
    main()
