from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

from gaming_research.kernel.types import Options, Params
from gaming_research.loader.schema import CaseRecord
from gaming_research.exhaustion.spec import (
    GridSpec, materialize_axis, reduction_eligible,
)


def enumerate_cases(spec: GridSpec, options: Options) -> Iterator[CaseRecord]:
    c1_axis = materialize_axis(spec.c1)
    c2_axis = materialize_axis(spec.c2)
    use_reduction = reduction_eligible(spec, options)

    for min1 in spec.min1_values:
        max1 = min1 + spec.span1
        for min2 in spec.min2_values:
            max2 = min2 + spec.span2
            avg1 = min1 + spec.span1 / 2
            avg2 = min2 + spec.span2 / 2
            if avg1 - avg2 < spec.avg_diff_min:
                continue
            for p in spec.p_values:
                if use_reduction:
                    yield from _reduction_cases(
                        spec, min1, max1, min2, max2, p, c1_axis, c2_axis,
                    )
                else:
                    yield from _full_grid_cases(
                        spec, min1, max1, min2, max2, p, c1_axis, c2_axis,
                    )


def _reduction_cases(
    spec: GridSpec,
    min1: Decimal, max1: Decimal,
    min2: Decimal, max2: Decimal,
    p: Decimal,
    c1_axis: tuple[Decimal, ...],
    c2_axis: tuple[Decimal, ...],
) -> Iterator[CaseRecord]:
    c1_lo = p * max1
    c1_hi = c1_lo + spec.a1
    c2_lo = (1 - p) * max2
    c2_hi = c2_lo + spec.a2
    for c1 in c1_axis:
        if not (c1_lo < c1 < c1_hi):
            continue
        for c2 in c2_axis:
            if not (c2_lo < c2 < c2_hi):
                continue
            yield _make_record(min1, max1, min2, max2, p, c1, c2, spec)


def _full_grid_cases(
    spec: GridSpec,
    min1: Decimal, max1: Decimal,
    min2: Decimal, max2: Decimal,
    p: Decimal,
    c1_axis: tuple[Decimal, ...],
    c2_axis: tuple[Decimal, ...],
) -> Iterator[CaseRecord]:
    for c1 in c1_axis:
        for c2 in c2_axis:
            yield _make_record(min1, max1, min2, max2, p, c1, c2, spec)


def _make_record(
    min1: Decimal, max1: Decimal,
    min2: Decimal, max2: Decimal,
    p: Decimal, c1: Decimal, c2: Decimal,
    spec: GridSpec,
) -> CaseRecord:
    raw: dict[str, str] = {
        "min1": str(min1), "max1": str(max1),
        "min2": str(min2), "max2": str(max2),
        "a1":   str(spec.a1), "a2": str(spec.a2),
        "c1":   str(c1), "c2": str(c2),
        "p":    str(p),
    }
    params = Params(
        min1=min1, max1=max1, min2=min2, max2=max2,
        a1=spec.a1, a2=spec.a2, c1=c1, c2=c2, p=p,
    )
    case_id = (
        f"m1={raw['min1']}_m2={raw['min2']}"
        f"_p={raw['p']}_c1={raw['c1']}_c2={raw['c2']}"
    )
    return CaseRecord(case_id=case_id, params=params, raw_fields=raw, metadata={})
