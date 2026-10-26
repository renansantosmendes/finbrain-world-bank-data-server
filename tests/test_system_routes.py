"""Tests of the system routes: /health and /version."""

from world_bank_api.config import SERVER_VERSION, WBDATA_VERSION


def test_health_answers_ok(client, gateway):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_does_not_call_the_world_bank(client, gateway):
    client.get("/health")

    assert gateway.calls == []


def test_version_reports_server_and_wbdata_versions(client):
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"server": SERVER_VERSION, "wbdata": WBDATA_VERSION}


def test_version_does_not_call_the_world_bank(client, gateway):
    client.get("/version")

    assert gateway.calls == []
