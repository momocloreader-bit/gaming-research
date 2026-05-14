from __future__ import annotations

from decimal import Decimal

import pytest

from gaming_research.exhaustion.cli import _spec_to_dict
from gaming_research.exhaustion.spec import CURRENT_SPEC, GridSpec


def _current_dict() -> dict:
    return _spec_to_dict(CURRENT_SPEC)


def test_from_dict_roundtrip_current_spec():
    assert GridSpec.from_dict(_current_dict()) == CURRENT_SPEC


def test_from_dict_without_schema_version_v2_shape():
    d = _current_dict()
    del d["schema_version"]
    assert GridSpec.from_dict(d) == CURRENT_SPEC


def test_rejects_numeric_scalar():
    d = _current_dict()
    d["a1"] = 0.5
    with pytest.raises(ValueError, match="must be a string"):
        GridSpec.from_dict(d)


def test_rejects_numeric_in_list():
    d = _current_dict()
    d["p_values"] = [0.5]
    with pytest.raises(ValueError, match="must be a string"):
        GridSpec.from_dict(d)


def test_rejects_non_list_tuple_field():
    d = _current_dict()
    d["min1_values"] = "2"
    with pytest.raises(ValueError, match="must be a list"):
        GridSpec.from_dict(d)


def test_rejects_unknown_field():
    d = _current_dict()
    d["foo"] = "bar"
    with pytest.raises(ValueError, match="unknown spec field: foo"):
        GridSpec.from_dict(d)


def test_rejects_missing_field():
    d = _current_dict()
    del d["c1"]
    with pytest.raises(ValueError, match="missing spec field: c1"):
        GridSpec.from_dict(d)


def test_rejects_unsupported_schema_version():
    d = _current_dict()
    d["schema_version"] = 99
    with pytest.raises(ValueError, match="unsupported schema_version"):
        GridSpec.from_dict(d)


def test_validate_empty_min1():
    d = _current_dict()
    d["min1_values"] = []
    with pytest.raises(ValueError, match="min1_values"):
        GridSpec.from_dict(d)


def test_validate_negative_avg_diff_min():
    d = _current_dict()
    d["avg_diff_min"] = "-1"
    with pytest.raises(ValueError, match="avg_diff_min"):
        GridSpec.from_dict(d)


def test_custom_a1_loads_without_error():
    d = _current_dict()
    d["a1"] = "0.7"
    spec = GridSpec.from_dict(d)
    assert spec.a1 == Decimal("0.7")


def test_rejects_non_dict_input():
    with pytest.raises(ValueError, match="must be a JSON object"):
        GridSpec.from_dict([1, 2, 3])  # type: ignore[arg-type]
