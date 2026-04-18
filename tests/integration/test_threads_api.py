"""Integration tests for /api/v1/threads — CRUD, ownership, soft-delete."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.thread import Message, Thread


class TestCreate:
    def test_create_thread_unauthenticated_401(self, client):
        r = client.post("/api/v1/threads", json={"thread_name": "nope"})
        assert r.status_code == 401

    def test_create_thread(self, client, user, user_headers):
        r = client.post(
            "/api/v1/threads",
            headers=user_headers,
            json={"thread_name": "My first chat"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["thread_name"] == "My first chat"
        assert body["user_id"] == user.id

    def test_create_thread_without_name(self, client, user_headers):
        r = client.post("/api/v1/threads", headers=user_headers, json={})
        assert r.status_code == 201
        assert r.json()["thread_name"] is None


class TestListAndGet:
    def test_list_empty(self, client, user_headers):
        r = client.get("/api/v1/threads", headers=user_headers)
        assert r.status_code == 200
        body = r.json()
        assert body == {"items": [], "total": 0, "page": 1, "size": 20, "pages": 0}

    def test_list_paginates_and_shows_message_count(
        self, client, db_session, user, user_headers
    ):
        # Seed: 3 threads, 2 messages in the first one.
        t1 = Thread(user_id=user.id, thread_name="A")
        t2 = Thread(user_id=user.id, thread_name="B")
        t3 = Thread(user_id=user.id, thread_name="C")
        db_session.add_all([t1, t2, t3])
        db_session.commit()
        db_session.add_all(
            [
                Message(thread_id=t1.id, user_request="hi", ai_response="hello"),
                Message(thread_id=t1.id, user_request="more", ai_response="ok"),
            ]
        )
        db_session.commit()

        r = client.get("/api/v1/threads?size=2", headers=user_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert body["pages"] == 2
        assert len(body["items"]) == 2
        by_id = {t["id"]: t for t in body["items"]}
        if t1.id in by_id:
            assert by_id[t1.id]["message_count"] == 2

    def test_get_own_thread(self, client, db_session, user, user_headers):
        t = Thread(user_id=user.id, thread_name="mine")
        db_session.add(t)
        db_session.commit()
        r = client.get(f"/api/v1/threads/{t.id}", headers=user_headers)
        assert r.status_code == 200
        assert r.json()["id"] == t.id

    def test_get_other_users_thread_404(
        self, client, db_session, other_user, user_headers
    ):
        # Ownership check: a user cannot see another user's thread at all.
        t = Thread(user_id=other_user.id, thread_name="theirs")
        db_session.add(t)
        db_session.commit()
        r = client.get(f"/api/v1/threads/{t.id}", headers=user_headers)
        assert r.status_code == 404

    def test_get_nonexistent_thread_404(self, client, user_headers):
        r = client.get("/api/v1/threads/99999", headers=user_headers)
        assert r.status_code == 404


class TestUpdate:
    def test_rename_thread(self, client, db_session, user, user_headers):
        t = Thread(user_id=user.id, thread_name="old")
        db_session.add(t)
        db_session.commit()
        r = client.patch(
            f"/api/v1/threads/{t.id}",
            headers=user_headers,
            json={"thread_name": "new"},
        )
        assert r.status_code == 200
        assert r.json()["thread_name"] == "new"

    def test_update_other_users_thread_404(
        self, client, db_session, other_user, user_headers
    ):
        t = Thread(user_id=other_user.id, thread_name="theirs")
        db_session.add(t)
        db_session.commit()
        r = client.patch(
            f"/api/v1/threads/{t.id}",
            headers=user_headers,
            json={"thread_name": "hijack"},
        )
        assert r.status_code == 404

    def test_empty_update_is_noop(self, client, db_session, user, user_headers):
        t = Thread(user_id=user.id, thread_name="keep")
        db_session.add(t)
        db_session.commit()
        r = client.patch(
            f"/api/v1/threads/{t.id}", headers=user_headers, json={}
        )
        assert r.status_code == 200
        assert r.json()["thread_name"] == "keep"


class TestDelete:
    def test_soft_delete_thread_and_messages(
        self, client, db_session, user, user_headers
    ):
        t = Thread(user_id=user.id, thread_name="bye")
        db_session.add(t)
        db_session.commit()
        db_session.add(Message(thread_id=t.id, user_request="hi", ai_response="ok"))
        db_session.commit()

        r = client.delete(f"/api/v1/threads/{t.id}", headers=user_headers)
        assert r.status_code == 204

        # Thread is hidden from list/get
        assert client.get(f"/api/v1/threads/{t.id}", headers=user_headers).status_code == 404
        list_body = client.get("/api/v1/threads", headers=user_headers).json()
        assert t.id not in {item["id"] for item in list_body["items"]}

        # Underlying rows still exist with deleted_at set (no hard delete)
        db_session.expire_all()
        row = db_session.query(Thread).filter(Thread.id == t.id).first()
        assert row is not None
        assert row.deleted_at is not None
        msg_rows = db_session.query(Message).filter(Message.thread_id == t.id).all()
        assert msg_rows and all(m.deleted_at is not None for m in msg_rows)

    def test_delete_other_users_thread_404(
        self, client, db_session, other_user, user_headers
    ):
        t = Thread(user_id=other_user.id, thread_name="theirs")
        db_session.add(t)
        db_session.commit()
        r = client.delete(f"/api/v1/threads/{t.id}", headers=user_headers)
        assert r.status_code == 404

        # Untouched on the other user's side
        db_session.expire_all()
        assert db_session.query(Thread).filter(
            Thread.id == t.id
        ).first().deleted_at is None