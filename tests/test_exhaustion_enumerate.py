from __future__ import annotations

from decimal import Decimal

import pytest

from gaming_research.kernel.types import Options
from gaming_research.exhaustion.spec import CURRENT_SPEC, GridSpec
from gaming_research.exhaustion.enumerate import enumerate_cases

_default_options = Options()


def test_reduction_path_case_count():
    assert sum(1 for _ in enumerate_cases(CURRENT_SPEC, _default_options)) == 3920


def test_reduction_path_c1_values():
    target = {"5.2", "5.3", "5.4", "5.5"}
    records = [
        r for r in enumerate_cases(CURRENT_SPEC, _default_options)
        if r.raw_fields["min1"] == "2"
        and r.raw_fields["min2"] == "1"
        and r.raw_fields["p"] == "0.3"
    ]
    assert {r.raw_fields["c1"] for r in records} == target


def test_reduction_path_c2_values():
    target = {"11.3", "11.4", "11.5", "11.6"}
    records = [
        r for r in enumerate_cases(CURRENT_SPEC, _default_options)
        if r.raw_fields["min1"] == "2"
        and r.raw_fields["min2"] == "1"
        and r.raw_fields["p"] == "0.3"
    ]
    assert {r.raw_fields["c2"] for r in records} == target


def test_case_id_format():
    first = next(iter(enumerate_cases(CURRENT_SPEC, _default_options)))
    assert first.case_id == "m1=2_m2=1_p=0.3_c1=5.2_c2=11.3"


def test_raw_fields_decimal_text():
    first = next(iter(enumerate_cases(CURRENT_SPEC, _default_options)))
    assert first.raw_fields["min1"] == "2"
    assert first.raw_fields["p"] == "0.3"
    assert first.raw_fields["a1"] == "0.5"


def test_full_grid_path_no_reduction():
    opts = Options(enforce_war_payoff_s1=False)
    first = next(iter(enumerate_cases(CURRENT_SPEC, opts)))
    assert first.raw_fields["c1"] == "0.1"
    assert first.raw_fields["c2"] == "0.1"


def test_avg_diff_min_filter():
    # Build a spec that includes min1=1, min2=1 (avg diff = 0 < 1) — should be skipped.
    spec = GridSpec(
        min1_values=(Decimal("1"), Decimal("2")),
        min2_values=(Decimal("1"),),
        span1=Decimal("15"),
        span2=Decimal("15"),
        a1=Decimal("0.5"),
        a2=Decimal("0.5"),
        p_values=(Decimal("0.5"),),
        c1_min=Decimal("0.1"),
        c1_max=Decimal("24"),
        c1_step=Decimal("0.1"),
        c2_min=Decimal("0.1"),
        c2_max=Decimal("24"),
        c2_step=Decimal("0.1"),
        avg_diff_min=Decimal("1"),
    )
    records = list(enumerate_cases(spec, _default_options))
    # min1=1,min2=1 → avg diff 0 < 1 → skipped; min1=2,min2=1 → avg diff 1 ≥ 1 → included
    assert all(r.raw_fields["min1"] != "1" for r in records)
    assert any(r.raw_fields["min1"] == "2" for r in records)
