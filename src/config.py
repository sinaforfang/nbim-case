from dotenv import load_dotenv
import os

load_dotenv()  # expects .env with OPENAI_API_KEY

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
assert OPENAI_API_KEY, "OPENAI_API_KEY missing. Create a .env and set it."

MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0
MAX_TOKENS = 300
