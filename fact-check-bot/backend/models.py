from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class Verdict(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNVERIFIABLE = "UNVERIFIABLE"
    NOT_A_CLAIM = "NOT_A_CLAIM"


class CheckRequest(BaseModel):
    post: str


class Source(BaseModel):
    title: str
    url: str
    snippet: str


class ClaimDetectionResult(BaseModel):
    is_claim: bool
    extracted_claim: Optional[str] = None
    reasoning: Optional[str] = None
    bart_label: Optional[str] = None
    bart_score: Optional[float] = None
    combined_confidence: Optional[float] = None


class CheckResponse(BaseModel):
    original_post: str
    is_claim: bool
    extracted_claim: Optional[str] = None
    verdict: Verdict
    response: str
    sources: List[Source] = []
    confidence: float = 0.0
    latency_ms: Optional[int] = None
    bart_label: Optional[str] = None
    bart_score: Optional[float] = None
    detection_method: Optional[str] = None
