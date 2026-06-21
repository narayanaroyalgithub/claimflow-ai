"""Retrieval Agent

Provides domain-specific context through Retrieval-Augmented
Generation: embeds the patient's condition terms (or an explicit
question), runs top-k similarity search over the knowledge store, and
returns the retrieved context for the Summary Agent.
"""

from typing import Any

from app.vector_store.retriever import Retriever


def run(state: dict[str, Any]) -> dict[str, Any]:
    profile = state["profile"]
    condition_terms = ", ".join(item.description for item in profile.conditions[:8])
    query = state.get("question") or f"patient conditions and medications: {condition_terms}"
    return {"context": Retriever().search(state["db"], query)}
