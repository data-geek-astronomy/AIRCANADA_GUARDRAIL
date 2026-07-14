"""Quick sanity check across all topics -- not a formal test suite, just a
smoke test to confirm the guardrail correctly passes legitimate commitments
and blocks fabricated ones before shipping."""
from pipeline import run_pipeline

QUERIES = [
    ("My father passed away and I already flew home for the funeral, can I get a refund?", "bereavement_fare", True),
    ("AirNova cancelled my flight, what happens now?", "flight_cancellation_by_airline", False),
    ("I want to cancel my trip next week, can I get my money back?", "voluntary_cancellation", True),
    ("My bag was delayed and I had to buy clothes", "baggage_delay", False),
    ("My luggage has been missing for 3 weeks now", "baggage_lost", False),
    ("My flight was delayed 4 hours, what do I get?", "flight_delay_compensation", True),
    ("I got bumped from my overbooked flight", "overbooking", False),
    ("I had a medical emergency and need to cancel my flight", "medical_emergency_cancellation", True),
    ("Can I bring my cat in the cabin?", "pet_travel_fee", True),
    ("My 8 year old is flying alone, what's the process?", "unaccompanied_minor", True),
]

print(f"{'TOPIC':30} {'GUARDRAILS OFF':20} {'GUARDRAILS ON':20} {'expected_block'}")
for query, topic, expected_block in QUERIES:
    off = run_pipeline(query, guardrails_enabled=False, llm_mode="mock")
    on = run_pipeline(query, guardrails_enabled=True, llm_mode="mock")
    status_on = "BLOCKED" if on.blocked else ("VERIFIED" if on.verification else "no-commitment")
    match = "OK" if on.blocked == expected_block else "MISMATCH!!"
    print(f"{topic:30} {'commitment sent raw':20} {status_on:20} expected_block={expected_block} [{match}]")

print("\n--- Full detail for bereavement (the Air Canada case) ---")
r = run_pipeline(QUERIES[0][0], guardrails_enabled=True, llm_mode="mock")
print("DRAFT:", r.draft_response)
print("FINAL:", r.final_response)
print("BLOCKED:", r.blocked)
print("REASON:", r.verification.reason if r.verification else None)
