"""
Deterministic verification step.

This is the piece the real Air Canada chatbot lacked: before any
commitment-bearing response reaches the customer, it is cross-referenced
against a hardcoded, immutable table of authorized corporate procedures.
The LLM (or, in this demo, the mock generator) is never trusted as the
source of truth for policy facts -- it only drafts language, which this
module then either approves, or blocks and replaces with the verified
authorized text.

This is intentionally simple, rule-based, and fully auditable -- exactly
the property you want for a compliance-critical gate. A real deployment
would harden the numeric/claim extraction, but the architecture (LLM draft
-> classifier -> deterministic verification against an immutable source of
truth -> approve/block) is the same.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field

from guardrails.topics import detect_topic
from rag.retriever import load_policy_records

RETROACTIVE_PHRASES = [
    "after the flight", "after your flight", "after you travel", "after you've flown",
    "already flown", "after your trip", "retroactive", "once you've traveled",
    "after you traveled", "after the trip",
]


@dataclass
class VerificationResult:
    authorized: bool
    reason: str
    topic: str | None = None
    matched_policy: dict | None = None
    citations: list[str] = field(default_factory=list)


def _extract_dollar_amounts(text: str) -> list[int]:
    return [int(m.replace(",", "")) for m in re.findall(r"\$([\d,]+)", text)]


def _extract_percentages(text: str) -> list[int]:
    return [int(m) for m in re.findall(r"(\d{1,3})\s?%", text)]


def verify(user_query: str, response_text: str) -> VerificationResult:
    policies = {p["topic"]: p for p in load_policy_records()}
    topic = detect_topic(user_query) or detect_topic(response_text)

    if topic is None:
        return VerificationResult(
            authorized=False,
            reason="Response makes a commitment but no matching authorized policy topic "
                   "could be identified. Cannot verify against the policy database.",
            topic=None,
        )

    policy = policies.get(topic)
    if policy is None:
        return VerificationResult(
            authorized=False,
            reason=f"Topic '{topic}' detected but no record exists in the authorized policy database.",
            topic=topic,
        )

    text_lower = response_text.lower()
    violations = []

    mentions_refund = bool(re.search(r"\brefund", text_lower))
    if mentions_refund and policy["max_refund_pct"] == 0:
        violations.append(
            f"claims a 'refund' but {policy['id']} ({policy['title']}) authorizes no refund "
            f"(only credit/discount, if any)."
        )

    mentions_retroactive = any(p in text_lower for p in RETROACTIVE_PHRASES)
    if mentions_retroactive and not policy["retroactive_allowed"]:
        violations.append(
            f"implies compensation after travel has already occurred, but {policy['id']} "
            f"explicitly disallows retroactive claims."
        )

    mentions_waiver = bool(re.search(r"\bwaive|free of charge|no charge\b", text_lower))
    if mentions_waiver and policy["max_discount_pct"] == 0:
        violations.append(
            f"offers to waive a fee or provide it free of charge, but {policy['id']} "
            f"authorizes no fee waiver."
        )

    authorized_dollar_amounts = set(_extract_dollar_amounts(policy["authorized_text"]))
    response_dollar_amounts = set(_extract_dollar_amounts(response_text))
    unverified_amounts = response_dollar_amounts - authorized_dollar_amounts
    if unverified_amounts:
        violations.append(
            f"cites dollar amount(s) {sorted(unverified_amounts)} not present in the authorized "
            f"policy text for {policy['id']}."
        )

    response_pcts = _extract_percentages(response_text)
    max_pct_allowed = max(policy["max_refund_pct"], policy["max_discount_pct"])
    for pct in response_pcts:
        if pct > max_pct_allowed:
            violations.append(
                f"cites {pct}%, which exceeds the {max_pct_allowed}% maximum authorized under {policy['id']}."
            )

    if violations:
        return VerificationResult(
            authorized=False,
            reason=" ".join(violations),
            topic=topic,
            matched_policy=policy,
        )

    return VerificationResult(
        authorized=True,
        reason=f"Claims are consistent with authorized policy {policy['id']} ({policy['title']}).",
        topic=topic,
        matched_policy=policy,
        citations=[policy["id"]],
    )
