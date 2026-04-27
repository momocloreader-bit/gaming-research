from __future__ import annotations

from gaming_research.kernel.derived import compute_derived
from gaming_research.kernel.types import Derived, Options, Params, Validation


def validate(params: Params, options: Options) -> tuple[Validation, Derived | None]:
    min1 = float(params.min1)
    max1 = float(params.max1)
    min2 = float(params.min2)
    max2 = float(params.max2)
    a1 = float(params.a1)
    a2 = float(params.a2)
    c1 = float(params.c1)
    c2 = float(params.c2)
    p = float(params.p)

    codes: list[str] = []
    messages: list[str] = []

    def fail(code: str, msg: str) -> None:
        codes.append(code)
        messages.append(msg)

    if not (min1 > 0 and max1 > 0 and min2 > 0 and max2 > 0
            and a1 > 0 and a2 > 0 and c1 > 0 and c2 > 0 and p > 0):
        fail("all_positive", "All parameters must be positive")

    if not (min1 < max1):
        fail("min1_lt_max1", "min1 must be less than max1")

    if not (min2 < max2):
        fail("min2_lt_max2", "min2 must be less than max2")

    if not (0.0 < p < 1.0):
        fail("p_in_open_unit_interval", "p must be in the open interval (0, 1)")

    if not (c1 > a1):
        fail("c1_gt_a1", "c1 must be greater than a1")

    if not (c2 > a2):
        fail("c2_gt_a2", "c2 must be greater than a2")

    # Compute v1_star and v2_star only if structural checks passed
    derived: Derived | None = None
    can_compute_stars = (
        "all_positive" not in codes
        and "min1_lt_max1" not in codes
        and "min2_lt_max2" not in codes
        and "p_in_open_unit_interval" not in codes
        and "c1_gt_a1" not in codes
        and "c2_gt_a2" not in codes
    )

    if can_compute_stars:
        derived = compute_derived(params)
        v1_star = derived.v1_star
        v2_star = derived.v2_star

        if not (min1 < v1_star < max1):
            fail("v1_star_in_support", f"v1_star ({v1_star:.6g}) must be in (min1, max1) = ({min1}, {max1})")

        if not (min2 < v2_star < max2):
            fail("v2_star_in_support", f"v2_star ({v2_star:.6g}) must be in (min2, max2) = ({min2}, {max2})")

        if options.enforce_war_payoff_s1:
            if not (p * max1 - c1 < 0.0):
                fail("s1_war_payoff_negative", f"War payoff for side 1 must be negative: p*max1 - c1 = {p*max1 - c1:.6g}")

        if options.enforce_war_payoff_s2:
            if not ((1.0 - p) * max2 - c2 < 0.0):
                fail("s2_war_payoff_negative", f"War payoff for side 2 must be negative: (1-p)*max2 - c2 = {(1-p)*max2 - c2:.6g}")

    passed = len(codes) == 0
    return Validation(passed=passed, failure_codes=tuple(codes), failure_messages=tuple(messages)), derived
