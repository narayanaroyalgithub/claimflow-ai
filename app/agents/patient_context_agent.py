"""Patient Context Agent

Constructs a comprehensive patient profile: demographics, diagnoses,
medications, encounters, and procedures.
"""

from typing import Any

from app.services.patient_service import patient_profile


def run(state: dict[str, Any]) -> dict[str, Any]:
    return {"profile": patient_profile(state["db"], state["patient_id"])}
