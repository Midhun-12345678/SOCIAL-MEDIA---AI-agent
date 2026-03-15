import json
import logging
from openai import OpenAI
from backend.config import OPENAI_API_KEY, GPT_MODEL
from backend.models import Source, Verdict
from typing import List, Tuple

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are an AI fact-checking bot for social media.

You will receive:
1. The original social media post
2. The extracted factual claim
3. Evidence retrieved from web searches

Your job is to:
- Assess if the claim is TRUE, FALSE, or UNVERIFIABLE based on the evidence
- Write a clear, concise, natural response (2-4 sentences max)
- Assign a confidence score from 0.0 to 1.0

RULES:
- Be direct and factual, not preachy
- If evidence is conflicting, say so honestly
- If evidence is insufficient, return UNVERIFIABLE
- Always ground your verdict in the provided evidence only

Respond ONLY with valid JSON, no markdown:
{
  "verdict": "TRUE" or "FALSE" or "UNVERIFIABLE",
  "response": "your natural language reply here",
  "confidence": 0.0 to 1.0,
  "used_source_indices": [0, 1, 2]
}"""


def build_evidence_block(sources: List[Source]) -> str:
    if not sources:
        return "No evidence retrieved."

    lines = []
    for i, src in enumerate(sources):
        lines.append(f"[{i}] {src.title}\nURL: {src.url}\nSnippet: {src.snippet}\n")

    return "\n".join(lines)


def generate_response(
    post: str,
    claim: str,
    sources: List[Source]
) -> Tuple[Verdict, str, float, List[Source]]:

    evidence_block = build_evidence_block(sources)

    user_message = f"""Original Post:
\"{post}\"

Extracted Claim:
\"{claim}\"

Retrieved Evidence:
{evidence_block}

Now generate your fact-check response."""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.2,
        max_tokens=250
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    parsed = json.loads(raw)

    verdict = Verdict(parsed["verdict"])
    reply = parsed["response"]
    confidence = float(parsed.get("confidence", 0.5))

    used_indices = parsed.get("used_source_indices", list(range(min(3, len(sources)))))
    used_sources = [sources[i] for i in used_indices if i < len(sources)]

    return verdict, reply, confidence, used_sources
