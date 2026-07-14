"""Simple keyword-to-policy-topic mapping, shared by retrieval and the verifier.

In production this would be a small intent classifier; keyword matching keeps
the demo dependency-free while still being deterministic and auditable.
"""

from __future__ import annotations

TOPIC_KEYWORDS = {
    "bereavement_fare": ["bereavement", "death", "passed away", "funeral", "died", "loss of a"],
    "flight_cancellation_by_airline": ["cancelled my flight", "you cancelled", "airline cancelled", "flight was cancelled"],
    "voluntary_cancellation": ["cancel my trip", "cancel my booking", "want to cancel", "cancel my ticket"],
    "baggage_delay": ["delayed bag", "bag didn't arrive", "luggage delayed", "bag is late"],
    "baggage_lost": ["lost my bag", "lost luggage", "bag never showed", "missing luggage"],
    "flight_delay_compensation": ["flight delay", "delayed flight", "flight was late", "flight was delayed", "delayed 3", "delayed 4", "delayed hours", "hours late"],
    "overbooking": ["overbook", "bumped", "denied boarding"],
    "medical_emergency_cancellation": ["medical emergency", "hospital", "surgery", "got sick"],
    "pet_travel_fee": ["pet", "dog", "cat", "animal in cabin"],
    "unaccompanied_minor": ["unaccompanied minor", "child flying alone", "kid traveling alone", "flying alone", "traveling alone", "travelling alone", "flies alone", "year old is flying"],
}


def detect_topic(text: str) -> str | None:
    text_lower = text.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return topic
    return None
