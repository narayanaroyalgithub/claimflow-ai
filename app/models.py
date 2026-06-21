from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    birthdate: Mapped[date | None] = mapped_column(Date)
    deathdate: Mapped[date | None] = mapped_column(Date)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    gender: Mapped[str | None] = mapped_column(String(20))
    race: Mapped[str | None] = mapped_column(String(80))
    ethnicity: Mapped[str | None] = mapped_column(String(80))
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(80))
    healthcare_expenses: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    healthcare_coverage: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class Encounter(Base):
    __tablename__ = "encounters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    organization_id: Mapped[str | None] = mapped_column(String(36), index=True)
    provider_id: Mapped[str | None] = mapped_column(String(36), index=True)
    payer_id: Mapped[str | None] = mapped_column(String(36), index=True)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    stop: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    encounter_class: Mapped[str | None] = mapped_column(String(40))
    code: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(Text)
    base_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    total_claim_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    payer_coverage: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class Condition(Base):
    __tablename__ = "conditions"
    __table_args__ = (
        Index("ix_conditions_patient_start_code", "patient_id", "start", "code", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    encounter_id: Mapped[str | None] = mapped_column(String(36), index=True)
    start: Mapped[date] = mapped_column(Date, index=True)
    stop: Mapped[date | None] = mapped_column(Date)
    code: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)


class Procedure(Base):
    __tablename__ = "procedures"
    __table_args__ = (
        Index("ix_procedures_patient_start_code", "patient_id", "start", "code", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    encounter_id: Mapped[str | None] = mapped_column(String(36), index=True)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    stop: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    code: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    base_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class Medication(Base):
    __tablename__ = "medications"
    __table_args__ = (
        Index("ix_medications_patient_start_code", "patient_id", "start", "code", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    encounter_id: Mapped[str | None] = mapped_column(String(36), index=True)
    payer_id: Mapped[str | None] = mapped_column(String(36), index=True)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    stop: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    code: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    base_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    payer_coverage: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    dispenses: Mapped[int | None]
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    provider_id: Mapped[str | None] = mapped_column(String(36), index=True)
    primary_payer_id: Mapped[str | None] = mapped_column(String(36), index=True)
    appointment_id: Mapped[str | None] = mapped_column(String(36), index=True)
    service_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str | None] = mapped_column(String(40))


class ClaimTransaction(Base):
    __tablename__ = "claim_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(30), index=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    payments: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    adjustments: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    transfers: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    outstanding: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    procedure_code: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    from_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str | None] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(200))
    gender: Mapped[str | None] = mapped_column(String(20))
    speciality: Mapped[str | None] = mapped_column(String(120))
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(40))


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(240))
    address: Mapped[str | None] = mapped_column(String(240))
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(40))
    phone: Mapped[str | None] = mapped_column(String(60))


class Payer(Base):
    __tablename__ = "payers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(40))
    amount_covered: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    amount_uncovered: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(240), unique=True)
    source: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    embedding_json: Mapped[str | None] = mapped_column(Text)

