from app.seed import CLAIM_ID, PATIENT_ID


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_patient_profile(client):
    response = client.get(f"/patients/{PATIENT_ID}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["demographics"]["first_name"] == "Maya"
    assert len(payload["conditions"]) == 2
    assert len(payload["medications"]) == 2


def test_claim_analytics(client):
    response = client.get(f"/claims/{CLAIM_ID}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_cost"] == "780.00"
    assert payload["covered_cost"] == "640.00"
    assert payload["patient_responsibility"] == "100.00"


def test_summary_workflow_without_api_key(client):
    response = client.post(
        "/summary",
        json={"patient_id": PATIENT_ID, "question": "Summarize chronic conditions"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_used"] is False
    assert "Hypertension" in payload["summary"]
    assert len(payload["timings"]) == 7
    assert payload["retrieved_context"]
    assert payload["procedure_intelligence"]["procedure_count"] == 1


def test_not_found(client):
    response = client.get("/patients/does-not-exist")
    assert response.status_code == 404
