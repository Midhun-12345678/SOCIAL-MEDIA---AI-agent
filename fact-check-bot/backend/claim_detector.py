import json
import logging
from openai import OpenAI
from backend.config import OPENAI_API_KEY, GPT_MODEL
from backend.models import ClaimDetectionResult
from backend.zero_shot_classifier import ZeroShotClassifier

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

BART_WEIGHT = 0.4
GPT_WEIGHT = 0.6
BART_CONFIDENT_REJECT = 0.65

GPT_SYSTEM_PROMPT = """You are a fact-checking assistant specialized in social media posts.

A post has already been pre-screened as likely containing a factual claim.
Your job is to:
1. Confirm whether it truly contains a verifiable factual claim
2. If yes, extract the core claim in clean, concise, searchable language
3. Provide one-sentence reasoning

A factual claim = something objectively verifiable as true or false.
Examples:
  CLAIM:     "Vaccines cause autism" -> extract: "Vaccines cause autism"
  CLAIM:     "Einstein failed math in school lol" -> extract: "Einstein failed math in school"
  NOT CLAIM: "I think coffee is amazing" -> not a claim
  NOT CLAIM: "What time is it?" -> not a claim

Respond ONLY with valid JSON, no markdown:
{
  "is_claim": true or false,
  "extracted_claim": "clean claim text, or null",
  "reasoning": "one sentence explanation",
  "gpt_confidence": 0.0 to 1.0
}"""


def _call_gpt_extractor(post: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": GPT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this post:\n\n{post}"}
        ],
        temperature=0.1,
        max_tokens=150
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


def detect_claim(post: str) -> ClaimDetectionResult:
    classifier = ZeroShotClassifier.get_instance()

    if classifier.is_available:
        try:
            bart_is_claim, bart_label, bart_score, all_scores = classifier.is_factual_claim(post)

            logger.debug(f"BART: label={bart_label} score={bart_score:.3f} is_claim={bart_is_claim}")

            # Skip GPT if BART is HIGHLY confident (either TRUE or NOT TRUE) - saves ~1-2 seconds
            if bart_is_claim and bart_score >= 0.85:
                logger.debug(f"BART highly confident claim (score={bart_score:.3f}) — skipping GPT extraction")
                return ClaimDetectionResult(
                    is_claim=True,
                    extracted_claim=post,  # Use original text as claim
                    reasoning=f"BART high-confidence factual claim (score: {bart_score:.2f})",
                    bart_label=bart_label,
                    bart_score=round(bart_score, 4),
                    combined_confidence=round(bart_score, 4)
                )

            # Only reject without GPT if BART is highly confident it's NOT a claim
            if not bart_is_claim and bart_score >= BART_CONFIDENT_REJECT:
                return ClaimDetectionResult(
                    is_claim=False,
                    extracted_claim=None,
                    reasoning=f"BART confidently classified as '{bart_label}' (score: {bart_score:.2f})",
                    bart_label=bart_label,
                    bart_score=round(bart_score, 4),
                    combined_confidence=round(1.0 - bart_score, 4)
                )

            # For borderline cases or BART-positive but low confidence, consult GPT
            gpt_result = _call_gpt_extractor(post)
            gpt_confidence = float(gpt_result.get("gpt_confidence", 0.75))

            if bart_is_claim:
                combined = round(BART_WEIGHT * bart_score + GPT_WEIGHT * gpt_confidence, 4)
            else:
                # Borderline: GPT gets final say
                combined = round(gpt_confidence, 4)

            return ClaimDetectionResult(
                is_claim=gpt_result["is_claim"],
                extracted_claim=gpt_result.get("extracted_claim"),
                reasoning=gpt_result.get("reasoning"),
                bart_label=bart_label,
                bart_score=round(bart_score, 4),
                combined_confidence=combined
            )

        except Exception as e:
            logger.warning(f"BART stage failed ({e}), falling back to GPT-only")

    logger.info("Using GPT-only claim detection")
    gpt_result = _call_gpt_extractor(post)
    gpt_confidence = float(gpt_result.get("gpt_confidence", 0.75))

    return ClaimDetectionResult(
        is_claim=gpt_result["is_claim"],
        extracted_claim=gpt_result.get("extracted_claim"),
        reasoning=gpt_result.get("reasoning"),
        bart_label=None,
        bart_score=None,
        combined_confidence=round(gpt_confidence, 4)
    )
