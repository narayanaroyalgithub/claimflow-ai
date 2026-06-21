"""Summary Agent service: generates a structured natural-language patient
summary via GPT-4o, with a deterministic fallback when no LLM is
configured (e.g. in tests or offline development).
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from openai import OpenAI

from app.config import settings
from app.schemas import MedicationIntelligence, PatientProfile, TimelineEvent
from app.services.utilization_service import _money

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "summary_prompt.txt"
_PROMPT_TEMPLATE = _PROMPT_PATH.read_text()


def generate_summary_text(
    profile: PatientProfile,
    timeline: list[TimelineEvent],
    meds: MedicationIntelligence,
    claims: dict[str, Decimal | int],
    context: list[dict[str, str]],
    question: str | None,
) -> tuple[str, bool]:
    fallback = _deterministic_summary(profile, meds, claims)
    if not settings.openai_api_key:
        return fallback, False

    client = OpenAI(api_key=settings.openai_api_key)
    compact = {
        "patient": profile.demographics.model_dump(mode="json"),
        "conditions": [item.model_dump(mode="json") for item in profile.conditions[:20]],
        "encounters": [item.model_dump(mode="json") for item in profile.encounters[:20]],
        "active_medications": [item.model_dump(mode="json") for item in meds.active_medications[:20]],
        "recent_timeline": [item.model_dump(mode="json") for item in timeline[:30]],
        "claim_totals": {key: str(value) for key, value in claims.items()},
        "retrieved_context": context,
    }
    prompt = _PROMPT_TEMPLATE.format(
        question=question or "General longitudinal overview",
        record=json.dumps(compact, default=str),
    )
    try:
        response = client.responses.create(model=settings.openai_model, input=prompt)
        return response.output_text.strip() or fallback, True
    except Exception:
        return fallback, False


def _deterministic_summary(
    profile: PatientProfile,
    meds: MedicationIntelligence,
    claims: dict[str, Decimal | int],
) -> str:
    patient = profile.demographics
    age = _age(patient.birthdate)
    active_conditions = [condition.description for condition in profile.conditions if not condition.stop]
    conditions = ", ".join(active_conditions[:5]) if active_conditions else "no active conditions recorded"
    active_meds = ", ".join(m.description for m in meds.active_medications[:5])
    medication_text = active_meds or "no active medications recorded"
    inpatient = sum(1 for encounter in profile.encounters if encounter.encounter_class == "inpatient")
    return (
        f"{age}-year-old {patient.gender or 'patient'} with {conditions}. "
        f"The record contains {len(profile.encounters)} encounters, including {inpatient} inpatient "
        f"encounter(s), and {len(profile.procedures)} procedures. Active medications: {medication_text}. "
        f"There are {claims['claim_count']} claim(s), with total recorded charges of "
        f"${_money(claims['total_charged']):,.2f}."
    )


def _age(birthdate) -> int:
    if not birthdate:
        return 0
    today = datetime.now(timezone.utc).date()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
