from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from gaming_research.kernel.types import Options


@dataclass(frozen=True)
class GridSpec:
    min1_values:  tuple[Decimal, ...]
    min2_values:  tuple[Decimal, ...]
    span1:        Decimal
    span2:        Decimal
    a1:           Decimal
    a2:           Decimal
    p_values:     tuple[Decimal, ...]
    c1_min:       Decimal
    c1_max:       Decimal
    c1_step:      Decimal
    c2_min:       Decimal
    c2_max:       Decimal
    c2_step:      Decimal
    avg_diff_min: Decimal


CURRENT_SPEC = GridSpec(
    min1_values  = tuple(Decimal(i) for i in range(2, 10)),
    min2_values  = tuple(Decimal(i) for i in range(1, 8)),
    span1        = Decimal("15"),
    span2        = Decimal("15"),
    a1           = Decimal("0.5"),
    a2           = Decimal("0.5"),
    p_values     = tuple(Decimal("0.1") * i for i in range(3, 10)),
    c1_min       = Decimal("0.1"),
    c1_max       = Decimal("24"),
    c1_step      = Decimal("0.1"),
    c2_min       = Decimal("0.1"),
    c2_max       = Decimal("24"),
    c2_step      = Decimal("0.1"),
    avg_diff_min = Decimal("1"),
)


def reduction_eligible(spec: GridSpec, options: Options) -> bool:
    return (
        options.enforce_war_payoff_s1
        and options.enforce_war_payoff_s2
        and spec.a1 == Decimal("0.5")
        and spec.a2 == Decimal("0.5")
    )


def _valid_pair_count(spec: GridSpec) -> int:
    count = 0
    for min1 in spec.min1_values:
        for min2 in spec.min2_values:
            avg1 = min1 + spec.span1 / 2
            avg2 = min2 + spec.span2 / 2
            if avg1 - avg2 >= spec.avg_diff_min:
                count += 1
    return count


def estimate_case_count(spec: GridSpec, options: Options) -> int:
    pairs = _valid_pair_count(spec)
    n_p = len(spec.p_values)

    if reduction_eligible(spec, options):
        # count candidates analytically for one representative triple per p
        # (window width is constant across all valid pairs for a given p)
        total = 0
        for min1 in spec.min1_values:
            max1 = min1 + spec.span1
            for min2 in spec.min2_values:
                max2 = min2 + spec.span2
                avg1 = min1 + spec.span1 / 2
                avg2 = min2 + spec.span2 / 2
                if avg1 - avg2 < spec.avg_diff_min:
                    continue
                for p in spec.p_values:
                    c1_lo = p * max1
                    c1_hi = c1_lo + spec.a1
                    c1_count = 0
                    c1 = c1_lo + spec.c1_step
                    while c1 < c1_hi:
                        if spec.c1_min <= c1 <= spec.c1_max:
                            c1_count += 1
                        c1 += spec.c1_step

                    c2_lo = (1 - p) * max2
                    c2_hi = c2_lo + spec.a2
                    c2_count = 0
                    c2 = c2_lo + spec.c2_step
                    while c2 < c2_hi:
                        if spec.c2_min <= c2 <= spec.c2_max:
                            c2_count += 1
                        c2 += spec.c2_step

                    total += c1_count * c2_count
        return total
    else:
        n_c1 = math.floor((spec.c1_max - spec.c1_min) / spec.c1_step) + 1
        n_c2 = math.floor((spec.c2_max - spec.c2_min) / spec.c2_step) + 1
        return pairs * n_p * int(n_c1) * int(n_c2)
