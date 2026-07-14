"""
Lightweight RAG retriever.

Architecture note: in production this slot is a vector DB such as Qdrant or
Milvus with a proper embedding model. For this self-contained demo we use
TF-IDF cosine similarity (scikit-learn) over two corpora so the project runs
anywhere with zero external services or model downloads:

  1. `support_kb` -- the messy, semi-authoritative help-center content a
     real ingestion pipeline would pull in. This is what an ungated LLM
     would use to answer, and it's exactly the kind of loosely-worded
     content that caused the real Air Canada bereavement-fare hallucination.
  2. `policy_db` -- the immutable, legally-authorized policy records. This
     is the ONLY source the deterministic verifier (see guardrails/verifier.py)
     is allowed to treat as ground truth for any commitment language.

Swap `TfidfRetriever` for a Qdrant-backed retriever without touching the
rest of the pipeline -- it only needs to expose `.search(query, k)`.
"""
import json
import os
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@dataclass
class Document:
    id: str
    title: str
    text: str
    source: str  # "support_kb" or "policy_db"


class TfidfRetriever:
    def __init__(self, documents: list[Document]):
        self.documents = documents
        self._vectorizer = TfidfVectorizer(stop_words="english")
        corpus = [f"{d.title}. {d.text}" for d in documents]
        self._matrix = self._vectorizer.fit_transform(corpus)

    def search(self, query: str, k: int = 3) -> list[tuple[Document, float]]:
        q_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self._matrix).flatten()
        ranked = sorted(zip(self.documents, scores), key=lambda x: x[1], reverse=True)
        return [(doc, float(score)) for doc, score in ranked[:k] if score > 0]


def load_support_kb() -> list[Document]:
    with open(os.path.join(DATA_DIR, "support_kb_raw.json")) as f:
        raw = json.load(f)
    return [
        Document(id=a["id"], title=a["title"], text=a["text"], source="support_kb")
        for a in raw["articles"]
    ]


def load_policy_db() -> list[Document]:
    with open(os.path.join(DATA_DIR, "authorized_policies.json")) as f:
        raw = json.load(f)
    return [
        Document(id=p["id"], title=p["title"], text=p["authorized_text"], source="policy_db")
        for p in raw["policies"]
    ]


def load_policy_records() -> list[dict]:
    """Raw structured policy records (with numeric fields) for the verifier."""
    with open(os.path.join(DATA_DIR, "authorized_policies.json")) as f:
        raw = json.load(f)
    return raw["policies"]


def build_kb_retriever() -> TfidfRetriever:
    return TfidfRetriever(load_support_kb())


def build_policy_retriever() -> TfidfRetriever:
    return TfidfRetriever(load_policy_db())
