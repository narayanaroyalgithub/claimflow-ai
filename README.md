# ClaimFlow AI

### Agentic Healthcare Intelligence Platform Built on Synthetic EHR Data

---

# Overview

ClaimFlow AI is an AI-powered healthcare intelligence platform that transforms fragmented patient records into structured, contextual, and longitudinal patient insights.

Built on MITRE's Synthea synthetic EHR dataset, the system combines FastAPI, PostgreSQL, LangGraph, pgvector, and GPT-4o to create specialized AI agents that retrieve patient context, analyze claims, summarize medical history, and generate clinically meaningful insights.

Rather than automating revenue cycle operations, ClaimFlow AI focuses on healthcare intelligence and contextual understanding, serving as a foundation for downstream clinical and administrative workflows.

---

# Motivation

Healthcare data is fragmented across:

* Encounters
* Conditions
* Procedures
* Medications
* Claims
* Providers
* Payers

Understanding a patient's complete history often requires navigating multiple systems and records.

ClaimFlow AI provides AI-powered context retrieval and longitudinal patient understanding through agent orchestration.

---

# Dataset

## Source

MITRE Synthea™

## Dataset Used

**1K Sample Synthetic Patient Records (CSV)**

Link - https://synthea.mitre.org/downloads 

Contains approximately 1,000 synthetic patients and their longitudinal medical records. 

### Files Used

```text
patients.csv
encounters.csv
conditions.csv
procedures.csv
medications.csv
claims.csv
claims_transactions.csv
providers.csv
organizations.csv
payers.csv
```

### Dataset Properties

* Fully synthetic
* HIPAA-safe
* Open-source
* Realistic longitudinal records
* Suitable for AI and healthcare research

---

# System Architecture

```text
                    Synthea Dataset
                           │
                           ▼
                   Data Loading Pipeline
                           │
                           ▼
                      PostgreSQL
                           │
──────────────────────────────────────────
│          │            │          │
Patient   Claims     Timeline    Medication
Agent      Agent      Agent        Agent
│          │            │          │
──────────────────────────────────────────
                           │
                           ▼
                   Retrieval Agent
                           │
                           ▼
                    Summary Agent
                           │
                           ▼
                     LangGraph Flow
                           │
                           ▼
                       FastAPI APIs
```

---

# Tech Stack

### Backend

* Python
* FastAPI

### Database

* PostgreSQL

### ORM

* SQLAlchemy

### Vector Database

* pgvector

### Agent Framework

* LangGraph

### LLM

* GPT-4o

### Embeddings

* text-embedding-3-small

### Observability

* LangSmith

### Containerization

* Docker

---

# Database Schema

## Patients

Stores demographic information.

```text
patient_id
first_name
last_name
gender
birthdate
race
ethnicity
city
state
```

---

## Conditions

Stores diagnoses and disease history.

Examples:

* Hypertension
* Type 2 Diabetes
* Asthma

---

## Encounters

Stores patient visits.

Examples:

* Emergency visits
* Inpatient admissions
* Outpatient appointments

---

## Procedures

Stores medical procedures performed.

---

## Medications

Stores medications prescribed to patients.

---

## Claims

Stores claim and financial information.

---

## Claims Transactions

Stores payment and adjustment history.

---

## Providers

Stores physician and organization information.

---

## Payers

Stores insurance payer information.

---

# Agent Architecture

---

# 1. Patient Context Agent

### Purpose

Construct a comprehensive patient profile.

### Responsibilities

* Demographics
* Diagnoses
* Medications
* Encounters
* Procedures

### Input

```python
patient_id
```

### Output

```json
{
  "conditions": [...],
  "medications": [...],
  "encounters": [...]
}
```

---

# 2. Timeline Agent

### Purpose

Build chronological patient history.

Example:

```text
2019
Hypertension

2020
Type 2 Diabetes

2022
Hospital Admission

2024
Medication Change
```

### Responsibilities

* Event sequencing
* Disease progression
* Historical context

---

# 3. Claims Analytics Agent

### Purpose

Analyze claim and spending patterns.

### Responsibilities

* Total spend
* Covered amount
* Out-of-pocket costs
* Payer distribution
* Historical claims

### Input

```python
claim_id
```

### Output

```json
{
  "total_cost": 2500,
  "covered_cost": 1800,
  "patient_responsibility": 700
}
```

---

# 4. Procedure History Agent

### Purpose

Understand prior procedures.

Questions answered:

* Has this patient undergone MRI previously?
* Which procedures occurred most frequently?
* How many inpatient encounters exist?

---

# 5. Medication Intelligence Agent

### Purpose

Analyze medication history.

### Responsibilities

* Active medications
* Duplicate medications
* Polypharmacy patterns

---

# 6. Retrieval Agent

### Purpose

Provide domain-specific context through Retrieval-Augmented Generation.

Knowledge Sources

* ICD descriptions
* Procedure descriptions
* Clinical guidelines
* Public medical references

### Pipeline

```text
Query
↓
Embedding
↓
Vector Search
↓
Top-k Retrieval
↓
GPT Context
```

---

# 7. Summary Agent

### Purpose

Generate structured patient summaries.

Example

```text
62-year-old female with hypertension and Type 2 diabetes.

Four encounters in the last three years.

Current medications include metformin and lisinopril.

No prior inpatient admissions.
```

---

# LangGraph Workflow

```text
START
 │
 ▼
Patient Context Agent
 │
 ▼
Timeline Agent
 │
 ▼
Claims Analytics Agent
 │
 ▼
Procedure History Agent
 │
 ▼
Medication Intelligence Agent
 │
 ▼
Retrieval Agent
 │
 ▼
Summary Agent
 │
 ▼
END
```

---

# API Endpoints

## Get Patient Profile

```http
GET /patients/{patient_id}
```

Returns:

* demographics
* conditions
* encounters
* medications

---

## Get Timeline

```http
GET /timeline/{patient_id}
```

Returns chronological history.

---

## Get Claims Analytics

```http
GET /claims/{claim_id}
```

Returns:

* total cost
* covered amount
* patient responsibility

---

## Get Medication History

```http
GET /medications/{patient_id}
```

Returns medication records.

---

## Generate Patient Summary

```http
POST /summary
```

Produces a natural-language patient summary.

---

# Retrieval-Augmented Generation

```text
Medical Documents
        ↓
Chunking
        ↓
Embeddings
        ↓
pgvector
        ↓
Similarity Search
        ↓
Retrieved Context
        ↓
GPT-4o
        ↓
Final Response
```

---

# Observability

Metrics tracked:

### Request Latency

Average processing time per workflow.

---

### Token Usage

Tracks:

* prompt tokens
* completion tokens
* cost

---

### Agent Execution Time

Monitors:

* Patient Agent
* Timeline Agent
* Retrieval Agent
* Summary Agent

---

### Workflow Failures

Categories:

* Database failures
* Retrieval failures
* LLM failures
* Validation failures

---

# Deployment

Dockerized services:

```text
FastAPI
PostgreSQL
pgvector
LangSmith
```

Run:

```bash
docker compose up
```

---

# Future Enhancements

### GraphRAG

Build patient relationship graphs using Neo4j.

---

### Predictive Risk Models

Estimate:

* Hospital readmission risk
* Diabetes progression risk
* Cardiovascular risk

using XGBoost.

---

### Population Health Analytics

Identify:

* High-risk patients
* Frequent hospital utilizers
* Chronic disease cohorts

---

### Human-in-the-loop Review

Support physician and administrator review for low-confidence outputs.

---

# Example Workflow

```text
Patient ID
↓
Retrieve Demographics
↓
Retrieve Conditions
↓
Retrieve Encounters
↓
Retrieve Claims
↓
Retrieve Medications
↓
Retrieve Medical Knowledge
↓
Generate Longitudinal Summary
↓
Return Contextual Insights
```

---

# Resume Description

**ClaimFlow AI | FastAPI, LangGraph, PostgreSQL, pgvector, GPT-4o**

Built an agentic healthcare intelligence platform using MITRE's Synthea dataset that coordinated patient context retrieval, timeline generation, claims analytics, medication analysis, and RAG-powered summarization through LangGraph workflows and FastAPI services, enabling contextual understanding of longitudinal patient records.
