"""API contract smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_sample_endpoint_returns_puzzle(client: TestClient) -> None:
    response = client.get("/api/v1/puzzles/sample")
    payload = response.json()
    assert response.status_code == 200
    assert payload["demo_mode"] is True
    assert len(payload["puzzle"]["groups"]) == 4


def test_generate_endpoint_returns_generated_payload(client: TestClient) -> None:
    response = client.post("/api/v1/puzzles/generate", json={"include_trace": True})
    payload = response.json()
    assert response.status_code == 200
    assert "selected_components" in payload
    assert len(payload["puzzle"]["board_words"]) == 16


def test_latest_evaluation_debug_endpoint_returns_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/debug/evaluation/latest")
    payload = response.json()
    assert response.status_code == 200
    assert "latest" in payload
