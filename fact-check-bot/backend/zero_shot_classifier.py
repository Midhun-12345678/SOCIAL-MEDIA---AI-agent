import os
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("BART_MODEL", "cross-encoder/nli-MiniLM2-L6-H768")
CLAIM_THRESHOLD = float(os.getenv("BART_THRESHOLD", "0.40"))
CLAIM_LABEL = "factual claim"

CANDIDATE_LABELS = [
    "factual claim",
    "personal opinion",
    "question",
    "joke or sarcasm",
    "emotional expression",
]


class ZeroShotClassifier:
    _instance = None
    _pipeline = None

    @classmethod
    def get_instance(cls) -> "ZeroShotClassifier":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if ZeroShotClassifier._pipeline is not None:
            return
        self._load()

    def _load(self):
        try:
            from transformers import pipeline as hf_pipeline
            import torch

            device = 0 if torch.cuda.is_available() else -1
            label = "GPU" if device == 0 else "CPU"
            logger.info(f"Loading {MODEL_NAME} on {label}...")

            ZeroShotClassifier._pipeline = hf_pipeline(
                task="zero-shot-classification",
                model=MODEL_NAME,
                device=device,
                batch_size=1
            )
            logger.info(f"Model loaded on {label}")

        except Exception as e:
            logger.warning(f"Classifier not available ({e}) — GPT-only fallback active")
            ZeroShotClassifier._pipeline = None

    @property
    def is_available(self) -> bool:
        return ZeroShotClassifier._pipeline is not None

    def classify(self, text: str) -> Tuple[str, float, dict]:
        if not self.is_available:
            raise RuntimeError("Classifier not loaded")

        result = ZeroShotClassifier._pipeline(
            text,
            candidate_labels=CANDIDATE_LABELS,
            multi_label=False
        )
        top_label = result["labels"][0]
        top_score = result["scores"][0]
        all_scores = dict(zip(result["labels"], result["scores"]))
        return top_label, top_score, all_scores

    def is_factual_claim(self, text: str) -> Tuple[bool, str, float, dict]:
        top_label, top_score, all_scores = self.classify(text)

        if top_label == CLAIM_LABEL and top_score >= CLAIM_THRESHOLD:
            return True, top_label, top_score, all_scores

        claim_score = all_scores.get(CLAIM_LABEL, 0.0)
        if claim_score >= CLAIM_THRESHOLD + 0.10:
            return True, CLAIM_LABEL, claim_score, all_scores

        return False, top_label, top_score, all_scores
