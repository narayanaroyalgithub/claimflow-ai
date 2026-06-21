from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents import (
    medication_intelligence_agent,
    patient_context_agent,
    procedure_history_agent,
    retrieval_agent,
    summary_agent,
    timeline_agent,
    utilization_agent,
)
from app.observability.tracing import timed_node
from app.schemas import AgentTiming, SummaryResponse


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


builder = StateGraph(WorkflowState)
builder.add_node("patient_context_agent", timed_node("patient_context_agent", patient_context_agent.run))
builder.add_node("timeline_agent", timed_node("timeline_agent", timeline_agent.run))
builder.add_node("utilization_analytics_agent", timed_node("utilization_analytics_agent", utilization_agent.run))
builder.add_node("procedure_history_agent", timed_node("procedure_history_agent", procedure_history_agent.run))
builder.add_node(
    "medication_intelligence_agent",
    timed_node("medication_intelligence_agent", medication_intelligence_agent.run),
)
builder.add_node("retrieval_agent", timed_node("retrieval_agent", retrieval_agent.run))
builder.add_node("summary_agent", timed_node("summary_agent", summary_agent.run))
builder.add_edge(START, "patient_context_agent")
builder.add_edge("patient_context_agent", "timeline_agent")
builder.add_edge("timeline_agent", "utilization_analytics_agent")
builder.add_edge("utilization_analytics_agent", "procedure_history_agent")
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
