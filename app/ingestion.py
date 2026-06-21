import argparse
import csv
import io
import logging
import zipfile
from collections.abc import Callable, Iterator
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine, init_db
from app.models import (
    Claim,
    ClaimTransaction,
    Condition,
    Encounter,
    Medication,
    Organization,
    Patient,
    Payer,
    Procedure,
    Provider,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def text(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def number(value: str | None) -> Decimal | None:
    try:
        return Decimal(value) if value not in {None, ""} else None
    except InvalidOperation:
        return None


def integer(value: str | None) -> int | None:
    try:
        return int(value) if value not in {None, ""} else None
    except ValueError:
        return None


def day(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def instant(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


TABLES: list[tuple[str, type, Callable[[dict[str, str]], dict]]] = [
    (
        "patients.csv",
        Patient,
        lambda r: {
            "id": r["Id"],
            "birthdate": day(r["BIRTHDATE"]),
            "deathdate": day(r["DEATHDATE"]),
            "first_name": r["FIRST"],
            "last_name": r["LAST"],
            "gender": text(r["GENDER"]),
            "race": text(r["RACE"]),
            "ethnicity": text(r["ETHNICITY"]),
            "city": text(r["CITY"]),
            "state": text(r["STATE"]),
            "healthcare_expenses": number(r["HEALTHCARE_EXPENSES"]),
            "healthcare_coverage": number(r["HEALTHCARE_COVERAGE"]),
        },
    ),
    (
        "providers.csv",
        Provider,
        lambda r: {
            "id": r["Id"],
            "organization_id": text(r["ORGANIZATION"]),
            "name": r["NAME"],
            "gender": text(r["GENDER"]),
            "speciality": text(r["SPECIALITY"]),
            "city": text(r["CITY"]),
            "state": text(r["STATE"]),
        },
    ),
    (
        "organizations.csv",
        Organization,
        lambda r: {
            "id": r["Id"],
            "name": r["NAME"],
            "address": text(r["ADDRESS"]),
            "city": text(r["CITY"]),
            "state": text(r["STATE"]),
            "phone": text(r["PHONE"]),
        },
    ),
    (
        "payers.csv",
        Payer,
        lambda r: {
            "id": r["Id"],
            "name": r["NAME"],
            "city": text(r["CITY"]),
            "state": text(r["STATE_HEADQUARTERED"]),
            "amount_covered": number(r["AMOUNT_COVERED"]),
            "amount_uncovered": number(r["AMOUNT_UNCOVERED"]),
        },
    ),
    (
        "encounters.csv",
        Encounter,
        lambda r: {
            "id": r["Id"],
            "patient_id": r["PATIENT"],
            "organization_id": text(r["ORGANIZATION"]),
            "provider_id": text(r["PROVIDER"]),
            "payer_id": text(r["PAYER"]),
            "start": instant(r["START"]),
            "stop": instant(r["STOP"]),
            "encounter_class": text(r["ENCOUNTERCLASS"]),
            "code": text(r["CODE"]),
            "description": text(r["DESCRIPTION"]),
            "base_cost": number(r["BASE_ENCOUNTER_COST"]),
            "total_claim_cost": number(r["TOTAL_CLAIM_COST"]),
            "payer_coverage": number(r["PAYER_COVERAGE"]),
        },
    ),
    (
        "conditions.csv",
        Condition,
        lambda r: {
            "patient_id": r["PATIENT"],
            "encounter_id": text(r["ENCOUNTER"]),
            "start": day(r["START"]),
            "stop": day(r["STOP"]),
            "code": r["CODE"],
            "description": r["DESCRIPTION"],
        },
    ),
    (
        "procedures.csv",
        Procedure,
        lambda r: {
            "patient_id": r["PATIENT"],
            "encounter_id": text(r["ENCOUNTER"]),
            "start": instant(r["START"]),
            "stop": instant(r["STOP"]),
            "code": r["CODE"],
            "description": r["DESCRIPTION"],
            "base_cost": number(r["BASE_COST"]),
        },
    ),
    (
        "medications.csv",
        Medication,
        lambda r: {
            "patient_id": r["PATIENT"],
            "payer_id": text(r["PAYER"]),
            "encounter_id": text(r["ENCOUNTER"]),
            "start": instant(r["START"]),
            "stop": instant(r["STOP"]),
            "code": r["CODE"],
            "description": r["DESCRIPTION"],
            "base_cost": number(r["BASE_COST"]),
            "payer_coverage": number(r["PAYER_COVERAGE"]),
            "dispenses": integer(r["DISPENSES"]),
            "total_cost": number(r["TOTALCOST"]),
        },
    ),
    (
        "claims.csv",
        Claim,
        lambda r: {
            "id": r["Id"],
            "patient_id": r["PATIENTID"],
            "provider_id": text(r["PROVIDERID"]),
            "primary_payer_id": text(r["PRIMARYPATIENTINSURANCEID"]),
            "appointment_id": text(r["APPOINTMENTID"]),
            "service_date": instant(r["SERVICEDATE"]),
            "status": text(r["STATUSP"] or r["STATUS1"]),
        },
    ),
    (
        "claims_transactions.csv",
        ClaimTransaction,
        lambda r: {
            "id": r["ID"],
            "claim_id": r["CLAIMID"],
            "patient_id": r["PATIENTID"],
            "transaction_type": r["TYPE"],
            "amount": number(r["AMOUNT"]),
            "payments": number(r["PAYMENTS"]),
            "adjustments": number(r["ADJUSTMENTS"]),
            "transfers": number(r["TRANSFERS"]),
            "outstanding": number(r["OUTSTANDING"]),
            "procedure_code": text(r["PROCEDURECODE"]),
            "notes": text(r["NOTES"]),
            "from_date": instant(r["FROMDATE"]),
        },
    ),
]


def csv_rows(archive: zipfile.ZipFile, filename: str) -> Iterator[dict[str, str]]:
    member = next((name for name in archive.namelist() if name.endswith(f"/{filename}")), None)
    if not member:
        raise FileNotFoundError(f"{filename} not found in dataset archive")
    with archive.open(member) as raw:
        with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
            yield from csv.DictReader(stream)


def load_archive(
    archive_path: str | Path,
    *,
    limit_per_table: int | None = None,
    batch_size: int = 2_000,
    reset: bool = False,
) -> dict[str, int]:
    archive_path = Path(archive_path)
    if not archive_path.exists():
        raise FileNotFoundError(f"Dataset ZIP does not exist: {archive_path}")
    if reset:
        Base.metadata.drop_all(bind=engine)
    init_db()
    loaded: dict[str, int] = {}
    with zipfile.ZipFile(archive_path) as archive, SessionLocal() as db:
        if limit_per_table and settings.database_url.startswith("sqlite"):
            # Independent CSV limits intentionally produce an incomplete relational sample.
            db.connection().exec_driver_sql("PRAGMA foreign_keys=OFF")
        for filename, model, transform in TABLES:
            count = _load_table(
                db,
                archive,
                filename,
                model,
                transform,
                limit=limit_per_table,
                batch_size=batch_size,
            )
            loaded[filename] = count
            logger.info("Loaded %s rows from %s", f"{count:,}", filename)
        if limit_per_table and settings.database_url.startswith("sqlite"):
            db.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
    return loaded


def _load_table(
    db: Session,
    archive: zipfile.ZipFile,
    filename: str,
    model: type,
    transform: Callable[[dict[str, str]], dict],
    *,
    limit: int | None,
    batch_size: int,
) -> int:
    batch: list[dict] = []
    count = 0
    for row in csv_rows(archive, filename):
        batch.append(transform(row))
        if len(batch) >= batch_size:
            db.bulk_insert_mappings(model, batch)
            db.commit()
            count += len(batch)
            batch.clear()
        if limit and count + len(batch) >= limit:
            break
    if batch:
        db.bulk_insert_mappings(model, batch)
        db.commit()
        count += len(batch)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream Synthea CSV files into ClaimFlow AI")
    parser.add_argument("--zip", default=settings.synthea_zip, help="Path to the Synthea CSV ZIP")
    parser.add_argument("--limit", type=int, default=None, help="Optional row limit per CSV")
    parser.add_argument("--batch-size", type=int, default=2000)
    parser.add_argument("--reset", action="store_true", help="Drop existing tables before loading")
    args = parser.parse_args()
    counts = load_archive(
        args.zip,
        limit_per_table=args.limit,
        batch_size=args.batch_size,
        reset=args.reset,
    )
    logger.info("Ingestion complete: %s", counts)


if __name__ == "__main__":
    main()
