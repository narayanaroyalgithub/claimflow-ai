# ClaimFlow AI

Agentic healthcare intelligence over MITRE Synthea synthetic EHR data. ClaimFlow AI turns
longitudinal records into patient profiles, timelines, claims analytics, medication intelligence,
retrieved context, and structured summaries.

> This project uses synthetic data and is not a medical device. Outputs are not for diagnosis,
> treatment, billing submission, or clinical decision-making.

## What is implemented

- FastAPI REST API and interactive dashboard
- PostgreSQL/SQLite persistence through SQLAlchemy
- Streaming import of the 565 MB Synthea CSV ZIP (no extraction required)
- Patient, encounter, condition, procedure, medication, claim, claim transaction, provider,
  organization, and payer models
- Correct claims calculations based on `claims_transactions.csv`
- LangGraph workflow with patient context, timeline, claims, medication, retrieval, and summary agents
- OpenAI Responses API (`gpt-4o` by default) and `text-embedding-3-small`
- Fully functional deterministic fallback when `OPENAI_API_KEY` is absent
- Retrieval over embedded knowledge documents
- Prometheus metrics, per-agent timings, health endpoint, tests, Docker, and GitHub Actions CI

## Quick start without Docker

Python 3.10+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

For a zero-configuration local demo, set this in `.env`:

```dotenv
DATABASE_URL=sqlite:///./claimflow.db
APP_ENV=development
```

Then run:

```bash
python -m app.seed
uvicorn app.main:app --reload
```

Open:

- Dashboard: http://localhost:8000
- API docs: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics

Demo identifiers:

```text
Patient: demo-patient-001
Claim:   demo-claim-001
```

## Load the supplied Synthea dataset

Keep large data out of Git. Place `synthea_sample_data_csv_nov2021.zip` in `data/`, or provide its
absolute path:

```bash
python -m app.ingestion \
  --zip /path/to/synthea_sample_data_csv_nov2021.zip \
  --reset
```

The importer streams each CSV directly from the ZIP and commits in batches. For a quick validation:

```bash
python -m app.ingestion --zip /path/to/dataset.zip --reset --limit 100
```

`--limit` is for parser smoke testing only. Each CSV is independently limited, so SQLite temporarily
disables foreign-key checks for this mode and relational coverage is not guaranteed. Use the complete
import for the real application.

## Docker/PostgreSQL

```bash
cp .env.example .env
mkdir -p data
cp /path/to/synthea_sample_data_csv_nov2021.zip data/
docker compose up -d db
docker compose run --rm api python -m app.ingestion --zip /data/synthea_sample_data_csv_nov2021.zip --reset
docker compose up api
```

The database image includes pgvector. The application stores portable JSON embeddings so local
SQLite and PostgreSQL behave consistently; the schema initializes the `vector` extension for
production expansion.

## OpenAI and LangSmith

Add an API key to `.env` to enable model-generated summaries and OpenAI embeddings:

```dotenv
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Without a key, ClaimFlow AI produces deterministic summaries and local hashed embeddings. This
makes CI, portfolio review, and offline development reliable. LangGraph tracing can be enabled using:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=claimflow-ai
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/patients` | Search patients |
| `GET` | `/patients/{patient_id}` | Full patient profile |
| `GET` | `/timeline/{patient_id}` | Chronological longitudinal history |
| `GET` | `/claims/{claim_id}` | Claim financial analytics |
| `GET` | `/medications/{patient_id}` | Medication and polypharmacy analysis |
| `GET` | `/procedures/{patient_id}` | Procedure frequency and inpatient history |
| `POST` | `/summary` | Run the LangGraph intelligence workflow |
| `GET` | `/dashboard/stats` | Dataset counts |
| `GET` | `/health` | Service health |
| `GET` | `/metrics` | Prometheus metrics |

Example:

```bash
curl -X POST http://localhost:8000/summary \
  -H 'Content-Type: application/json' \
  -d '{"patient_id":"demo-patient-001","question":"What changed over time?"}'
```

## Architecture

```text
Synthea ZIP
    │ streaming CSV ingestion
    ▼
PostgreSQL / SQLite ─── Knowledge documents + embeddings
    │
    ▼
Patient Context → Timeline → Claims → Medication → Retrieval → Summary
                              LangGraph
    │
    ▼
FastAPI + Dashboard + Prometheus
```

## Development

```bash
pytest
ruff check .
```

## Data and security notes

- The supplied dataset is synthetic, but the repository excludes ZIP/CSV data by default.
- Never log API keys or place `.env` in Git.
- If adapting this project to real health data, perform a formal HIPAA/security review, add
  authentication and authorization, encryption, audit logging, retention controls, BAA-governed
  vendors, prompt-injection defenses, and human clinical oversight.

## License

Code is provided under the MIT License. Synthea is maintained by MITRE and distributed separately
under its own terms.
