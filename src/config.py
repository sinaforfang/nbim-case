from dotenv import load_dotenv
import os

load_dotenv()  # expects .env with OPENAI_API_KEY

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
assert OPENAI_API_KEY, "OPENAI_API_KEY missing. Create a .env and set it."

# LLM defaults
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0
MAX_TOKENS = 300

# agent guardrails
DEFAULT_TOP_K = 10           # classify at most this many events/lines
DEFAULT_SAMPLE_SIZE = 999999 # how many joined rows to consider from detect step
OUT_DIR = "outputs"
