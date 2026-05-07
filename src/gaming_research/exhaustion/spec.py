from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from gaming_research.kernel.types import Options


_SCALAR_FIELDS = (
    "span1", "span2", "a1", "a2",
    "c1_min", "c1_max", "c1_step",
    "c2_min", "c2_max", "c2_step",
    "avg_diff_min",
)
_TUPLE_FIELDS = ("min1_values", "min2_values", "p_values")
_ALL_FIELDS = frozenset(_SCALAR_FIELDS + _TUPLE_FIELDS)


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

    @classmethod
    def from_dict(cls, data: dict) -> "GridSpec":
        if not isinstance(data, dict):
            raise ValueError(f"spec must be a JSON object, got {type(data).__name__}")
        if "schema_version" in data:
            sv = data["schema_version"]
            if sv != 1:
                raise ValueError(f"unsupported schema_version: {sv!r} (expected 1)")
        payload = {k: v for k, v in data.items() if k != "schema_version"}

        unknown = set(payload) - _ALL_FIELDS
        if unknown:
            raise ValueError(f"unknown spec field: {sorted(unknown)[0]}")
        missing = _ALL_FIELDS - set(payload)
        if missing:
            raise ValueError(f"missing spec field: {sorted(missing)[0]}")

        kwargs: dict = {}
        for name in _SCALAR_FIELDS:
            v = payload[name]
            if not isinstance(v, str):
                raise ValueError(
                    f"field {name} must be a string, got {type(v).__name__}"
                )
            kwargs[name] = Decimal(v)
        for name in _TUPLE_FIELDS:
            v = payload[name]
            if not isinstance(v, list):
                raise ValueError(
                    f"field {name} must be a list, got {type(v).__name__}"
                )
            parsed: list[Decimal] = []
            for i, item in enumerate(v):
                if not isinstance(item, str):
                    raise ValueError(
                        f"field {name}[{i}] must be a string, "
                        f"got {type(item).__name__}"
                    )
                parsed.append(Decimal(item))
            kwargs[name] = tuple(parsed)

        spec = cls(**kwargs)
        _validate_spec(spec)
        return spec


def _validate_spec(spec: "GridSpec") -> None:
    if len(spec.min1_values) < 1:
        raise ValueError("min1_values must contain at least one value")
    if len(spec.min2_values) < 1:
        raise ValueError("min2_values must contain at least one value")
    if len(spec.p_values) < 1:
        raise ValueError("p_values must contain at least one value")
    if spec.span1 <= 0:
        raise ValueError(f"span1 ({spec.span1}) must be > 0")
    if spec.span2 <= 0:
        raise ValueError(f"span2 ({spec.span2}) must be > 0")
    if spec.c1_step <= 0:
        raise ValueError(f"c1_step ({spec.c1_step}) must be > 0")
    if spec.c2_step <= 0:
        raise ValueError(f"c2_step ({spec.c2_step}) must be > 0")
    if spec.c1_min > spec.c1_max:
        raise ValueError(
            f"c1_min ({spec.c1_min}) must be <= c1_max ({spec.c1_max})"
        )
    if spec.c2_min > spec.c2_max:
        raise ValueError(
            f"c2_min ({spec.c2_min}) must be <= c2_max ({spec.c2_max})"
        )
    if spec.a1 < 0:
        raise ValueError(f"a1 ({spec.a1}) must be >= 0")
    if spec.a2 < 0:
        raise ValueError(f"a2 ({spec.a2}) must be >= 0")
    if spec.avg_diff_min < 0:
        raise ValueError(f"avg_diff_min ({spec.avg_diff_min}) must be >= 0")


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
