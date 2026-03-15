import json
import math
import re
from collections import Counter
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class ClaimDetectionSample:
    post: str
    is_claim_ground_truth: bool
    predicted_is_claim: bool
    extracted_claim: Optional[str] = None


@dataclass
class RetrievalSample:
    query: str
    retrieved_urls: List[str]
    relevant_urls: List[str]


@dataclass
class GenerationSample:
    claim: str
    generated_response: str
    reference_response: Optional[str] = None
    verdict: Optional[str] = None
    ground_truth_verdict: Optional[str] = None
    sources_cited: List[str] = field(default_factory=list)


def compute_claim_detection_metrics(samples: List[ClaimDetectionSample]) -> Dict:
    tp = sum(1 for s in samples if s.predicted_is_claim and s.is_claim_ground_truth)
    fp = sum(1 for s in samples if s.predicted_is_claim and not s.is_claim_ground_truth)
    fn = sum(1 for s in samples if not s.predicted_is_claim and s.is_claim_ground_truth)
    tn = sum(1 for s in samples if not s.predicted_is_claim and not s.is_claim_ground_truth)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy  = (tp + tn) / len(samples) if samples else 0.0

    return {
        "true_positives":  tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives":  tn,
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1_score":  round(f1, 4),
        "accuracy":  round(accuracy, 4),
        "total_samples": len(samples)
    }


def reciprocal_rank(retrieved: List[str], relevant: List[str]) -> float:
    relevant_set = set(relevant)
    for rank, url in enumerate(retrieved, start=1):
        if url in relevant_set:
            return 1.0 / rank
    return 0.0


def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(top_k & relevant_set) / len(relevant_set)


def compute_retrieval_metrics(samples: List[RetrievalSample], k_values: List[int] = [1, 3, 5]) -> Dict:
    rr_scores = [reciprocal_rank(s.retrieved_urls, s.relevant_urls) for s in samples]
    mrr = sum(rr_scores) / len(rr_scores) if rr_scores else 0.0

    recall_at_k_scores = {}
    for k in k_values:
        scores = [recall_at_k(s.retrieved_urls, s.relevant_urls, k) for s in samples]
        recall_at_k_scores[f"recall@{k}"] = round(sum(scores) / len(scores), 4) if scores else 0.0

    return {
        "mrr": round(mrr, 4),
        **recall_at_k_scores,
        "total_queries": len(samples)
    }


def tokenize(text: str) -> List[str]:
    return re.findall(r'\b\w+\b', text.lower())


def ngrams(tokens: List[str], n: int) -> Counter:
    return Counter(tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1))


def bleu_score(hypothesis: str, reference: str, max_n: int = 4) -> float:
    hyp_tokens = tokenize(hypothesis)
    ref_tokens = tokenize(reference)

    if not hyp_tokens:
        return 0.0

    bp = 1.0 if len(hyp_tokens) >= len(ref_tokens) else math.exp(1 - len(ref_tokens) / len(hyp_tokens))

    precisions = []
    for n in range(1, max_n + 1):
        hyp_ngrams = ngrams(hyp_tokens, n)
        ref_ngrams = ngrams(ref_tokens, n)

        if not hyp_ngrams:
            precisions.append(0.0)
            continue

        clipped = sum(min(count, ref_ngrams[gram]) for gram, count in hyp_ngrams.items())
        total   = sum(hyp_ngrams.values())
        precisions.append(clipped / total if total > 0 else 0.0)

    if any(p == 0 for p in precisions):
        return 0.0

    log_avg = sum(math.log(p) for p in precisions) / len(precisions)
    return round(bp * math.exp(log_avg), 4)


def rouge_n(hypothesis: str, reference: str, n: int) -> Dict:
    hyp_ngrams = ngrams(tokenize(hypothesis), n)
    ref_ngrams = ngrams(tokenize(reference), n)

    overlap = sum(min(hyp_ngrams[g], ref_ngrams[g]) for g in hyp_ngrams)
    ref_total = sum(ref_ngrams.values())
    hyp_total = sum(hyp_ngrams.values())

    precision = overlap / hyp_total if hyp_total > 0 else 0.0
    recall    = overlap / ref_total if ref_total > 0 else 0.0
    f1        = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def rouge_l(hypothesis: str, reference: str) -> Dict:
    hyp = tokenize(hypothesis)
    ref = tokenize(reference)

    m, n = len(hyp), len(ref)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i-1][j-1] + 1 if hyp[i-1] == ref[j-1] else max(dp[i-1][j], dp[i][j-1])

    lcs_len = dp[m][n]
    precision = lcs_len / m if m > 0 else 0.0
    recall    = lcs_len / n if n > 0 else 0.0
    f1        = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def fever_score(predicted_verdict: str, ground_truth_verdict: str) -> float:
    fever_map = {
        "TRUE": "SUPPORTS",
        "FALSE": "REFUTES",
        "UNVERIFIABLE": "NOT ENOUGH INFO",
        "NOT_A_CLAIM": "NOT ENOUGH INFO"
    }
    pred_fever = fever_map.get(predicted_verdict.upper(), predicted_verdict)
    gt_fever   = fever_map.get(ground_truth_verdict.upper(), ground_truth_verdict)
    return 1.0 if pred_fever == gt_fever else 0.0


def compute_generation_metrics(samples: List[GenerationSample]) -> Dict:
    bleu_scores, rouge1_f1, rouge2_f1, rougel_f1, fever_scores = [], [], [], [], []

    for s in samples:
        if s.verdict and s.ground_truth_verdict:
            fever_scores.append(fever_score(s.verdict, s.ground_truth_verdict))

        if not s.reference_response:
            continue

        bleu_scores.append(bleu_score(s.generated_response, s.reference_response))
        r1 = rouge_n(s.generated_response, s.reference_response, 1)
        r2 = rouge_n(s.generated_response, s.reference_response, 2)
        rl = rouge_l(s.generated_response, s.reference_response)

        rouge1_f1.append(r1["f1"])
        rouge2_f1.append(r2["f1"])
        rougel_f1.append(rl["f1"])

    def avg(lst): return round(sum(lst) / len(lst), 4) if lst else None

    return {
        "bleu":        avg(bleu_scores),
        "rouge_1_f1":  avg(rouge1_f1),
        "rouge_2_f1":  avg(rouge2_f1),
        "rouge_l_f1":  avg(rougel_f1),
        "fever_score": avg(fever_scores),
        "verdict_accuracy": avg(fever_scores),
        "samples_with_reference": len(bleu_scores),
        "samples_with_verdict": len(fever_scores),
        "total_samples": len(samples)
    }


def compute_latency_metrics(latencies_ms: List[int]) -> Dict:
    if not latencies_ms:
        return {}

    sorted_l = sorted(latencies_ms)
    n = len(sorted_l)

    def percentile(p):
        idx = max(0, int(math.ceil(p / 100 * n)) - 1)
        return sorted_l[idx]

    return {
        "count":    n,
        "mean_ms":  round(sum(sorted_l) / n, 1),
        "min_ms":   sorted_l[0],
        "max_ms":   sorted_l[-1],
        "p50_ms":   percentile(50),
        "p95_ms":   percentile(95),
        "p99_ms":   percentile(99),
        "under_5s_pct": round(100 * sum(1 for l in sorted_l if l < 5000) / n, 1)
    }


def compute_robustness_metrics(results: List[Dict]) -> Dict:
    by_category = {}
    by_noise = {}

    for r in results:
        cat   = r.get("category", "unknown")
        noise = r.get("noise_level", "medium")
        correct = r.get("correct", False)

        by_category.setdefault(cat, []).append(correct)
        by_noise.setdefault(noise, []).append(correct)

    def acc(lst): return round(sum(lst) / len(lst), 4) if lst else 0.0

    return {
        "by_category": {k: {"accuracy": acc(v), "count": len(v)} for k, v in by_category.items()},
        "by_noise_level": {k: {"accuracy": acc(v), "count": len(v)} for k, v in by_noise.items()},
        "overall_accuracy": acc([r.get("correct", False) for r in results])
    }
