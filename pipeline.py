"""
End-to-end orchestration: retrieval -> generation -> guardrail classification
-> deterministic verification -> final response.

    user query
        |
        v
    [RAG retrieval over support_kb]  (rag/retriever.py)
        |
        v
    [LLM draft response]             (generator.py: mock or real)
        |
        v
    [Commitment classifier]          (guardrails/classifier.py)
        |          \\
        | no          \\ yes
        v               v
   send as-is     [Deterministic verifier against authorized_policies.json]
                        |             \\
                        | authorized     \\ NOT authorized
                        v                  v
                   send as-is        block + replace with the verified
                                      authorized policy text, log incident
"""

from __future__ import annotations
from dataclasses import dataclass, field

from rag.retriever import build_kb_retriever, Document
from generator import generate
from guardrails.classifier import contains_commitment, flagged_spans
from guardrails.verifier import verify, VerificationResult

_kb_retriever = build_kb_retriever()


@dataclass
class PipelineResult:
    final_response: str
    draft_response: str
    guardrails_enabled: bool
    commitment_detected: bool
    flagged_terms: list[str]
    verification: VerificationResult | None
    blocked: bool
    retrieved_docs: list[tuple[Document, float]] = field(default_factory=list)


def run_pipeline(user_query: str, guardrails_enabled: bool, llm_mode: str = "mock") -> PipelineResult:
    retrieved = _kb_retriever.search(user_query, k=2)
    kb_docs = [doc for doc, _ in retrieved]

    draft = generate(user_query, kb_docs, mode=llm_mode)

    has_commitment = contains_commitment(draft)
    terms = flagged_spans(draft) if has_commitment else []

    if not guardrails_enabled:
        # This branch reproduces the unguarded failure mode: whatever the
        # LLM drafted goes straight to the customer, verbatim.
        return PipelineResult(
            final_response=draft,
            draft_response=draft,
            guardrails_enabled=False,
            commitment_detected=has_commitment,
            flagged_terms=terms,
            verification=None,
            blocked=False,
            retrieved_docs=retrieved,
        )

    if not has_commitment:
        return PipelineResult(
            final_response=draft,
            draft_response=draft,
            guardrails_enabled=True,
            commitment_detected=False,
            flagged_terms=[],
            verification=None,
            blocked=False,
            retrieved_docs=retrieved,
        )

    result = verify(user_query, draft)

    if result.authorized:
        return PipelineResult(
            final_response=draft,
            draft_response=draft,
            guardrails_enabled=True,
            commitment_detected=True,
            flagged_terms=terms,
            verification=result,
            blocked=False,
            retrieved_docs=retrieved,
        )

    # Blocked: replace with the verified authorized policy text (or a safe
    # fallback if no policy could even be matched) instead of sending the
    # unverified LLM draft.
    if result.matched_policy:
        safe_response = (
            f"Let me give you the accurate policy on this rather than guess. "
            f"{result.matched_policy['authorized_text']}\n\n"
            f"If your situation doesn't fit this exactly, I can connect you with a specialist."
        )
    else:
        safe_response = (
            "I want to make sure I give you accurate information rather than guess. "
            "Let me connect you with a specialist who can confirm the exact policy for your situation."
        )

    return PipelineResult(
        final_response=safe_response,
        draft_response=draft,
        guardrails_enabled=True,
        commitment_detected=True,
        flagged_terms=terms,
        verification=result,
        blocked=True,
        retrieved_docs=retrieved,
    )
