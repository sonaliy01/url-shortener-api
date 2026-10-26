from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import Link

def test_create_link_returns_code_and_short_url(client):
    response = client.post("/links", json={"url": "https://example.com/a"})
    assert response.status_code == 201
    body = response.json()
    assert body["code"]
    assert body["short_url"].endswith("/" + body["code"])
    assert body["original_url"] == "https://example.com/a"

def test_custom_alias_and_redirect(client):
    created = client.post("/links", json={"url": "https://example.com/page", "custom_alias": "my-page"})
    assert created.status_code == 201
    redirected = client.get("/my-page", follow_redirects=False)
    assert redirected.status_code == 302
    assert redirected.headers["location"] == "https://example.com/page"

def test_duplicate_alias_returns_helpful_conflict(client):
    payload = {"url": "https://example.com", "custom_alias": "taken"}
    assert client.post("/links", json=payload).status_code == 201
    response = client.post("/links", json=payload)
    assert response.status_code == 409
    assert "already in use" in response.json()["detail"]

def test_unknown_code_returns_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert "No short link exists" in response.json()["detail"]

def test_expired_link_returns_410(client):
    created = client.post("/links", json={"url": "https://example.com", "custom_alias": "old-link"})
    assert created.status_code == 201
    db = SessionLocal()
    try:
        link = db.query(Link).filter(Link.code == "old-link").first()
        link.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.commit()
    finally:
        db.close()
    response = client.get("/old-link", follow_redirects=False)
    assert response.status_code == 410
    assert "has expired" in response.json()["detail"]

def test_click_stats_update(client):
    client.post("/links", json={"url": "https://example.com/destination", "custom_alias": "clickme"})
    before = client.get("/links/clickme/stats")
    assert before.status_code == 200
    assert before.json()["total_clicks"] == 0
    assert before.json()["last_clicked_at"] is None

    redirect = client.get("/clickme", follow_redirects=False)
    assert redirect.status_code == 302

    after = client.get("/links/clickme/stats")
    assert after.status_code == 200
    assert after.json()["total_clicks"] == 1
    assert after.json()["last_clicked_at"] is not None

def test_invalid_url_is_rejected(client):
    response = client.post("/links", json={"url": "ftp://example.com/file"})
    assert response.status_code == 422

def test_alias_validation(client):
    response = client.post("/links", json={"url": "https://example.com", "custom_alias": "bad alias"})
    assert response.status_code == 422

def test_expiry_must_be_in_the_future(client):
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    response = client.post("/links", json={"url": "https://example.com", "expires_at": past})
    assert response.status_code == 422
