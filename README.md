---
title: AIRCANADA GUARDRAIL
emoji: ✈️
colorFrom: red
colorTo: gray
sdk: streamlit
sdk_version: "1.38.0"
app_file: app.py
pinned: false
---

# AirNova Support — Guardrailed, Rule-Enforced Chatbot

**[View the project landing page](docs/index.html)** (enable GitHub Pages on this repo to host it live — see below) &middot; **[Live interactive demo](https://huggingface.co/spaces/Darkweb007/AIRCANADA_GUARDRAIL)**

**Portfolio project 1 of 5** — a demo response to the [Moffatt v. Air Canada](https://www.cbc.ca/news/canada/british-columbia/air-canada-chatbot-lawsuit-1.7116416)
ruling, where a tribunal held Air Canada liable for its chatbot fabricating a
bereavement refund policy that didn't exist. This project shows the
architecture that prevents that failure: **no commitment-bearing response
reaches the customer unless it's cross-checked against an immutable,
authorized policy database.**

> ⚠️ **All data in this project is synthetic.** `data/authorized_policies.json`
> is a fictional airline's ("AirNova") policy table, and `data/support_kb_raw.json`
> is deliberately messy, loosely-worded synthetic support content designed to
> reproduce the exact failure mode that caused the real lawsuit. No real
> airline data, policies, or customer data is used.

## Why this exists

Air Canada's chatbot answered from a support page about bereavement fares.
The LLM paraphrased loosely-worded, non-authoritative content into a
confident (and wrong) claim: that a passenger could get a refund *after*
traveling. The company argued the chatbot was "a separate legal entity"
responsible for its own words — the tribunal disagreed. The fix isn't a
better prompt. It's an architecture that never lets the LLM be the final
authority on a policy fact.

## Architecture

```
user query
    |
    v
[RAG retrieval over messy support KB]   <- rag/retriever.py (TF-IDF demo; swap for Qdrant/Milvus in prod)
    |
    v
[LLM drafts a response]                 <- generator.py (mock, offline-safe; or real Claude call)
    |
    v
[Commitment classifier]                 <- guardrails/classifier.py (stand-in for NeMo Guardrails / Llama Guard)
    |  no commitment          \\ commitment detected
    v                          v
send as-is          [Deterministic verifier]  <- guardrails/verifier.py
                     cross-checks every claim (refund? amount? %? retroactive? waiver?)
                     against data/authorized_policies.json — the ONLY source
                     of truth, never editable by the LLM.
                          |                  \\
                          | authorized          \\ NOT authorized
                          v                        v
                     send as-is           BLOCK. Replace with verified
                                           policy text. Log to audit trail.
```

The verifier is intentionally simple and rule-based (regex + a hardcoded
JSON table) rather than another model — that's the point. The one component
standing between an LLM and a legally-binding customer commitment should be
boring, deterministic, and auditable, not another probabilistic system that
can itself hallucinate.

## Try it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Toggle **guardrails off** in the sidebar and ask:

> *"My father passed away and I already flew home for the funeral — can I get a refund?"*

The mock generator will draft the same fabricated retroactive-refund promise
that got Air Canada sued. With **guardrails on**, the verifier catches it
(claims a refund when only a 5% pre-booking discount is authorized, and
implies retroactive compensation when the policy explicitly disallows it)
and replaces it with the real, authorized policy text — logged to the audit
panel.

Other topics worth trying: flight cancellations, delayed/lost baggage,
overbooking, medical-emergency cancellations, pet fees, unaccompanied
minors. Some drafts are legitimately authorized and pass through; others get
blocked — the audit log shows why in each case.

### Real LLM mode

Set `ANTHROPIC_API_KEY` and switch the sidebar radio to "Real LLM" to see
Claude draft from the same messy KB context instead of the mock generator.
The verifier gate works identically regardless of which model produced the
draft — that's the architectural point: guardrails don't trust the
generator, no matter how good it is.

## Project structure

```
airline-guardrail-bot/
├── app.py                        # Streamlit UI
├── pipeline.py                   # orchestrates retrieval -> generation -> guardrails
├── generator.py                  # mock + real (Claude) response generation
├── guardrails/
│   ├── classifier.py             # commitment-language detector
│   ├── topics.py                 # keyword -> policy topic mapping
│   └── verifier.py               # deterministic cross-check vs authorized_policies.json
├── rag/
│   └── retriever.py               # TF-IDF retrieval (swap for Qdrant/Milvus in prod)
├── data/
│   ├── authorized_policies.json  # SYNTHETIC immutable policy DB (source of truth)
│   └── support_kb_raw.json       # SYNTHETIC messy support content (RAG corpus)
└── requirements.txt
```

## Production upgrade path

| Demo component | Production equivalent |
|---|---|
| TF-IDF retriever | Qdrant / Milvus + real embedding model |
| Regex commitment classifier | Fine-tuned classifier, or NVIDIA NeMo Guardrails / Llama Guard |
| JSON policy file | Governed policy microservice, legal-reviewed, versioned, access-controlled |
| Rule-based verifier | Same architecture, hardened claim extraction (NLI model or structured-output LLM constrained to the policy schema) |

## Project landing page

`docs/index.html` is a standalone, single-file static landing page (no build step) summarizing the project's results, method, and findings. To host it live on GitHub Pages: repo **Settings → Pages → Source: Deploy from a branch → Branch: main, folder: /docs → Save**. It'll be live within a minute or two at `https://data-geek-astronomy.github.io/AIRCANADA_GUARDRAIL/`.
