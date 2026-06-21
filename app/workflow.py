from time import perf_counter
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.schemas import AgentTiming, SummaryResponse
from app.services import (
    RetrievalService,
    generate_summary_text,
    medication_intelligence,
    patient_claim_totals,
    patient_profile,
    patient_timeline,
    procedure_intelligence,
)


class WorkflowState(TypedDict, total=False):
    db: Session
    patient_id: str
    question: str | None
    profile: Any
    timeline: Any
    procedures: Any
    medications: Any
    claims: Any
    context: Any
    summary: str
    llm_used: bool
    timings: list[dict[str, Any]]


def _timed(name, function):
    def node(state: WorkflowState) -> dict:
        started = perf_counter()
        result = function(state)
        timing = {"agent": name, "duration_ms": round((perf_counter() - started) * 1000, 2)}
        return {**result, "timings": [*state.get("timings", []), timing]}

    return node


def _context(state):
    return {"profile": patient_profile(state["db"], state["patient_id"])}


def _timeline(state):
    return {"timeline": patient_timeline(state["db"], state["patient_id"])}


def _claims(state):
    return {"claims": patient_claim_totals(state["db"], state["patient_id"])}


def _medications(state):
    return {"medications": medication_intelligence(state["db"], state["patient_id"])}


def _procedures(state):
    return {"procedures": procedure_intelligence(state["db"], state["patient_id"])}


def _retrieval(state):
    profile = state["profile"]
    condition_terms = ", ".join(item.description for item in profile.conditions[:8])
    query = state.get("question") or f"patient conditions and medications: {condition_terms}"
    return {"context": RetrievalService().search(state["db"], query)}


def _summary(state):
    text, used = generate_summary_text(
        state["profile"],
        state["timeline"],
        state["medications"],
        state["claims"],
        state["context"],
        state.get("question"),
    )
    return {"summary": text, "llm_used": used}


builder = StateGraph(WorkflowState)
builder.add_node("patient_context_agent", _timed("patient_context_agent", _context))
builder.add_node("timeline_agent", _timed("timeline_agent", _timeline))
builder.add_node("claims_analytics_agent", _timed("claims_analytics_agent", _claims))
builder.add_node("procedure_history_agent", _timed("procedure_history_agent", _procedures))
builder.add_node("medication_intelligence_agent", _timed("medication_intelligence_agent", _medications))
builder.add_node("retrieval_agent", _timed("retrieval_agent", _retrieval))
builder.add_node("summary_agent", _timed("summary_agent", _summary))
builder.add_edge(START, "patient_context_agent")
builder.add_edge("patient_context_agent", "timeline_agent")
builder.add_edge("timeline_agent", "claims_analytics_agent")
builder.add_edge("claims_analytics_agent", "procedure_history_agent")
builder.add_edge("procedure_history_agent", "medication_intelligence_agent")
builder.add_edge("medication_intelligence_agent", "retrieval_agent")
builder.add_edge("retrieval_agent", "summary_agent")
builder.add_edge("summary_agent", END)
workflow = builder.compile()


def run_summary_workflow(
    db: Session,
    patient_id: str,
    question: str | None = None,
) -> SummaryResponse:
    result = workflow.invoke(
        {"db": db, "patient_id": patient_id, "question": question, "timings": []}
    )
    return SummaryResponse(
        patient_id=patient_id,
        summary=result["summary"],
        timeline=result["timeline"][:100],
        procedure_intelligence=result["procedures"],
        medication_intelligence=result["medications"],
        claim_totals=result["claims"],
        retrieved_context=result["context"],
        llm_used=result["llm_used"],
        timings=[AgentTiming(**item) for item in result["timings"]],
    )
