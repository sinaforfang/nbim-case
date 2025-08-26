import json
from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser

from .config import MODEL_NAME, TEMPERATURE, MAX_TOKENS
from .prompt_templates import build_classify_prompt

class ClassificationResult(BaseModel):
    reason_code: str
    explanation: str
    suggested_fix: str
    priority: int
    evidence_fields: List[str] = Field(default_factory=list)
    notes: str = ""

def classify_one_payload(llm: ChatOpenAI, payload: dict) -> ClassificationResult:
    parser = PydanticOutputParser(pydantic_object=ClassificationResult)
    prompt = build_classify_prompt(parser)
    # produce the actual system message + human message with all variables filled in
    messages = prompt.format_messages(payload_json=json.dumps(payload, default=str))
    response = llm.invoke(messages)
    return parser.parse(response.content)

def classify_payloads(payloads: List[dict]) -> List[ClassificationResult]:
    # one client for all payloads
    llm = ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE, max_tokens=MAX_TOKENS)
    results: List[ClassificationResult] = []
    for p in payloads:
        # include fields that appear different as evidence
        p = dict(p) 
        p["evidence_fields"] = p.get("different_fields", []) # which fields triggered this reasoning
        res = classify_one_payload(llm, p)
        results.append(res)
    return results # a list of pydantic objects
