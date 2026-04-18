"""Integration tests for /api/v1/users (profile + admin-only endpoints)."""

from __future__ import annotations

from datetime import datetime, timezone


class TestProfileEndpoints:
    def test_get_me(self, client, user, user_headers):
        r = client.get("/api/v1/users/me", headers=user_headers)
        assert r.status_code == 200
        assert r.json()["email"] == user.email

    def test_patch_me_updates_names(self, client, user_headers):
        r = client.patch(
            "/api/v1/users/me",
            headers=user_headers,
            json={"first_name": "Updated", "last_name": "Name"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["first_name"] == "Updated"
        assert body["last_name"] == "Name"

    def test_patch_me_empty_payload_is_noop(self, client, user, user_headers):
        r = client.patch("/api/v1/users/me", headers=user_headers, json={})
        assert r.status_code == 200
        assert r.json()["first_name"] == user.first_name


class TestAdminRBAC:
    def test_regular_user_cannot_list_users(self, client, user_headers):
        r = client.get("/api/v1/users", headers=user_headers)
        assert r.status_code == 403

    def test_admin_can_list_users(self, client, user, admin, admin_headers):
        # Seed: user + admin fixtures exist.
        r = client.get("/api/v1/users", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 2
        emails = {item["email"] for item in body["items"]}
        assert {user.email, admin.email} <= emails

    def test_regular_user_cannot_create_user(self, client, user_headers):
        r = client.post(
            "/api/v1/users",
            headers=user_headers,
            json={
                "email": "x@example.com",
                "password": "password123",
                "first_name": "X",
                "last_name": "Y",
                "role": "user",
            },
        )
        assert r.status_code == 403

    def test_admin_creates_user_with_role(self, client, admin_headers):
        r = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "email": "made@example.com",
                "password": "password123",
                "first_name": "Made",
                "last_name": "ByAdmin",
                "role": "admin",
            },
        )
        assert r.status_code == 201
        assert r.json()["role"] == "admin"

    def test_admin_cannot_duplicate_email(self, client, admin, admin_headers):
        r = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "email": admin.email,
                "password": "password123",
                "first_name": "X",
                "last_name": "Y",
                "role": "user",
            },
        )
        assert r.status_code == 400

    def test_admin_can_change_role(self, client, user, admin_headers):
        r = client.patch(
            f"/api/v1/users/{user.id}/role",
            headers=admin_headers,
            params={"role": "admin"},
        )
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_role_change_on_missing_user_404(self, client, admin_headers):
        r = client.patch(
            "/api/v1/users/99999/role",
            headers=admin_headers,
            params={"role": "admin"},
        )
        assert r.status_code == 404

    def test_role_change_on_soft_deleted_user_404(
        self, client, db_session, user, admin_headers
    ):
        user.deleted_at = datetime.now(timezone.utc)
        db_session.commit()
        r = client.patch(
            f"/api/v1/users/{user.id}/role",
            headers=admin_headers,
            params={"role": "admin"},
        )
        assert r.status_code == 404