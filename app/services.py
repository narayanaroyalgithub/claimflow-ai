import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from openai import OpenAI
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Claim,
    ClaimTransaction,
    Condition,
    Encounter,
    KnowledgeDocument,
    Medication,
    Patient,
    Payer,
    Procedure,
)
from app.schemas import (
    ClaimAnalytics,
    DashboardStats,
    MedicationIntelligence,
    PatientProfile,
    ProcedureIntelligence,
    TimelineEvent,
)


ZERO = Decimal("0")


def patient_profile(db: Session, patient_id: str) -> PatientProfile:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    conditions = db.scalars(
        select(Condition).where(Condition.patient_id == patient_id).order_by(Condition.start.desc())
    ).all()
    encounters = db.scalars(
        select(Encounter).where(Encounter.patient_id == patient_id).order_by(Encounter.start.desc())
    ).all()
    medications = db.scalars(
        select(Medication).where(Medication.patient_id == patient_id).order_by(Medication.start.desc())
    ).all()
    procedures = db.scalars(
        select(Procedure).where(Procedure.patient_id == patient_id).order_by(Procedure.start.desc())
    ).all()
    return PatientProfile(
        demographics=patient,
        conditions=conditions,
        encounters=encounters,
        medications=medications,
        procedures=procedures,
    )


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


def procedure_intelligence(db: Session, patient_id: str) -> ProcedureIntelligence:
    profile = patient_profile(db, patient_id)
    counts = Counter(procedure.description for procedure in profile.procedures)
    frequent = [
        {"description": description, "count": count}
        for description, count in counts.most_common(10)
    ]
    return ProcedureIntelligence(
        procedures=profile.procedures,
        procedure_count=len(profile.procedures),
        inpatient_encounter_count=sum(
            1 for encounter in profile.encounters if encounter.encounter_class == "inpatient"
        ),
        most_frequent=frequent,
    )


def claim_analytics(db: Session, claim_id: str) -> ClaimAnalytics:
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    transactions = db.scalars(
        select(ClaimTransaction)
        .where(ClaimTransaction.claim_id == claim_id)
        .order_by(ClaimTransaction.from_date)
    ).all()
    charges = sum((_money(t.amount) for t in transactions if t.transaction_type == "CHARGE"), ZERO)
    payments = sum((_money(t.payments) for t in transactions), ZERO)
    if payments == ZERO:
        payments = sum(
            (_money(t.amount) for t in transactions if t.transaction_type in {"PAYMENT", "TRANSFERIN"}),
            ZERO,
        )
    adjustments = sum((_money(t.adjustments) for t in transactions), ZERO)
    outstanding = sum((_money(t.outstanding) for t in transactions), ZERO)
    payer = db.get(Payer, claim.primary_payer_id) if claim.primary_payer_id not in {None, "", "0"} else None
    patient_responsibility = max(charges - payments - adjustments, outstanding, ZERO)
    return ClaimAnalytics(
        claim_id=claim.id,
        patient_id=claim.patient_id,
        status=claim.status,
        service_date=claim.service_date,
        payer_name=payer.name if payer else None,
        total_cost=charges,
        covered_cost=payments,
        patient_responsibility=patient_responsibility,
        adjustments=adjustments,
        outstanding=outstanding,
        transactions=transactions,
    )


def patient_claim_totals(db: Session, patient_id: str) -> dict[str, Decimal | int]:
    patient_profile(db, patient_id)
    rows = db.execute(
        select(
            func.count(func.distinct(Claim.id)),
            func.coalesce(
                func.sum(
                    case(
                        (ClaimTransaction.transaction_type == "CHARGE", ClaimTransaction.amount),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(func.sum(ClaimTransaction.payments), 0),
            func.coalesce(func.sum(ClaimTransaction.outstanding), 0),
        )
        .select_from(Claim)
        .outerjoin(ClaimTransaction, ClaimTransaction.claim_id == Claim.id)
        .where(Claim.patient_id == patient_id)
    ).one()
    return {
        "claim_count": int(rows[0] or 0),
        "total_charged": _money(rows[1]),
        "total_paid": _money(rows[2]),
        "outstanding": _money(rows[3]),
    }


def dashboard_stats(db: Session) -> DashboardStats:
    return DashboardStats(
        patients=db.scalar(select(func.count()).select_from(Patient)) or 0,
        encounters=db.scalar(select(func.count()).select_from(Encounter)) or 0,
        conditions=db.scalar(select(func.count()).select_from(Condition)) or 0,
        claims=db.scalar(select(func.count()).select_from(Claim)) or 0,
        medications=db.scalar(select(func.count()).select_from(Medication)) or 0,
    )


class RetrievalService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def embedding(self, text: str) -> list[float]:
        if self.client:
            response = self.client.embeddings.create(
                model=settings.openai_embedding_model,
                input=text,
            )
            return response.data[0].embedding
        return self._local_embedding(text)

    def search(self, db: Session, query: str, limit: int = 3) -> list[dict[str, str]]:
        documents = db.scalars(select(KnowledgeDocument)).all()
        if not documents:
            return []
        query_vector = self.embedding(query)
        scored = []
        for document in documents:
            vector = json.loads(document.embedding_json) if document.embedding_json else self.embedding(document.content)
            scored.append((_cosine(query_vector, vector), document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "title": document.title,
                "source": document.source,
                "content": document.content,
                "score": f"{score:.4f}",
            }
            for score, document in scored[:limit]
        ]

    @staticmethod
    def _local_embedding(text: str, dimensions: int = 256) -> list[float]:
        vector = [0.0] * dimensions
        for token in text.casefold().split():
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


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
    prompt = (
        "Create a concise longitudinal summary of this synthetic patient record. "
        "Separate facts from inferences, never diagnose, mention relevant dates, and state when "
        "information is unavailable. This is decision support, not medical advice.\n\n"
        f"Focus question: {question or 'General longitudinal overview'}\n\n"
        f"Record: {json.dumps(compact, default=str)}"
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


def _money(value) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _age(birthdate) -> int:
    if not birthdate:
        return 0
    today = datetime.now(timezone.utc).date()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))


def _cosine(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    numerator = sum(left[index] * right[index] for index in range(size))
    left_norm = math.sqrt(sum(value * value for value in left[:size]))
    right_norm = math.sqrt(sum(value * value for value in right[:size]))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0
