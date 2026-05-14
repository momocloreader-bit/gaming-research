from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Union

from gaming_research.kernel.types import Options


_V1_AXIS_FIELDS = ("c1_min", "c1_max", "c1_step", "c2_min", "c2_max", "c2_step")
_V2_AXIS_FIELDS = ("c1", "c2")

_SCALAR_FIELDS = ("span1", "span2", "a1", "a2", "avg_diff_min")
_TUPLE_FIELDS = ("min1_values", "min2_values", "p_values")
_ALL_FIELDS = frozenset(_SCALAR_FIELDS + _TUPLE_FIELDS + _V2_AXIS_FIELDS)


@dataclass(frozen=True)
class RangeSegment:
    min: Decimal
    max: Decimal
    step: Decimal


@dataclass(frozen=True)
class PointsSegment:
    values: tuple[Decimal, ...]


AxisSegment = Union[RangeSegment, PointsSegment]


@dataclass(frozen=True)
class GridSpec:
    min1_values:  tuple[Decimal, ...]
    min2_values:  tuple[Decimal, ...]
    span1:        Decimal
    span2:        Decimal
    a1:           Decimal
    a2:           Decimal
    p_values:     tuple[Decimal, ...]
    c1:           tuple[AxisSegment, ...]
    c2:           tuple[AxisSegment, ...]
    avg_diff_min: Decimal

    @classmethod
    def from_dict(cls, data: dict) -> "GridSpec":
        spec, _ = cls.from_dict_with_meta(data)
        return spec

    @classmethod
    def from_dict_with_meta(cls, data: dict) -> tuple["GridSpec", bool]:
        if not isinstance(data, dict):
            raise ValueError(
                f"spec must be a JSON object, got {type(data).__name__}"
            )
        payload, did_migrate = _normalize_version(data)

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
        for name in _V2_AXIS_FIELDS:
            kwargs[name] = _parse_axis(name, payload[name])

        spec = cls(**kwargs)
        _validate_spec(spec)
        return spec, did_migrate


def _normalize_version(data: dict) -> tuple[dict, bool]:
    has_sv = "schema_version" in data
    sv = data.get("schema_version")
    has_v1 = any(f in data for f in _V1_AXIS_FIELDS)
    has_v2 = any(f in data for f in _V2_AXIS_FIELDS)
    payload = {k: v for k, v in data.items() if k != "schema_version"}

    if has_sv and sv not in (1, 2):
        raise ValueError(
            f"unsupported schema_version: {sv!r} (expected 1 or 2)"
        )
    if has_sv and sv == 2:
        legacy = sorted(f for f in _V1_AXIS_FIELDS if f in data)
        if legacy:
            raise ValueError(
                f"schema_version=2 spec must not contain legacy field: "
                f"{legacy[0]}"
            )
        return payload, False
    if has_sv and sv == 1:
        v2_present = sorted(f for f in _V2_AXIS_FIELDS if f in data)
        if v2_present:
            raise ValueError(
                f"schema_version=1 spec must not contain v2 field: "
                f"{v2_present[0]}"
            )
        return _migrate_v1_to_v2(payload), True

    if has_v1 and has_v2:
        v1_field = sorted(f for f in _V1_AXIS_FIELDS if f in data)[0]
        v2_field = sorted(f for f in _V2_AXIS_FIELDS if f in data)[0]
        raise ValueError(
            f"spec mixes v1 fields ({v1_field}) and v2 fields ({v2_field}); "
            f"set schema_version explicitly"
        )
    if has_v1:
        return _migrate_v1_to_v2(payload), True
    return payload, False


def _migrate_v1_to_v2(payload: dict) -> dict:
    out = {k: v for k, v in payload.items() if k not in _V1_AXIS_FIELDS}
    if any(f in payload for f in ("c1_min", "c1_max", "c1_step")):
        out["c1"] = [{
            "type": "range",
            "min":  payload.get("c1_min"),
            "max":  payload.get("c1_max"),
            "step": payload.get("c1_step"),
        }]
    if any(f in payload for f in ("c2_min", "c2_max", "c2_step")):
        out["c2"] = [{
            "type": "range",
            "min":  payload.get("c2_min"),
            "max":  payload.get("c2_max"),
            "step": payload.get("c2_step"),
        }]
    return out


def _parse_axis(name: str, value: object) -> tuple[AxisSegment, ...]:
    if not isinstance(value, list):
        raise ValueError(
            f"field {name} must be a list, got {type(value).__name__}"
        )
    if len(value) == 0:
        raise ValueError(f"{name} must contain at least one segment")
    parsed: list[AxisSegment] = []
    for i, item in enumerate(value):
        parsed.append(_parse_segment(f"{name}[{i}]", item))
    return tuple(parsed)


def _parse_segment(path: str, item: object) -> AxisSegment:
    if not isinstance(item, dict):
        raise ValueError(
            f"field {path} must be an object, got {type(item).__name__}"
        )
    t = item.get("type")
    if t == "range":
        for k in ("min", "max", "step"):
            if k not in item:
                raise ValueError(f"{path}.{k} is missing")
            if not isinstance(item[k], str):
                raise ValueError(
                    f"{path}.{k} must be a string, "
                    f"got {type(item[k]).__name__}"
                )
        extra = set(item) - {"type", "min", "max", "step"}
        if extra:
            raise ValueError(
                f"{path} has unknown field: {sorted(extra)[0]}"
            )
        lo = Decimal(item["min"])
        hi = Decimal(item["max"])
        step = Decimal(item["step"])
        if step <= 0:
            raise ValueError(f"{path}.step ({step}) must be > 0")
        if lo > hi:
            raise ValueError(f"{path}.min ({lo}) must be <= max ({hi})")
        return RangeSegment(min=lo, max=hi, step=step)
    if t == "points":
        if "values" not in item:
            raise ValueError(f"{path}.values is missing")
        v = item["values"]
        if not isinstance(v, list):
            raise ValueError(
                f"{path}.values must be a list, got {type(v).__name__}"
            )
        if len(v) == 0:
            raise ValueError(f"{path}.values must be a non-empty list")
        extra = set(item) - {"type", "values"}
        if extra:
            raise ValueError(
                f"{path} has unknown field: {sorted(extra)[0]}"
            )
        parsed: list[Decimal] = []
        for j, vv in enumerate(v):
            if not isinstance(vv, str):
                raise ValueError(
                    f"{path}.values[{j}] must be a string, "
                    f"got {type(vv).__name__}"
                )
            parsed.append(Decimal(vv))
        return PointsSegment(values=tuple(parsed))
    raise ValueError(
        f"{path}.type must be 'range' or 'points', got {t!r}"
    )


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
    if spec.a1 < 0:
        raise ValueError(f"a1 ({spec.a1}) must be >= 0")
    if spec.a2 < 0:
        raise ValueError(f"a2 ({spec.a2}) must be >= 0")
    if spec.avg_diff_min < 0:
        raise ValueError(f"avg_diff_min ({spec.avg_diff_min}) must be >= 0")


def materialize_axis(segments: tuple[AxisSegment, ...]) -> tuple[Decimal, ...]:
    seen: set[Decimal] = set()
    for seg in segments:
        if isinstance(seg, RangeSegment):
            v = seg.min
            while v <= seg.max:
                seen.add(v)
                v += seg.step
        else:
            for p in seg.values:
                seen.add(p)
    return tuple(sorted(seen))


CURRENT_SPEC = GridSpec(
    min1_values  = tuple(Decimal(i) for i in range(2, 10)),
    min2_values  = tuple(Decimal(i) for i in range(1, 8)),
    span1        = Decimal("15"),
    span2        = Decimal("15"),
    a1           = Decimal("0.5"),
    a2           = Decimal("0.5"),
    p_values     = tuple(Decimal("0.1") * i for i in range(3, 10)),
    c1           = (RangeSegment(
        min=Decimal("0.1"), max=Decimal("24"), step=Decimal("0.1"),
    ),),
    c2           = (RangeSegment(
        min=Decimal("0.1"), max=Decimal("24"), step=Decimal("0.1"),
    ),),
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
    c1_axis = materialize_axis(spec.c1)
    c2_axis = materialize_axis(spec.c2)
    n_p = len(spec.p_values)

    if reduction_eligible(spec, options):
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
                    c1_count = sum(1 for c in c1_axis if c1_lo < c < c1_hi)
                    c2_lo = (1 - p) * max2
                    c2_hi = c2_lo + spec.a2
                    c2_count = sum(1 for c in c2_axis if c2_lo < c < c2_hi)
                    total += c1_count * c2_count
        return total

    pairs = _valid_pair_count(spec)
    return pairs * n_p * len(c1_axis) * len(c2_axis)
