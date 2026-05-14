from __future__ import annotations

from decimal import Decimal

import pytest

from gaming_research.kernel.types import Options
from gaming_research.exhaustion.spec import (
    CURRENT_SPEC, GridSpec, PointsSegment, RangeSegment, materialize_axis,
)
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
        c1=(RangeSegment(min=Decimal("0.1"), max=Decimal("24"), step=Decimal("0.1")),),
        c2=(RangeSegment(min=Decimal("0.1"), max=Decimal("24"), step=Decimal("0.1")),),
        avg_diff_min=Decimal("1"),
    )
    records = list(enumerate_cases(spec, _default_options))
    assert all(r.raw_fields["min1"] != "1" for r in records)
    assert any(r.raw_fields["min1"] == "2" for r in records)


def _single_pair_spec(c1_segs, c2_segs, p="0.3") -> GridSpec:
    return GridSpec(
        min1_values=(Decimal("2"),),
        min2_values=(Decimal("1"),),
        span1=Decimal("15"),
        span2=Decimal("15"),
        a1=Decimal("0.5"),
        a2=Decimal("0.5"),
        p_values=(Decimal(p),),
        c1=c1_segs,
        c2=c2_segs,
        avg_diff_min=Decimal("1"),
    )


def test_points_segment_enumerates_specified_values():
    # Full-grid mode (war payoff off) so all points enumerate without window filter.
    opts = Options(enforce_war_payoff_s1=False, enforce_war_payoff_s2=False)
    spec = _single_pair_spec(
        (PointsSegment(values=(Decimal("0.3"), Decimal("0.7"), Decimal("1.1"))),),
        (PointsSegment(values=(Decimal("0.4"), Decimal("0.9"))),),
    )
    records = list(enumerate_cases(spec, opts))
    pairs = {(r.raw_fields["c1"], r.raw_fields["c2"]) for r in records}
    assert pairs == {
        ("0.3", "0.4"), ("0.3", "0.9"),
        ("0.7", "0.4"), ("0.7", "0.9"),
        ("1.1", "0.4"), ("1.1", "0.9"),
    }


def test_multi_segment_axis_dedupes_and_sorts():
    # c1 has overlapping range + points; materialized axis must be deduped + sorted.
    segs = (
        RangeSegment(min=Decimal("0.30"), max=Decimal("0.32"), step=Decimal("0.01")),
        PointsSegment(values=(Decimal("0.31"), Decimal("0.50"), Decimal("0.10"))),
    )
    axis = materialize_axis(segs)
    assert axis == (
        Decimal("0.10"), Decimal("0.30"), Decimal("0.31"),
        Decimal("0.32"), Decimal("0.50"),
    )


def test_reduction_window_strictly_open_at_lo():
    # For p=0.3, max1=17: c1_lo = 5.1 exactly. Spec has c1 point 5.1 — must be excluded.
    spec = _single_pair_spec(
        (PointsSegment(values=(Decimal("5.1"), Decimal("5.2"))),),
        (PointsSegment(values=(Decimal("11.3"),)),),
    )
    records = list(enumerate_cases(spec, _default_options))
    c1_values = {r.raw_fields["c1"] for r in records}
    assert "5.1" not in c1_values
    assert "5.2" in c1_values


def test_reduction_window_filters_out_of_range_points():
    # For p=0.3, c1 window is (5.1, 5.6). c1 segment mixes inside and outside points.
    spec = _single_pair_spec(
        (PointsSegment(values=(
            Decimal("4.9"), Decimal("5.0"), Decimal("5.2"),
            Decimal("5.5"), Decimal("5.6"), Decimal("6.0"),
        )),),
        (PointsSegment(values=(Decimal("11.3"),)),),
    )
    records = list(enumerate_cases(spec, _default_options))
    c1_values = {r.raw_fields["c1"] for r in records}
    assert c1_values == {"5.2", "5.5"}
