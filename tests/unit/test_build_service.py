"""Unit tests for pure helpers in app.services.build."""

from __future__ import annotations

from app.models.base import PartType
from app.services.build import (
    PART_TYPE_LABELS,
    PART_TYPE_MODEL_MAP,
    SINGULAR_PART_TYPES,
    get_part_type_metadata,
)


class TestRegistries:
    def test_every_part_type_has_a_model(self):
        # Missing entries here would cause AttributeError deep in the API.
        for pt in PartType:
            assert pt in PART_TYPE_MODEL_MAP

    def test_every_part_type_has_a_label(self):
        for pt in PartType:
            assert pt in PART_TYPE_LABELS
            assert PART_TYPE_LABELS[pt]  # non-empty

    def test_singular_slots_are_the_expected_set(self):
        assert SINGULAR_PART_TYPES == {
            PartType.CPU,
            PartType.GPU,
            PartType.MOBO,
            PartType.PSU,
            PartType.CASE,
            PartType.CPU_COOLER,
        }


class TestPartTypeMetadata:
    def test_returns_one_entry_per_part_type(self):
        meta = get_part_type_metadata()
        assert len(meta) == len(list(PartType))
        keys = {m["key"] for m in meta}
        assert keys == {pt.value for pt in PartType}

    def test_allow_multiple_matches_singular_set(self):
        meta = {m["key"]: m for m in get_part_type_metadata()}
        for pt in PartType:
            expected = pt not in SINGULAR_PART_TYPES
            assert meta[pt.value]["allow_multiple"] is expected, (
                f"allow_multiple mismatch for {pt}"
            )

    def test_shape_is_stable(self):
        # The UI relies on exactly these three keys.
        for entry in get_part_type_metadata():
            assert set(entry.keys()) == {"key", "label", "allow_multiple"}