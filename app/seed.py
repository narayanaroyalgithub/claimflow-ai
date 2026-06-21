import json
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal, init_db
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
from app.vector_store.embeddings import Embedder


PATIENT_ID = "demo-patient-001"
CLAIM_ID = "demo-claim-001"


def seed() -> None:
    init_db()
    with SessionLocal() as db:
        if db.get(Patient, PATIENT_ID):
            return
        db.add(
            Patient(
                id=PATIENT_ID,
                birthdate=date(1962, 4, 12),
                first_name="Maya",
                last_name="Rivera",
                gender="F",
                race="white",
                ethnicity="hispanic",
                city="Springfield",
                state="Massachusetts",
                healthcare_expenses=Decimal("28450.00"),
                healthcare_coverage=Decimal("21740.00"),
            )
        )
        db.flush()
        db.add_all(
            [
                Condition(
                    patient_id=PATIENT_ID,
                    encounter_id="demo-encounter-001",
                    start=date(2019, 3, 10),
                    code="38341003",
                    description="Hypertension",
                ),
                Condition(
                    patient_id=PATIENT_ID,
                    encounter_id="demo-encounter-002",
                    start=date(2021, 8, 20),
                    code="44054006",
                    description="Type 2 diabetes mellitus",
                ),
                Encounter(
                    id="demo-encounter-001",
                    patient_id=PATIENT_ID,
                    start=datetime(2019, 3, 10, 14, 0, tzinfo=timezone.utc),
                    encounter_class="ambulatory",
                    code="185345009",
                    description="Encounter for symptom",
                    base_cost=Decimal("125.00"),
                    total_claim_cost=Decimal("420.00"),
                    payer_coverage=Decimal("320.00"),
                ),
                Encounter(
                    id="demo-encounter-002",
                    patient_id=PATIENT_ID,
                    start=datetime(2021, 8, 20, 9, 30, tzinfo=timezone.utc),
                    encounter_class="outpatient",
                    code="185349003",
                    description="Encounter for check up",
                    base_cost=Decimal("140.00"),
                    total_claim_cost=Decimal("780.00"),
                    payer_coverage=Decimal("640.00"),
                ),
                Procedure(
                    patient_id=PATIENT_ID,
                    encounter_id="demo-encounter-002",
                    start=datetime(2021, 8, 20, 9, 45, tzinfo=timezone.utc),
                    code="166001",
                    description="Hemoglobin A1c measurement",
                    base_cost=Decimal("68.00"),
                ),
                Medication(
                    patient_id=PATIENT_ID,
                    encounter_id="demo-encounter-002",
                    start=datetime(2021, 8, 20, 10, 0, tzinfo=timezone.utc),
                    code="860975",
                    description="Metformin 500 MG Oral Tablet",
                    base_cost=Decimal("12.00"),
                    payer_coverage=Decimal("9.00"),
                    dispenses=24,
                    total_cost=Decimal("288.00"),
                ),
                Medication(
                    patient_id=PATIENT_ID,
                    encounter_id="demo-encounter-001",
                    start=datetime(2019, 3, 10, 15, 0, tzinfo=timezone.utc),
                    code="314076",
                    description="Lisinopril 10 MG Oral Tablet",
                    base_cost=Decimal("10.00"),
                    payer_coverage=Decimal("8.00"),
                    dispenses=36,
                    total_cost=Decimal("360.00"),
                ),
                Payer(
                    id="demo-payer-001",
                    name="Synthetic Health Plan",
                    city="Boston",
                    state="MA",
                    amount_covered=Decimal("100000.00"),
                    amount_uncovered=Decimal("25000.00"),
                ),
                Claim(
                    id=CLAIM_ID,
                    patient_id=PATIENT_ID,
                    primary_payer_id="demo-payer-001",
                    appointment_id="demo-encounter-002",
                    service_date=datetime(2021, 8, 20, 9, 30, tzinfo=timezone.utc),
                    status="CLOSED",
                ),
                ClaimTransaction(
                    id="demo-transaction-001",
                    claim_id=CLAIM_ID,
                    patient_id=PATIENT_ID,
                    transaction_type="CHARGE",
                    amount=Decimal("780.00"),
                    payments=Decimal("640.00"),
                    adjustments=Decimal("40.00"),
                    outstanding=Decimal("100.00"),
                    procedure_code="185349003",
                    notes="Synthetic outpatient claim",
                    from_date=datetime(2021, 8, 20, 9, 30, tzinfo=timezone.utc),
                ),
            ]
        )
        db.commit()
        _seed_knowledge(db)


def _seed_knowledge(db) -> None:
    if db.scalar(select(KnowledgeDocument.id).limit(1)):
        return
    documents = [
        (
            "Hypertension record interpretation",
            "Built-in educational reference",
            "Longitudinal hypertension context commonly includes blood-pressure monitoring, "
            "medication history, comorbidities, and related encounters. This synthetic reference "
            "does not provide treatment recommendations.",
        ),
        (
            "Type 2 diabetes record interpretation",
            "Built-in educational reference",
            "A longitudinal diabetes record can include diagnosis dates, A1c procedures, medication "
            "changes, and utilization patterns. Missing observations must not be inferred.",
        ),
        (
            "Medication reconciliation",
            "Built-in educational reference",
            "Medication reconciliation compares active and historical medication entries, identifies "
            "duplicate descriptions, and flags five or more active medications as a review signal.",
        ),
    ]
    embedder = Embedder()
    for title, source, content in documents:
        db.add(
            KnowledgeDocument(
                title=title,
                source=source,
                content=content,
                embedding_json=json.dumps(embedder.embedding(content)),
            )
        )
    db.commit()


def main() -> None:
    seed()
    print(f"Demo patient: {PATIENT_ID}")
    print(f"Demo claim:   {CLAIM_ID}")


if __name__ == "__main__":
    main()
