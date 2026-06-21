"""Procedure History Agent

Understands prior procedures: counts, frequency, and inpatient
encounter history.
"""

from typing import Any

from app.services.procedure_service import procedure_intelligence


def run(state: dict[str, Any]) -> dict[str, Any]:
    return {"procedures": procedure_intelligence(state["db"], state["patient_id"])}
