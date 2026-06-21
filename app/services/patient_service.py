"""Patient Context Agent service: demographics, conditions, encounters,
medications, procedures, and overall dashboard counts.
"""

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Claim, Condition, Encounter, Medication, Patient, Procedure
from app.schemas import DashboardStats, PatientProfile


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


def dashboard_stats(db: Session) -> DashboardStats:
    return DashboardStats(
        patients=db.scalar(select(func.count()).select_from(Patient)) or 0,
        encounters=db.scalar(select(func.count()).select_from(Encounter)) or 0,
        conditions=db.scalar(select(func.count()).select_from(Condition)) or 0,
        claims=db.scalar(select(func.count()).select_from(Claim)) or 0,
        medications=db.scalar(select(func.count()).select_from(Medication)) or 0,
    )
