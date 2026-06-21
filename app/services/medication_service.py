"""Medication Intelligence Agent service: active medications, duplicate
descriptions, and polypharmacy detection.
"""

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Medication
from app.schemas import MedicationIntelligence
from app.services.patient_service import patient_profile
from app.services.timeline_service import _aware


def medication_intelligence(db: Session, patient_id: str) -> MedicationIntelligence:
    patient_profile(db, patient_id)
    medications = db.scalars(
        select(Medication).where(Medication.patient_id == patient_id).order_by(Medication.start.desc())
    ).all()
    now = datetime.now(timezone.utc)
    active = [m for m in medications if m.stop is None or _aware(m.stop) > now]
    counts = Counter(m.description.casefold() for m in active)
    duplicates = sorted({m.description for m in active if counts[m.description.casefold()] > 1})
    return MedicationIntelligence(
        medications=medications,
        active_medications=active,
        duplicate_descriptions=duplicates,
        active_medication_count=len(active),
        polypharmacy=len(active) >= 5,
    )
