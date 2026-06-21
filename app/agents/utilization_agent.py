"""Utilization Analytics Agent

Formerly named "Claims Analytics Agent" — renamed because that name
reads like revenue-cycle-management automation, which is not what this
platform does. This agent analyzes claim and spending patterns for a
patient: total spend, covered amount, and outstanding balance.
"""

from typing import Any

from app.services.utilization_service import patient_claim_totals


def run(state: dict[str, Any]) -> dict[str, Any]:
    return {"claims": patient_claim_totals(state["db"], state["patient_id"])}
