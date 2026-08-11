from unittest.mock import patch

from app.extensions import db


def test_healthz_returns_200_without_auth(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_readyz_returns_200_when_db_healthy(app, client):
    with app.app_context():
        response = client.get("/readyz")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["db"] == "ready"


def test_readyz_returns_503_when_db_unavailable(app, client):
    with app.app_context(), patch.object(
        db.session, "execute", side_effect=Exception("db down")
    ):
        response = client.get("/readyz")
    assert response.status_code == 503
    data = response.get_json()
    assert data["status"] == "error"
    assert data["db"] == "unavailable"
