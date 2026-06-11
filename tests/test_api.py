import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "diff-guard"

def test_webhook_missing_header():
    response = client.post("/webhook", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing X-GitHub-Event header"

def test_webhook_ignored_event():
    response = client.post(
        "/webhook",
        headers={"X-GitHub-Event": "issues"},
        json={"action": "opened"}
    )
    assert response.status_code == 200
    assert "Ignored event" in response.json()["status"]

def test_webhook_ignored_action():
    response = client.post(
        "/webhook",
        headers={"X-GitHub-Event": "pull_request"},
        json={"action": "closed"}
    )
    assert response.status_code == 200
    assert "Ignored action" in response.json()["status"]

def test_webhook_accepted_action():
    response = client.post(
        "/webhook",
        headers={"X-GitHub-Event": "pull_request"},
        json={"action": "opened"}
    )
    assert response.status_code == 202
    assert response.json()["status"] == "Analysis queued"
