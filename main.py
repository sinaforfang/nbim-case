# main.py
import json
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor

from src.config import MODEL_NAME, TEMPERATURE, DEFAULT_TOP_K, DEFAULT_SAMPLE_SIZE, OUT_DIR
from src.tools import detect_tool, classify_batch_tool, save_tool
from src.agent_prompt import build_agent_prompt

def main():
    # hard-coded defaults
    nbim_path = "data/NBIM_Dividend_Bookings.csv"
    custody_path = "data/CUSTODY_Dividend_Bookings.csv"
    sample_size = DEFAULT_SAMPLE_SIZE
    top_k = DEFAULT_TOP_K
    out_dir = OUT_DIR

    llm = ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE)
    tools = [detect_tool, classify_batch_tool, save_tool]
    prompt = build_agent_prompt()

    # create agent
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    run_params = {
        "nbim_path": nbim_path,
        "custody_path": custody_path,
        "sample_size": sample_size,
        "top_k": top_k,
        "out_dir": out_dir,
    }

    # only 'input' required
    result = executor.invoke({"input": json.dumps(run_params)})

    print("\n=== Agent finished ===")
    print(result.get("output", ""))

if __name__ == "__main__":
    main()


