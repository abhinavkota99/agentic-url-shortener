import os
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_greenfield_pauses_for_approval_then_completes():
    response = client.post("/api/workflows", json={
        "requirement":"Build a URL shortener with custom aliases and analytics",
        "scenario":"GREENFIELD"
    })
    assert response.status_code == 202
    workflow = response.json()
    workflow_id = workflow["id"]
    assert workflow["status"] == "WAITING_FOR_APPROVAL"
    assert "architecture" in workflow["artifacts"]

    approved = client.post(f"/api/workflows/{workflow_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "COMPLETED"

def test_ambiguous_requirement_detects_unknowns():
    response = client.post("/api/workflows", json={
        "requirement":"Make the URL shortener faster and improve analytics",
        "scenario":"AMBIGUOUS"
    })
    assert response.status_code == 202
    assert response.json()["artifacts"]["requirements"]["ambiguities"]
