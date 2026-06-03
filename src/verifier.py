import re
from dataclasses import dataclass
from typing import List, Dict, Tuple

CITATION_RE = re.compile(r"\[(\d+)\]")

CLAIM_HINT_RE = re.compile(
    r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|\bfailed\b|\battempt|\bsuccess|\bport\b|"
    r"\buser\b|\bblocked\b|\ballowed\b|\bstatus\b|\d{2,})",
    re.IGNORECASE,
)


@dataclass
class VerificationReport:
    total_citations_found: int
    valid_citations: List[int]
    invalid_citations: List[int]
    integrity_ok: bool
    integrity_mismatches: List[str]
    unsupported_claims: List[str]
    trust_score: float  


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def verify_answer(
    answer_text: str,
    retrieved: List[Tuple], 
) -> VerificationReport:
    index_to_chunk = {i + 1: chunk for i, (chunk, score) in enumerate(retrieved)}

    cited = [int(n) for n in CITATION_RE.findall(answer_text)]
    valid = sorted(set(n for n in cited if n in index_to_chunk))
    invalid = sorted(set(n for n in cited if n not in index_to_chunk))

    
    mismatches = []
    for n in valid:
        chunk = index_to_chunk[n]
        recomputed = chunk.chunk_hash
        if recomputed != _stored_hash(chunk):
            mismatches.append(chunk.chunk_id)

    unsupported = []
    for sentence in split_sentences(answer_text):
        has_citation = bool(CITATION_RE.search(sentence))
        looks_like_claim = bool(CLAIM_HINT_RE.search(sentence))
        if looks_like_claim and not has_citation:
            unsupported.append(sentence)

    total_sentences = max(len(split_sentences(answer_text)), 1)
    penalty = len(invalid) * 0.15 + len(mismatches) * 0.25 + len(unsupported) * (0.5 / total_sentences)
    trust_score = max(0.0, min(1.0, 1.0 - penalty))

    return VerificationReport(
        total_citations_found=len(cited),
        valid_citations=valid,
        invalid_citations=invalid,
        integrity_ok=(len(mismatches) == 0),
        integrity_mismatches=mismatches,
        unsupported_claims=unsupported,
        trust_score=round(trust_score, 2),
    )


def _stored_hash(chunk) -> str:
    return chunk.chunk_hash
