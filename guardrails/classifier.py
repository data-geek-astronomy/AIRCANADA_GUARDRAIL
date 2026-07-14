"""
Commitment-language classifier.

Stand-in for a production text-classification model (e.g. a fine-tuned
DistilBERT head, or NVIDIA NeMo Guardrails / Llama Guard running as a
sidecar). Its only job: decide whether a generated response contains
language that commits the company to money, a refund, a waiver, or a
policy claim. If it does, the response MUST NOT reach the customer until
the deterministic verifier (verifier.py) confirms every claim against the
authorized policy database.

Kept rule-based here for zero-dependency portability; swap `contains_commitment`
for a real classifier's `.predict()` without changing callers.
"""

from __future__ import annotations
import re

COMMITMENT_PATTERNS = [
    r"\brefund(ed|s)?\b",
    r"\breimburse(d|ment)?\b",
    r"\bcompensat(e|ed|ion)\b",
    r"\bwaive[d]?\b",
    r"\bfree of charge\b",
    r"\bcredit(ed)?\b",
    r"\bvoucher\b",
    r"\bdiscount(ed)?\b",
    r"\bentitled\b",
    r"\bguarantee[d]?\b",
    r"\bfull (refund|amount)\b",
    r"\bwe('| wi)ll (give|cover|pay|refund)\b",
    r"\bno charge\b",
    r"\$\d+",
    r"\d+%",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in COMMITMENT_PATTERNS]


def contains_commitment(text: str) -> bool:
    """True if the text makes any financial or policy commitment."""
    return any(p.search(text) for p in _COMPILED)


def flagged_spans(text: str) -> list[str]:
    """Return the specific phrases that triggered the classifier, for the audit log."""
    hits = []
    for p in _COMPILED:
        m = p.search(text)
        if m:
            hits.append(m.group(0))
    return hits
