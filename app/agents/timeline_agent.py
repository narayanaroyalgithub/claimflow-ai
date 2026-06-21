"""Timeline Agent

Builds a chronological patient history: event sequencing, disease
progression, and historical context across conditions, encounters,
procedures, and medications.
"""

from typing import Any

from app.services.timeline_service import patient_timeline


def run(state: dict[str, Any]) -> dict[str, Any]:
    return {"timeline": patient_timeline(state["db"], state["patient_id"])}
