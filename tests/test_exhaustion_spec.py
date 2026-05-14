from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from gaming_research.kernel.types import Options
from gaming_research.exhaustion.spec import (
    CURRENT_SPEC, GridSpec, PointsSegment, RangeSegment,
    estimate_case_count, reduction_eligible,
)

FIXTURES = Path(__file__).parent / "fixtures" / "exhaustion"

_default_options = Options()


def _v2_payload() -> dict:
    return json.loads((FIXTURES / "v2_spec.json").read_text(encoding="utf-8"))


def _v1_payload() -> dict:
    return json.loads((FIXTURES / "v1_spec.json").read_text(encoding="utf-8"))


def test_current_spec_valid_pair_count():
    pairs = [
        (min1, min2)
        for min1 in CURRENT_SPEC.min1_values
        for min2 in CURRENT_SPEC.min2_values
        if (min1 + CURRENT_SPEC.span1 / 2) - (min2 + CURRENT_SPEC.span2 / 2) >= CURRENT_SPEC.avg_diff_min
    ]
    assert len(pairs) == 35


def test_estimate_case_count_reduction():
    assert estimate_case_count(CURRENT_SPEC, _default_options) == 3920


def test_estimate_case_count_full_grid():
    opts = Options(enforce_war_payoff_s1=False)
    assert estimate_case_count(CURRENT_SPEC, opts) == 14_112_000


def test_reduction_eligible_default():
    assert reduction_eligible(CURRENT_SPEC, _default_options) is True


def test_reduction_eligible_war_payoff_off():
    opts = Options(enforce_war_payoff_s1=False)
    assert reduction_eligible(CURRENT_SPEC, opts) is False


def test_v2_spec_parses():
    spec, migrated = GridSpec.from_dict_with_meta(_v2_payload())
    assert migrated is False
    assert spec.c1 == (RangeSegment(
        min=Decimal("5.1"), max=Decimal("5.6"), step=Decimal("0.01"),
    ),)
    assert spec.c2 == (RangeSegment(
        min=Decimal("11.2"), max=Decimal("11.7"), step=Decimal("0.01"),
    ),)


def test_v1_auto_migration_equivalent_to_v2():
    v1_spec, migrated = GridSpec.from_dict_with_meta(_v1_payload())
    assert migrated is True
    v2_spec, _ = GridSpec.from_dict_with_meta(_v2_payload())
    assert v1_spec == v2_spec


def test_v2_rejects_legacy_field():
    payload = _v2_payload()
    payload["c1_min"] = "0.1"
    with pytest.raises(ValueError, match="must not contain legacy field"):
        GridSpec.from_dict(payload)


def test_v1_rejects_v2_field():
    payload = _v1_payload()
    payload["c1"] = [{"type": "range", "min": "0.1", "max": "0.5", "step": "0.1"}]
    with pytest.raises(ValueError, match="must not contain v2 field"):
        GridSpec.from_dict(payload)


def test_missing_schema_version_mixed_fields_rejected():
    payload = _v2_payload()
    del payload["schema_version"]
    payload["c1_min"] = "0.1"
    with pytest.raises(ValueError, match=r"mixes v1 fields .* and v2 fields"):
        GridSpec.from_dict(payload)


def test_empty_segment_list_rejected():
    payload = _v2_payload()
    payload["c1"] = []
    with pytest.raises(ValueError, match="c1 must contain at least one segment"):
        GridSpec.from_dict(payload)


def test_invalid_segment_type_rejected():
    payload = _v2_payload()
    payload["c1"] = [{"type": "bogus", "min": "0", "max": "1", "step": "0.1"}]
    with pytest.raises(ValueError, match="must be 'range' or 'points'"):
        GridSpec.from_dict(payload)


def test_range_step_non_positive_rejected():
    payload = _v2_payload()
    payload["c1"] = [{"type": "range", "min": "0.1", "max": "0.5", "step": "0"}]
    with pytest.raises(ValueError, match=r"c1\[0\]\.step .* must be > 0"):
        GridSpec.from_dict(payload)


def test_range_min_gt_max_rejected():
    payload = _v2_payload()
    payload["c1"] = [{"type": "range", "min": "9", "max": "1", "step": "0.1"}]
    with pytest.raises(ValueError, match=r"c1\[0\]\.min .* must be <= max"):
        GridSpec.from_dict(payload)


def test_points_empty_values_rejected():
    payload = _v2_payload()
    payload["c1"] = [{"type": "points", "values": []}]
    with pytest.raises(ValueError, match=r"c1\[0\]\.values must be a non-empty list"):
        GridSpec.from_dict(payload)
