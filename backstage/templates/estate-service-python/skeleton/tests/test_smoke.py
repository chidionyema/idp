"""The first test, green on the first commit. /healthz is what the cluster and the drill read."""
from fastapi.testclient import TestClient

from ${{ values.pkg }}.app import app


def test_healthz_answers():
    r = TestClient(app).get("/healthz")
    assert r.status_code == 200
    assert r.json()["ok"] is True
