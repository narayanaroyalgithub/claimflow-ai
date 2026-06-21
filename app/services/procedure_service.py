"""Procedure History Agent service: procedure counts, frequency, and
inpatient encounter history.
"""

from collections import Counter

from sqlalchemy.orm import Session

from app.schemas import ProcedureIntelligence
from app.services.patient_service import patient_profile


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
