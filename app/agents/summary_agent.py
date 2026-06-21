"""Summary Agent

Generates a structured, natural-language patient summary from the
context gathered by every upstream agent, using GPT-4o with a
deterministic local fallback when no LLM is configured.
"""

from typing import Any

from app.services.summary_service import generate_summary_text


def run(state: dict[str, Any]) -> dict[str, Any]:
    text, used = generate_summary_text(
        state["profile"],
        state["timeline"],
        state["medications"],
        state["claims"],
        state["context"],
        state.get("question"),
    )
    return {"summary": text, "llm_used": used}
