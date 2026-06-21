"""Utilization Analytics Agent service (formerly "claims analytics").

Analyzes claim and spending patterns: per-claim cost breakdowns and
per-patient claim/utilization totals.
"""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Claim, ClaimTransaction, Payer
from app.schemas import ClaimAnalytics
from app.services.patient_service import patient_profile

ZERO = Decimal("0")


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


def _money(value) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(Decimal("0.01"))
