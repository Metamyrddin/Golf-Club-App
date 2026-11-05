"""Auth, profile, recommendation, catalog and export flows against SQLite."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'fit.db'}")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("MEDICAL_FERNET_KEY", "")
    from app.db import reset_engine

    reset_engine()
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
    reset_engine()


def _auth(client: TestClient, email: str = "ada@example.com") -> dict:
    response = client.post("/api/auth/register", json={"email": email, "password": "correct-horse"})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


PROFILE = {
    "age": 46,
    "height_ft": 5,
    "height_in": 11,
    "weight_lb": 190,
    "gender": "male",
    "body_type": "average",
    "wrist_to_floor_in": 35,
    "handicap": 14,
    "squat_lb": 220,
    "preferred_brands": ["Titleist"],
    "current_brand": "Callaway",
    "medical_flags": ["shoulder"],
}


def test_health_and_rules(client: TestClient):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    rules = client.get("/api/rules")
    ids = {rule["id"] for rule in rules.json()["rules"]}
    assert {"SS-1", "LL-1", "MED-1", "SET-1"} <= ids


def test_catalog_has_three_houses_and_full_bags(client: TestClient):
    brands = client.get("/api/catalog/brands").json()
    assert {brand["name"] for brand in brands} == {"Titleist", "TaylorMade", "Callaway"}
    heads = client.get("/api/catalog/heads").json()
    shafts = client.get("/api/catalog/shafts").json()
    assert len(heads) >= 30
    assert len(shafts) >= 30
    for brand in ("Titleist", "TaylorMade", "Callaway"):
        types = {row["club_type"] for row in heads if row["brand"] == brand}
        assert {"driver", "fairway_wood", "hybrid", "iron_set", "wedge", "putter"} <= types
        assert sum(1 for row in heads if row["brand"] == brand) >= 10
        assert sum(1 for row in shafts if row["brand"] == brand) >= 10


def test_profile_requires_login(client: TestClient):
    assert client.get("/api/profile").status_code == 401


def test_register_login_profile_recommend_feedback_export(client: TestClient):
    headers = _auth(client)
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    saved = client.put("/api/profile", json=PROFILE, headers=headers)
    assert saved.status_code == 200, saved.text
    assert saved.json()["medical_flags"] == ["shoulder"]
    assert saved.json()["medical_storage"] == "plaintext"
    assert saved.json()["height_ft"] == 5
    assert saved.json()["height_in"] == 11
    assert saved.json()["weight_lb"] == 190
    assert "height_cm" not in saved.json()

    fit = client.post("/api/recommendations", json={"use_saved_profile": True}, headers=headers)
    assert fit.status_code == 200, fit.text
    body = fit.json()
    assert body["id"]
    assert len(body["sets"]) == 3
    assert {bag["brand"] for bag in body["sets"]} == {"Titleist", "TaylorMade", "Callaway"}
    assert body["target"]["flex"] != "X"  # shoulder softens
    preference = next(bag for bag in body["sets"] if bag["id"] == "preference")
    assert preference["brand"] == "Titleist"

    listed = client.get("/api/recommendations", headers=headers).json()
    assert any(row["id"] == body["id"] for row in listed)

    feedback = client.post(
        f"/api/recommendations/{body['id']}/feedback",
        json={"taken_to_fitter": True, "rating": 4, "fitter_notes": "Lie board agreed."},
        headers=headers,
    )
    assert feedback.status_code == 200
    assert feedback.json()["taken_to_fitter"] is True

    csv_body = client.get(f"/api/recommendations/{body['id']}/export.csv", headers=headers)
    assert csv_body.status_code == 200
    assert "Driver" in csv_body.text
    pdf = client.get(f"/api/recommendations/{body['id']}/export.pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    exported = client.get(f"/api/recommendations/{body['id']}/export.json", headers=headers).json()
    assert exported["rating"] == 4


def test_anonymous_inline_fit_and_home_page(client: TestClient):
    page = client.get("/")
    assert page.status_code == 200
    assert "Fairway Ledger" in page.text
    assert "/static/body/ectomorph.jpg" in page.text
    assert page.text.count("<details") == 5
    assert "<details" in page.text and "open" not in page.text.split("<form", 1)[1].split("</form", 1)[0]
    demo = client.get("/?demo=average")
    form = demo.text.split("<form", 1)[1].split("</form", 1)[0]
    assert form.count("<details") == 5
    assert form.count(" open") == 4
    assert 'value="average"' in form and "checked" in form
    fit = client.post(
        "/api/recommendations",
        json={"profile": {"age": 74, "height_ft": 5, "height_in": 8, "gender": "male"}, "save": True},
    )
    assert fit.status_code == 200, fit.text
    body = fit.json()
    assert body["target"]["swing_speed_source"] == "estimated"
    assert body["target"]["flex"] == "A"
    sheet = client.get(f"/sheet/{body['id']}")
    assert sheet.status_code == 200
    assert "Control" in sheet.text


def test_duplicate_register_conflicts(client: TestClient):
    _auth(client, "twice@example.com")
    again = client.post("/api/auth/register", json={"email": "twice@example.com", "password": "correct-horse"})
    assert again.status_code == 409
