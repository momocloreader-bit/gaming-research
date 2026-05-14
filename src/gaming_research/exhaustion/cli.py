from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal

from gaming_research.kernel.types import Options
from gaming_research.exhaustion.spec import (
    CURRENT_SPEC, GridSpec, PointsSegment, RangeSegment,
    estimate_case_count, reduction_eligible,
)
from gaming_research.exhaustion.runner import run_all
from gaming_research.exhaustion.writer import write_cases, write_metadata


def _bool_arg(s: str) -> bool:
    if s == "true":
        return True
    if s == "false":
        return False
    raise argparse.ArgumentTypeError(f"expected 'true' or 'false', got {s!r}")


def _segment_to_dict(seg) -> dict:
    if isinstance(seg, RangeSegment):
        return {
            "type": "range",
            "min":  str(seg.min),
            "max":  str(seg.max),
            "step": str(seg.step),
        }
    if isinstance(seg, PointsSegment):
        return {
            "type":   "points",
            "values": [str(v) for v in seg.values],
        }
    raise TypeError(f"unknown segment type: {type(seg).__name__}")


def _spec_to_dict(spec: GridSpec) -> dict:
    return {
        "schema_version": 2,
        "min1_values":    [str(v) for v in spec.min1_values],
        "min2_values":    [str(v) for v in spec.min2_values],
        "span1":          str(spec.span1),
        "span2":          str(spec.span2),
        "a1":             str(spec.a1),
        "a2":             str(spec.a2),
        "p_values":       [str(v) for v in spec.p_values],
        "c1":             [_segment_to_dict(s) for s in spec.c1],
        "c2":             [_segment_to_dict(s) for s in spec.c2],
        "avg_diff_min":   str(spec.avg_diff_min),
    }


def _options_to_dict(options: Options) -> dict:
    return {
        "bluffing_solver_mode":  options.bluffing_solver_mode,
        "enforce_war_payoff_s1": options.enforce_war_payoff_s1,
        "enforce_war_payoff_s2": options.enforce_war_payoff_s2,
        "bluffing_sample_count": options.bluffing_sample_count,
        "denom_eps":             options.denom_eps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m gaming_research.exhaustion")
    parser.add_argument("-o", "--output", required=True, metavar="OUTPUT")
    parser.add_argument("--bluffing-mode", choices=["compat", "research"], default="research")
    parser.add_argument(
        "--enforce-war-payoff-s1", type=_bool_arg, default=True, metavar="{true,false}",
    )
    parser.add_argument(
        "--enforce-war-payoff-s2", type=_bool_arg, default=True, metavar="{true,false}",
    )
    parser.add_argument("--allow-large-grid", action="store_true", default=False)
    parser.add_argument("--spec-file", default=None, metavar="PATH")
    args = parser.parse_args()

    output_path: str = args.output
    if not output_path.endswith(".csv"):
        print("exhaustion: -o path must end with .csv", file=sys.stderr)
        sys.exit(2)
    metadata_path = output_path[:-4] + ".metadata.json"

    if args.spec_file:
        try:
            with open(args.spec_file, encoding="utf-8") as fh:
                spec, did_migrate = GridSpec.from_dict_with_meta(json.load(fh))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"exhaustion: cannot load --spec-file: {exc}", file=sys.stderr)
            sys.exit(2)
        spec_source: str = args.spec_file
        if did_migrate:
            print(
                "note: detected schema_version=1 spec, "
                "auto-migrated to v2 in-memory",
                file=sys.stderr,
            )
    else:
        spec = CURRENT_SPEC
        spec_source = "CURRENT_SPEC"

    options = Options(
        bluffing_solver_mode=args.bluffing_mode,
        enforce_war_payoff_s1=args.enforce_war_payoff_s1,
        enforce_war_payoff_s2=args.enforce_war_payoff_s2,
    )

    estimated = estimate_case_count(spec, options)
    if estimated > 100_000 and not args.allow_large_grid:
        print(
            f"exhaustion: estimated {estimated:,} cases exceeds the 100,000 "
            f"threshold. Pass --allow-large-grid to proceed.",
            file=sys.stderr,
        )
        sys.exit(2)

    started_at = datetime.now(timezone.utc)
    pairs = list(run_all(spec, options))
    finished_at = datetime.now(timezone.utc)

    try:
        output_row_count = write_cases(pairs, output_path)
    except OSError as exc:
        print(f"exhaustion: cannot write output: {exc}", file=sys.stderr)
        sys.exit(2)

    reduction_path = (
        "analytical_reduction" if reduction_eligible(spec, options) else "full_grid"
    )
    meta = {
        "schema_version": 1,
        "package_version": importlib.metadata.version("gaming-research"),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "elapsed_seconds": (finished_at - started_at).total_seconds(),
        "spec": _spec_to_dict(spec),
        "spec_source": spec_source,
        "options": _options_to_dict(options),
        "estimated_case_count": estimated,
        "ran_case_count": len(pairs),
        "output_row_count": output_row_count,
        "reduction_path": reduction_path,
        "allow_large_grid_used": args.allow_large_grid,
        "truncated": False,
        "truncation_reason": None,
    }

    try:
        write_metadata(meta, metadata_path)
    except OSError as exc:
        print(f"exhaustion: cannot write metadata: {exc}", file=sys.stderr)
        sys.exit(2)

    print(
        f"exhaustion: {len(pairs)} cases, {output_row_count} output rows, "
        f"{(finished_at - started_at).total_seconds():.1f}s [{reduction_path}]",
        file=sys.stderr,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
