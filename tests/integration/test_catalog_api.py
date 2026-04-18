"""Integration tests for /api/v1/catalog — public, read-only browsing."""

from __future__ import annotations

import pytest


CATEGORIES = [
    "cpu", "gpu", "mobo", "memory", "case",
    "storage", "cpu_cooler", "psu", "case_fans",
]


class TestCoverage:
    @pytest.mark.parametrize("category", CATEGORIES)
    def test_every_category_has_a_list_route(self, client, category):
        # No auth required for catalog browsing.
        r = client.get(f"/api/v1/catalog/{category}")
        assert r.status_code == 200, r.text


class TestListFilterSort:
    def test_pagination_shape(self, client, seeded_catalog):
        r = client.get("/api/v1/catalog/cpu?page=1&size=1")
        assert r.status_code == 200
        body = r.json()
        assert {"items", "total", "page", "size", "pages"} <= body.keys()
        assert body["size"] == 1
        assert len(body["items"]) == 1
        assert body["total"] == 2

    def test_search_by_name(self, client, seeded_catalog):
        r = client.get("/api/v1/catalog/cpu?search=CPU 1")
        assert r.status_code == 200
        names = [item["name"] for item in r.json()["items"]]
        assert names == ["Test CPU 1"]

    def test_min_max_price_filter(self, client, seeded_catalog):
        # cpu1 = 299.99, cpu2 = 599.00. min=500 → only cpu2.
        r = client.get("/api/v1/catalog/cpu?min_price=500")
        assert r.status_code == 200
        names = {item["name"] for item in r.json()["items"]}
        assert names == {"Test CPU 2"}

        r2 = client.get("/api/v1/catalog/cpu?max_price=300")
        assert r2.status_code == 200
        names2 = {item["name"] for item in r2.json()["items"]}
        assert names2 == {"Test CPU 1"}

    def test_sort_asc_and_desc(self, client, seeded_catalog):
        asc = client.get("/api/v1/catalog/cpu?sort_by=price&order=asc").json()["items"]
        desc = client.get("/api/v1/catalog/cpu?sort_by=price&order=desc").json()["items"]
        assert [i["name"] for i in asc] == ["Test CPU 1", "Test CPU 2"]
        assert [i["name"] for i in desc] == ["Test CPU 2", "Test CPU 1"]

    def test_invalid_sort_column_400(self, client, seeded_catalog):
        r = client.get("/api/v1/catalog/cpu?sort_by=; DROP TABLE cpu")
        # Important: invalid columns must 400, never hit the DB.
        assert r.status_code == 400
        assert "Invalid sort_by" in r.json()["detail"]

    def test_negative_price_rejected_by_query_validation(self, client):
        r = client.get("/api/v1/catalog/cpu?min_price=-1")
        assert r.status_code == 422

    def test_excessive_page_size_rejected(self, client):
        r = client.get("/api/v1/catalog/cpu?size=1000")
        assert r.status_code == 422


class TestDetailEndpoint:
    def test_get_by_id(self, client, seeded_catalog):
        cid = seeded_catalog["cpu1"].id
        r = client.get(f"/api/v1/catalog/cpu/{cid}")
        assert r.status_code == 200
        assert r.json()["id"] == cid
        assert r.json()["name"] == "Test CPU 1"

    def test_get_missing_id_404(self, client):
        r = client.get("/api/v1/catalog/cpu/99999")
        assert r.status_code == 404

    def test_unknown_category_404(self, client):
        # No route registered for this category → FastAPI returns 404.
        r = client.get("/api/v1/catalog/notreal")
        assert r.status_code == 404