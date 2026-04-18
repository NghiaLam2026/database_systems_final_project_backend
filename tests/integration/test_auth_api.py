"""Integration tests for /api/v1/auth."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


class TestRegister:
    def test_register_creates_user(self, client):
        r = client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "password": "password123",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["email"] == "new@example.com"
        assert body["role"] == "user"
        assert "password" not in body
        assert "password_hash" not in body

    def test_register_duplicate_email_rejected(self, client):
        payload = {
            "email": "dup@example.com",
            "password": "password123",
            "first_name": "A",
            "last_name": "B",
        }
        assert client.post("/api/v1/auth/register", json=payload).status_code == 201
        r = client.post("/api/v1/auth/register", json=payload)
        assert r.status_code == 400
        assert "already registered" in r.json()["detail"].lower()

    @pytest.mark.parametrize(
        "bad_payload",
        [
            {"email": "not-an-email", "password": "password123",
             "first_name": "A", "last_name": "B"},
            {"email": "x@example.com", "password": "short",
             "first_name": "A", "last_name": "B"},
            {"email": "x@example.com", "password": "password123",
             "first_name": "", "last_name": "B"},
            # Missing password entirely
            {"email": "x@example.com", "first_name": "A", "last_name": "B"},
        ],
    )
    def test_register_invalid_payload_422(self, client, bad_payload):
        r = client.post("/api/v1/auth/register", json=bad_payload)
        assert r.status_code == 422


class TestLogin:
    def test_valid_credentials_return_token_and_user(self, client, user):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "password123"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["token_type"] == "bearer"
        assert isinstance(body["access_token"], str) and body["access_token"]
        assert body["user"]["email"] == user.email
        # Never return sensitive fields
        assert "password_hash" not in body["user"]

    def test_wrong_password_returns_401(self, client, user):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "wrong"},
        )
        assert r.status_code == 401

    def test_unknown_email_returns_401(self, client):
        # Same 401 shape as wrong password → no user enumeration.
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "whatever"},
        )
        assert r.status_code == 401

    def test_soft_deleted_user_cannot_log_in(self, client, db_session, user):
        user.deleted_at = datetime.now(timezone.utc)
        db_session.commit()
        r = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "password123"},
        )
        assert r.status_code == 401


class TestMe:
    def test_me_with_valid_token(self, client, user, user_headers):
        r = client.get("/api/v1/auth/me", headers=user_headers)
        assert r.status_code == 200
        assert r.json()["email"] == user.email

    def test_me_without_token_401(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401

    def test_me_with_invalid_token_401(self, client):
        r = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer garbage.token.value"},
        )
        assert r.status_code == 401

    def test_me_with_wrong_scheme_401(self, client, user_headers):
        # Swap Bearer → Basic, same value → should be rejected.
        tok = user_headers["Authorization"].split(" ", 1)[1]
        r = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Basic {tok}"},
        )
        assert r.status_code == 401