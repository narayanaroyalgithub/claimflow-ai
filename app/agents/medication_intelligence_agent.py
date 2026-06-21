"""Medication Intelligence Agent

Analyzes medication history: active medications, duplicate
descriptions, and polypharmacy patterns.
"""

from typing import Any

from app.services.medication_service import medication_intelligence


def run(state: dict[str, Any]) -> dict[str, Any]:
    return {"medications": medication_intelligence(state["db"], state["patient_id"])}
