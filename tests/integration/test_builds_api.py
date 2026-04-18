"""Integration tests for /api/v1/builds — CRUD, parts, slots, clone, ownership."""

from __future__ import annotations

from decimal import Decimal

from app.models.build import Build


class TestPartTypeMetadata:
    def test_returns_nine_part_types(self, client, user_headers):
        r = client.get("/api/v1/builds/part-types", headers=user_headers)
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 9
        keys = {entry["key"] for entry in body}
        assert keys == {
            "cpu", "gpu", "mobo", "memory", "case", "storage",
            "cpu_cooler", "psu", "case_fans",
        }


class TestBuildCRUD:
    def test_create_and_get(self, client, user, user_headers):
        r = client.post(
            "/api/v1/builds",
            headers=user_headers,
            json={"build_name": "Gaming Rig", "description": "high refresh"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["build_name"] == "Gaming Rig"
        # String representation of 0 differs between SQLite ("0") and Postgres
        # NUMERIC(10,2) ("0.00"); compare as Decimal to stay DB-agnostic.
        assert Decimal(body["total_price"]) == Decimal("0")
        assert body["parts"] == []

        r2 = client.get(f"/api/v1/builds/{body['id']}", headers=user_headers)
        assert r2.status_code == 200
        assert r2.json()["id"] == body["id"]

    def test_list_builds(self, client, user_headers):
        for name in ("A", "B", "C"):
            client.post(
                "/api/v1/builds",
                headers=user_headers,
                json={"build_name": name},
            )
        r = client.get("/api/v1/builds", headers=user_headers)
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 3
        for entry in body:
            assert "parts_count" in entry
            assert "total_price" in entry

    def test_update_build(self, client, user_headers):
        bid = client.post(
            "/api/v1/builds", headers=user_headers, json={"build_name": "old"},
        ).json()["id"]
        r = client.patch(
            f"/api/v1/builds/{bid}",
            headers=user_headers,
            json={"build_name": "new", "description": "updated"},
        )
        assert r.status_code == 200
        assert r.json()["build_name"] == "new"
        assert r.json()["description"] == "updated"

    def test_delete_build_soft_deletes(
        self, client, db_session, user, user_headers
    ):
        bid = client.post(
            "/api/v1/builds", headers=user_headers, json={"build_name": "bye"},
        ).json()["id"]
        r = client.delete(f"/api/v1/builds/{bid}", headers=user_headers)
        assert r.status_code == 204
        # Hidden from API
        assert client.get(f"/api/v1/builds/{bid}", headers=user_headers).status_code == 404
        # Row still exists with deleted_at
        db_session.expire_all()
        row = db_session.query(Build).filter(Build.id == bid).first()
        assert row is not None and row.deleted_at is not None


class TestOwnership:
    def test_cannot_read_other_users_build(
        self, client, db_session, other_user, user_headers
    ):
        b = Build(user_id=other_user.id, build_name="theirs")
        db_session.add(b)
        db_session.commit()
        r = client.get(f"/api/v1/builds/{b.id}", headers=user_headers)
        assert r.status_code == 404

    def test_cannot_update_other_users_build(
        self, client, db_session, other_user, user_headers
    ):
        b = Build(user_id=other_user.id, build_name="theirs")
        db_session.add(b)
        db_session.commit()
        r = client.patch(
            f"/api/v1/builds/{b.id}",
            headers=user_headers,
            json={"build_name": "hijack"},
        )
        assert r.status_code == 404


class TestBuildParts:
    def test_add_part_resolves_component_and_price(
        self, client, seeded_catalog, user_headers
    ):
        bid = client.post(
            "/api/v1/builds", headers=user_headers, json={"build_name": "rig"},
        ).json()["id"]
        r = client.post(
            f"/api/v1/builds/{bid}/parts",
            headers=user_headers,
            json={"part_type": "cpu", "part_id": seeded_catalog["cpu1"].id, "quantity": 1},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["component"]["name"] == "Test CPU 1"
        assert body["component"]["price"] == "299.99"
        assert body["line_total"] == "299.99"

    def test_singular_slot_rejects_second_cpu(
        self, client, seeded_catalog, user_headers
    ):
        bid = client.post(
            "/api/v1/builds", headers=user_headers, json={"build_name": "rig"},
        ).json()["id"]
        assert client.post(
            f"/api/v1/builds/{bid}/parts",
            headers=user_headers,
            json={"part_type": "cpu", "part_id": seeded_catalog["cpu1"].id},
        ).status_code == 201
        r = client.post(
            f"/api/v1/builds/{bid}/parts",
            headers=user_headers,
            json={"part_type": "cpu", "part_id": seeded_catalog["cpu2"].id},
        )
        assert r.status_code == 409
        assert "CPU" in r.json()["detail"]

    def test_non_singular_can_have_multiple(
        self, client, seeded_catalog, user_headers
    ):
        # case_fans allows multiple entries.
        bid = client.post(
            "/api/v1/builds", headers=user_headers, json={"build_name": "rig"},
        ).json()["id"]
        for _ in range(2):
            r = client.post(
                f"/api/v1/builds/{bid}/parts",
                headers=user_headers,
                json={"part_type": "case_fans", "part_id": seeded_catalog["fan"].id},
            )
            assert r.status_code == 201

    def test_add_unknown_component_404(
        self, client, seeded_catalog, user_headers
    ):
        bid = client.post(
            "/api/v1/builds", headers=user_headers, json={"build_name": "rig"},
        ).json()["id"]
        r = client.post(
            f"/api/v1/builds/{bid}/parts",
            headers=user_headers,
            json={"part_type": "cpu", "part_id": 99999},
        )
        assert r.status_code == 404

    def test_update_part_swaps_component(
        self, client, seeded_catalog, user_headers
    ):
        bid = client.post(
            "/api/v1/builds", headers=user_headers, json={"build_name": "rig"},
        ).json()["id"]
        part = client.post(
            f"/api/v1/builds/{bid}/parts",
            headers=user_headers,
            json={"part_type": "gpu", "part_id": seeded_catalog["gpu1"].id},
        ).json()
        r = client.patch(
            f"/api/v1/builds/{bid}/parts/{part['id']}",
            headers=user_headers,
            json={"part_id": seeded_catalog["gpu2"].id},
        )
        assert r.status_code == 200
        assert r.json()["component"]["name"] == "Test GPU 2"

    def test_update_part_with_invalid_component_404(
        self, client, seeded_catalog, user_headers
    ):
        bid = client.post(
            "/api/v1/builds", headers=user_headers, json={"build_name": "rig"},
        ).json()["id"]
        part = client.post(
            f"/api/v1/builds/{bid}/parts",
            headers=user_headers,
            json={"part_type": "gpu", "part_id": seeded_catalog["gpu1"].id},
        ).json()
        r = client.patch(
            f"/api/v1/builds/{bid}/parts/{part['id']}",
            headers=user_headers,
            json={"part_id": 99999},
        )
        assert r.status_code == 404

    def test_remove_part_soft_deletes(
        self, client, seeded_catalog, user_headers
    ):
        bid = client.post(
            "/api/v1/builds", headers=user_headers, json={"build_name": "rig"},
        ).json()["id"]
        pid = client.post(
            f"/api/v1/builds/{bid}/parts",
            headers=user_headers,
            json={"part_type": "gpu", "part_id": seeded_catalog["gpu1"].id},
        ).json()["id"]

        r = client.delete(
            f"/api/v1/builds/{bid}/parts/{pid}", headers=user_headers,
        )
        assert r.status_code == 204

        listing = client.get(f"/api/v1/builds/{bid}/parts", headers=user_headers)
        assert listing.status_code == 200
        assert listing.json() == []

        # After removing the CPU slot holder you can add a different one again.
        # (Regression guard for singular-slot + soft-delete interaction.)
        bid2 = client.post(
            "/api/v1/builds", headers=user_headers, json={"build_name": "rig2"},
        ).json()["id"]
        first_cpu = client.post(
            f"/api/v1/builds/{bid2}/parts",
            headers=user_headers,
            json={"part_type": "cpu", "part_id": seeded_catalog["cpu1"].id},
        ).json()
        client.delete(
            f"/api/v1/builds/{bid2}/parts/{first_cpu['id']}", headers=user_headers,
        )
        r_swap = client.post(
            f"/api/v1/builds/{bid2}/parts",
            headers=user_headers,
            json={"part_type": "cpu", "part_id": seeded_catalog["cpu2"].id},
        )
        assert r_swap.status_code == 201

    def test_total_price_aggregates(
        self, client, seeded_catalog, user_headers
    ):
        bid = client.post(
            "/api/v1/builds", headers=user_headers, json={"build_name": "rig"},
        ).json()["id"]
        client.post(
            f"/api/v1/builds/{bid}/parts",
            headers=user_headers,
            json={"part_type": "cpu", "part_id": seeded_catalog["cpu1"].id, "quantity": 1},
        )
        client.post(
            f"/api/v1/builds/{bid}/parts",
            headers=user_headers,
            json={"part_type": "case_fans", "part_id": seeded_catalog["fan"].id, "quantity": 3},
        )
        detail = client.get(f"/api/v1/builds/{bid}", headers=user_headers).json()
        # 299.99 + 3 * 19.99 = 359.96
        assert Decimal(detail["total_price"]) == Decimal("359.96")


class TestClone:
    def test_clone_copies_parts(self, client, seeded_catalog, user_headers):
        bid = client.post(
            "/api/v1/builds", headers=user_headers, json={"build_name": "orig"},
        ).json()["id"]
        for pt, obj in [
            ("cpu", seeded_catalog["cpu1"]),
            ("gpu", seeded_catalog["gpu1"]),
        ]:
            client.post(
                f"/api/v1/builds/{bid}/parts",
                headers=user_headers,
                json={"part_type": pt, "part_id": obj.id},
            )
        r = client.post(f"/api/v1/builds/{bid}/clone", headers=user_headers)
        assert r.status_code == 201
        clone = r.json()
        assert clone["id"] != bid
        assert clone["build_name"].endswith("(copy)")
        assert {p["part_type"] for p in clone["parts"]} == {"cpu", "gpu"}

    def test_clone_of_other_users_build_404(
        self, client, db_session, other_user, user_headers
    ):
        b = Build(user_id=other_user.id, build_name="theirs")
        db_session.add(b)
        db_session.commit()
        r = client.post(f"/api/v1/builds/{b.id}/clone", headers=user_headers)
        assert r.status_code == 404