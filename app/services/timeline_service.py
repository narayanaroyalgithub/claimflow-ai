"""Timeline Agent service: builds chronological patient history from
conditions, encounters, procedures, and medications.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.schemas import TimelineEvent
from app.services.patient_service import patient_profile


def patient_timeline(db: Session, patient_id: str) -> list[TimelineEvent]:
    profile = patient_profile(db, patient_id)
    events: list[TimelineEvent] = []
    for row in profile.conditions:
        events.append(
            TimelineEvent(
                occurred_at=datetime.combine(row.start, datetime.min.time(), tzinfo=timezone.utc),
                event_type="condition",
                title=row.description,
                code=row.code,
                status="resolved" if row.stop else "active",
            )
        )
    for row in profile.encounters:
        events.append(
            TimelineEvent(
                occurred_at=row.start,
                event_type="encounter",
                title=row.description or row.encounter_class or "Encounter",
                code=row.code,
            )
        )
    for row in profile.procedures:
        events.append(
            TimelineEvent(
                occurred_at=row.start,
                event_type="procedure",
                title=row.description,
                code=row.code,
            )
        )
    for row in profile.medications:
        events.append(
            TimelineEvent(
                occurred_at=row.start,
                event_type="medication",
                title=row.description,
                code=row.code,
                status="stopped" if row.stop else "active",
            )
        )
    return sorted(events, key=lambda event: _aware(event.occurred_at), reverse=True)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
