from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db
from app.models import Patient
from app.schemas import (
    ClaimAnalytics,
    DashboardStats,
    MedicationIntelligence,
    PatientProfile,
    ProcedureIntelligence,
    SummaryRequest,
    SummaryResponse,
    TimelineEvent,
)
from app.seed import seed
from app.services import (
    claim_analytics,
    dashboard_stats,
    medication_intelligence,
    patient_profile,
    patient_timeline,
    procedure_intelligence,
)
from app.workflow import run_summary_workflow

REQUESTS = Counter("claimflow_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("claimflow_http_request_duration_seconds", "HTTP request latency", ["path"])


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.app_env == "development":
        seed()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Agentic healthcare intelligence over synthetic Synthea EHR records.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        REQUESTS.labels(request.method, request.url.path, 500).inc()
        raise
    LATENCY.labels(request.url.path).observe(perf_counter() - started)
    REQUESTS.labels(request.method, request.url.path, response.status_code).inc()
    return response


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "environment": settings.app_env}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/dashboard/stats", response_model=DashboardStats)
def stats(db: Session = Depends(get_db)):
    return dashboard_stats(db)


@app.get("/patients", response_model=list[dict])
def list_patients(
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    statement = select(Patient).order_by(Patient.last_name, Patient.first_name).limit(limit)
    if q:
        statement = statement.where(
            (Patient.first_name.ilike(f"%{q}%"))
            | (Patient.last_name.ilike(f"%{q}%"))
            | (Patient.id.ilike(f"%{q}%"))
        )
    return [
        {
            "id": patient.id,
            "name": f"{patient.first_name} {patient.last_name}",
            "birthdate": patient.birthdate,
            "gender": patient.gender,
            "city": patient.city,
            "state": patient.state,
        }
        for patient in db.scalars(statement).all()
    ]


@app.get("/patients/{patient_id}", response_model=PatientProfile)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    return patient_profile(db, patient_id)


@app.get("/timeline/{patient_id}", response_model=list[TimelineEvent])
def get_timeline(patient_id: str, db: Session = Depends(get_db)):
    return patient_timeline(db, patient_id)


@app.get("/claims/{claim_id}", response_model=ClaimAnalytics)
def get_claim(claim_id: str, db: Session = Depends(get_db)):
    return claim_analytics(db, claim_id)


@app.get("/medications/{patient_id}", response_model=MedicationIntelligence)
def get_medications(patient_id: str, db: Session = Depends(get_db)):
    return medication_intelligence(db, patient_id)


@app.get("/procedures/{patient_id}", response_model=ProcedureIntelligence)
def get_procedures(patient_id: str, db: Session = Depends(get_db)):
    return procedure_intelligence(db, patient_id)


@app.post("/summary", response_model=SummaryResponse)
def create_summary(payload: SummaryRequest, db: Session = Depends(get_db)):
    return run_summary_workflow(db, payload.patient_id, payload.question)


@app.exception_handler(ValueError)
def value_error_handler(_request: Request, error: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(error)})
