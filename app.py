import os
import streamlit as st

from pipeline import run_pipeline

st.set_page_config(page_title="AirNova Support | Guardrailed Assistant", page_icon="✈️", layout="wide")

# ---------------------------------------------------------------------------
# Theme: deep red / near-black, minimal, high-contrast -- airline-brand feel
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --nova-red: #D0102A;
        --nova-black: #101114;
        --nova-charcoal: #1B1D22;
        --nova-grey: #8A8D96;
    }
    .stApp { background-color: var(--nova-black); color: #F2F2F3; }
    section[data-testid="stSidebar"] { background-color: var(--nova-charcoal); }
    h1, h2, h3 { font-family: -apple-system, 'Helvetica Neue', sans-serif; letter-spacing: -0.02em; }
    .nova-hero { font-size: 2.1rem; font-weight: 700; margin-bottom: 0; }
    .nova-sub { color: var(--nova-grey); font-size: 0.95rem; margin-top: 0.2rem; }
    .nova-badge {
        display: inline-block; padding: 3px 10px; border-radius: 999px;
        font-size: 0.75rem; font-weight: 600; letter-spacing: 0.03em;
    }
    .badge-on { background: rgba(46, 204, 113, 0.15); color: #2ECC71; border: 1px solid #2ECC71; }
    .badge-off { background: rgba(208, 16, 42, 0.15); color: var(--nova-red); border: 1px solid var(--nova-red); }
    .nova-card {
        background: var(--nova-charcoal); border: 1px solid #2A2D34; border-radius: 14px;
        padding: 16px 18px; margin-bottom: 10px;
    }
    .nova-blocked { border-left: 4px solid var(--nova-red); }
    .nova-passed { border-left: 4px solid #2ECC71; }
    .stChatMessage { background: var(--nova-charcoal); border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []

with st.sidebar:
    st.markdown("### ✈️ AirNova Assistant")
    st.caption("Deterministic Rule-Enforced Support Agent — demo")

    guardrails_on = st.toggle("Guardrails enabled", value=True)
    st.markdown(
        f'<span class="nova-badge {"badge-on" if guardrails_on else "badge-off"}">'
        f'{"GUARDRAILS ON" if guardrails_on else "GUARDRAILS OFF — unsafe demo mode"}</span>',
        unsafe_allow_html=True,
    )

    st.divider()
    llm_mode = st.radio(
        "Response generator",
        options=["mock", "real"],
        format_func=lambda m: "Mock (offline, deterministic)" if m == "mock" else "Real LLM (Claude, needs ANTHROPIC_API_KEY)",
    )
    if llm_mode == "real" and not os.environ.get("ANTHROPIC_API_KEY"):
        st.warning("No ANTHROPIC_API_KEY set — will fall back to mock.")

    st.divider()
    st.caption(
        "Try asking: *'My father passed away and I already flew, can I get a refund?'* "
        "with guardrails off, then on, to see the difference."
    )

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.session_state.audit_log = []
        st.rerun()

    st.divider()
    st.markdown("#### 📋 Audit log")
    if not st.session_state.audit_log:
        st.caption("No commitment-bearing responses yet.")
    for entry in reversed(st.session_state.audit_log[-8:]):
        css = "nova-blocked" if entry["blocked"] else "nova-passed"
        icon = "🛑 BLOCKED" if entry["blocked"] else "✅ VERIFIED"
        st.markdown(
            f'<div class="nova-card {css}"><b>{icon}</b><br>'
            f'<span style="color:var(--nova-grey); font-size:0.85rem;">{entry["reason"]}</span></div>',
            unsafe_allow_html=True,
        )

st.markdown('<div class="nova-hero">AirNova Customer Support</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="nova-sub">Every commitment-bearing reply is cross-checked against an immutable, '
    'legally-authorized policy database before it reaches you.</div>',
    unsafe_allow_html=True,
)
st.write("")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("meta"):
            st.caption(msg["meta"])

if prompt := st.chat_input("Ask about refunds, cancellations, baggage, delays..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    result = run_pipeline(prompt, guardrails_enabled=guardrails_on, llm_mode=llm_mode)

    with st.chat_message("assistant"):
        st.markdown(result.final_response)
        if result.blocked:
            st.error(f"⚠️ Original draft blocked by guardrails: {result.verification.reason}", icon="🛑")
            with st.expander("See the unverified LLM draft that was blocked"):
                st.code(result.draft_response)
        elif result.verification and result.verification.authorized:
            st.success(f"✅ Verified against {', '.join(result.verification.citations)}", icon="✅")
        elif not result.guardrails_enabled and result.commitment_detected:
            st.warning(
                "Guardrails are OFF. This commitment-bearing response was sent to the customer "
                "with no verification against the policy database — this is the Air Canada failure mode.",
                icon="⚠️",
            )

    meta = None
    if result.commitment_detected:
        meta = f"Flagged terms: {', '.join(result.flagged_terms)}"
    st.session_state.messages.append({"role": "assistant", "content": result.final_response, "meta": meta})

    if result.commitment_detected and result.guardrails_enabled:
        st.session_state.audit_log.append({
            "blocked": result.blocked,
            "reason": result.verification.reason if result.verification else "",
        })
    st.rerun()
