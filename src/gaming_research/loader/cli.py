from __future__ import annotations

import argparse
import sys

from gaming_research.kernel.types import Options
from gaming_research.loader.reader import read_cases
from gaming_research.loader.runner import run
from gaming_research.loader.writer import flatten, write_rows


def _bool_arg(s: str) -> bool:
    if s == "true":
        return True
    if s == "false":
        return False
    raise argparse.ArgumentTypeError(f"expected 'true' or 'false', got {s!r}")


def _infer_metadata_columns(records: list) -> tuple[str, ...]:
    from gaming_research.loader.schema import CaseRecord
    for r in records:
        if isinstance(r, CaseRecord):
            return tuple(r.metadata.keys())
    return ()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m gaming_research.loader")
    parser.add_argument("input", metavar="INPUT")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--bluffing-mode", choices=["compat", "research"], default="research")
    parser.add_argument("--enforce-war-payoff-s1", type=_bool_arg, default=True, metavar="{true,false}")
    parser.add_argument("--enforce-war-payoff-s2", type=_bool_arg, default=True, metavar="{true,false}")
    args = parser.parse_args()

    try:
        records = list(read_cases(args.input))
    except OSError as exc:
        print(f"loader: cannot read input: {exc}", file=sys.stderr)
        sys.exit(2)

    metadata_columns = _infer_metadata_columns(records)

    options = Options(
        bluffing_solver_mode=args.bluffing_mode,
        enforce_war_payoff_s1=args.enforce_war_payoff_s1,
        enforce_war_payoff_s2=args.enforce_war_payoff_s2,
    )

    pairs = [run(r, options) for r in records]
    all_rows = [row for record, result in pairs for row in flatten(record, result)]

    try:
        write_rows(args.output, all_rows, metadata_columns)
    except OSError as exc:
        print(f"loader: cannot write output: {exc}", file=sys.stderr)
        sys.exit(2)

    from gaming_research.loader.schema import LoaderError
    from gaming_research.kernel.types import KernelResult

    n_rows = sum(1 for r in records if not (isinstance(r, LoaderError) and r.reason_code == "missing_required_column" and r.case_id == "row_00000"))
    n_loader_rejected = sum(1 for r in records if isinstance(r, LoaderError) and not (r.reason_code == "missing_required_column" and r.case_id == "row_00000"))
    n_validation_failed = 0
    n_solved = 0
    n_total_solutions = 0
    for record, result in pairs:
        if isinstance(record, LoaderError):
            continue
        if result is None:
            continue
        if result.summary.status == "validation_failed":
            n_validation_failed += 1
        elif result.summary.status == "solver_has_valid_solution":
            n_solved += 1
            n_total_solutions += len(result.solutions)

    # rows read = actual data rows (not header-level errors)
    n_rows = n_loader_rejected + n_validation_failed + n_solved + sum(
        1 for record, result in pairs
        if not isinstance(record, LoaderError) and result is not None
        and result.summary.status == "solver_no_valid_solution"
    )

    print(
        f"loader: {n_rows} rows read, {n_loader_rejected} rejected at loader, "
        f"{n_validation_failed} failed validation, {n_solved} solved, "
        f"{n_total_solutions} total solution rows",
        file=sys.stderr,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
