from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PatientDemographics(ORMModel):
    id: str
    first_name: str
    last_name: str
    birthdate: date | None
    deathdate: date | None
    gender: str | None
    race: str | None
    ethnicity: str | None
    city: str | None
    state: str | None


class ConditionRecord(ORMModel):
    start: date
    stop: date | None
    code: str
    description: str


class EncounterRecord(ORMModel):
    id: str
    start: datetime
    stop: datetime | None
    encounter_class: str | None
    code: str | None
    description: str | None
    total_claim_cost: Decimal | None
    payer_coverage: Decimal | None


class ProcedureRecord(ORMModel):
    start: datetime
    stop: datetime | None
    code: str
    description: str
    base_cost: Decimal | None


class MedicationRecord(ORMModel):
    start: datetime
    stop: datetime | None
    code: str
    description: str
    base_cost: Decimal | None
    payer_coverage: Decimal | None
    dispenses: int | None
    total_cost: Decimal | None


class PatientProfile(BaseModel):
    demographics: PatientDemographics
    conditions: list[ConditionRecord]
    encounters: list[EncounterRecord]
    medications: list[MedicationRecord]
    procedures: list[ProcedureRecord]


class TimelineEvent(BaseModel):
    occurred_at: datetime
    event_type: str
    title: str
    code: str | None = None
    status: str | None = None


class MedicationIntelligence(BaseModel):
    medications: list[MedicationRecord]
    active_medications: list[MedicationRecord]
    duplicate_descriptions: list[str]
    active_medication_count: int
    polypharmacy: bool


class ProcedureIntelligence(BaseModel):
    procedures: list[ProcedureRecord]
    procedure_count: int
    inpatient_encounter_count: int
    most_frequent: list[dict[str, str | int]]


class ClaimTransactionRecord(ORMModel):
    id: str
    transaction_type: str
    amount: Decimal | None
    payments: Decimal | None
    adjustments: Decimal | None
    transfers: Decimal | None
    outstanding: Decimal | None
    procedure_code: str | None
    notes: str | None


class ClaimAnalytics(BaseModel):
    claim_id: str
    patient_id: str
    status: str | None
    service_date: datetime | None
    payer_name: str | None
    total_cost: Decimal
    covered_cost: Decimal
    patient_responsibility: Decimal
    adjustments: Decimal
    outstanding: Decimal
    transactions: list[ClaimTransactionRecord]


class SummaryRequest(BaseModel):
    patient_id: str
    question: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional question used to focus retrieval and the generated summary.",
    )


class AgentTiming(BaseModel):
    agent: str
    duration_ms: float


class SummaryResponse(BaseModel):
    patient_id: str
    summary: str
    timeline: list[TimelineEvent]
    procedure_intelligence: ProcedureIntelligence
    medication_intelligence: MedicationIntelligence
    claim_totals: dict[str, Decimal | int]
    retrieved_context: list[dict[str, str]]
    llm_used: bool
    timings: list[AgentTiming]
    disclaimer: str = "Synthetic data and AI-generated output; not for clinical decision-making."


class DashboardStats(BaseModel):
    patients: int
    encounters: int
    conditions: int
    claims: int
    medications: int
