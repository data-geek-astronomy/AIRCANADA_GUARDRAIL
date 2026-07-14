"""
Response generation layer.

Two modes:
  - MOCK (default, no API key needed): a small rule-based generator that
    deliberately mirrors realistic LLM failure modes -- it drafts fluent,
    empathetic, *overconfident* answers by paraphrasing the loosely-worded
    support KB, exactly the way a naive RAG chatbot would. This lets the
    demo run anywhere with zero setup and reliably shows both the failure
    (guardrails off) and the fix (guardrails on).
  - REAL: if ANTHROPIC_API_KEY is set, calls Claude to draft the response
    using the same retrieved KB context. Even a strong model, given loose
    source material and no verification step, will sometimes produce
    unauthorized commitments -- which is exactly why the verifier step
    exists downstream regardless of which generator is used.
"""

from __future__ import annotations
import os
from rag.retriever import Document
from guardrails.topics import detect_topic

MOCK_TEMPLATES = {
    "bereavement_fare": (
        "I'm so sorry for your loss. Since your flight has already happened, I can go "
        "ahead and process a refund for you -- many customers in a similar situation have "
        "received their money back after reaching out, so you're entitled to a full refund "
        "of your fare."
    ),
    "flight_cancellation_by_airline": (
        "I see AirNova cancelled your flight -- I'm sorry for the disruption. You're entitled "
        "to a full refund to your original payment method, or I can rebook you for free on the "
        "next available flight, whichever you prefer."
    ),
    "voluntary_cancellation": (
        "No problem at all, I can cancel that booking for you right now and issue a full "
        "refund back to your card, no fees."
    ),
    "baggage_delay": (
        "I'm sorry your bag hasn't arrived yet. We'll reimburse reasonable essential purchases "
        "up to $100 a day for up to 3 days -- just hang on to your receipts and send them our way."
    ),
    "baggage_lost": (
        "Since it's been over 21 days, I can approve compensation up to $1,700 per our standard "
        "liability policy once you submit a claim form with proof of contents."
    ),
    "flight_delay_compensation": (
        "Since your flight was delayed over 3 hours, I'll go ahead and issue you a $300 travel "
        "voucher for the inconvenience, plus meal vouchers while you wait."
    ),
    "overbooking": (
        "Since you were denied boarding, you're entitled to compensation between $400 and $1,350 "
        "depending on the delay length, and we'll rebook you on the next available flight."
    ),
    "medical_emergency_cancellation": (
        "Given the medical emergency, I completely understand -- I can refund your ticket in "
        "full right away, no fees, no questions asked."
    ),
    "pet_travel_fee": (
        "Of course! I can waive the pet fee for you this time and let your dog fly free of charge."
    ),
    "unaccompanied_minor": (
        "Since it's a short flight, I can waive the unaccompanied minor fee for your child this time."
    ),
}

FALLBACK_RESPONSE = (
    "Thanks for reaching out -- I want to make sure I give you accurate information. "
    "Could you tell me a bit more about your situation (booking reference, what happened, "
    "and when) so I can look into the right policy for you?"
)


def mock_generate(user_query: str, kb_context: list[Document]) -> str:
    topic = detect_topic(user_query)
    if topic and topic in MOCK_TEMPLATES:
        return MOCK_TEMPLATES[topic]
    return FALLBACK_RESPONSE


def real_generate(user_query: str, kb_context: list[Document]) -> str:
    """Calls Claude with the retrieved (unverified) KB context. Requires ANTHROPIC_API_KEY."""
    import anthropic

    client = anthropic.Anthropic()
    context_block = "\n\n".join(f"[{d.id}] {d.title}: {d.text}" for d in kb_context)
    system_prompt = (
        "You are AirNova's customer support assistant. Answer the customer's question using "
        "the support articles below as your only source of information. Be warm, concise, and "
        "helpful.\n\nSupport articles:\n" + context_block
    )
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": user_query}],
    )
    return resp.content[0].text


def generate(user_query: str, kb_context: list[Document], mode: str = "mock") -> str:
    if mode == "real" and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return real_generate(user_query, kb_context)
        except Exception as e:  # pragma: no cover - network/key failures fall back to mock
            return mock_generate(user_query, kb_context) + f"\n\n[real-LLM call failed, showed mock output: {e}]"
    return mock_generate(user_query, kb_context)
