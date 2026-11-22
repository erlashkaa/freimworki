import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_rotated_csrf_token_can_be_refreshed_without_disabling_protection():
    client = Client(enforce_csrf_checks=True)
    user = User.objects.create_user(
        "csrf_user", password="Example-strong-937!",
    )
    old_token = client.get("/api/session/").json()["csrfToken"]
    data = {"username": user.username, "password": "Example-strong-937!"}
    response = client.post("/api/login/", data,
                           content_type="application/json",
                           HTTP_X_CSRFTOKEN=old_token)
    assert response.status_code == 200

    response = client.post("/api/login/", data,
                           content_type="application/json",
                           HTTP_X_CSRFTOKEN=old_token)
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"
    fresh_token = client.get("/api/session/").json()["csrfToken"]
    response = client.post("/api/login/", data,
                           content_type="application/json",
                           HTTP_X_CSRFTOKEN=fresh_token)
    assert response.status_code == 200


@pytest.mark.parametrize("mode, expected", [
    ("cookie", "cookie_missing"),
    ("token", "token_missing"),
    ("origin", "origin_mismatch"),
])
def test_csrf_failure_explains_reason(mode, expected):
    client = Client(enforce_csrf_checks=True)
    headers = {}
    if mode != "cookie":
        token = client.get("/api/session/").json()["csrfToken"]
        if mode == "origin":
            headers = {
                "HTTP_X_CSRFTOKEN": token,
                "HTTP_ORIGIN": "https://untrusted.example",
            }
    response = client.post(
        "/api/login/", {}, content_type="application/json", **headers,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == expected
