from __future__ import annotations

import csv
import os
from typing import Iterable

from gaming_research.kernel.types import KernelResult
from gaming_research.loader.schema import CaseRecord, LoaderError

OUTPUT_COLUMNS: tuple[str, ...] = (
    "case_id",
    # metadata columns injected here by write_rows
    "status",
    "status_detail",
    "scenario",
    "solver_mode",
    "root_index",
    "is_selected",
    "v1_hat",
    "v2_hat",
    "in_support",
    "F1_v1_hat",
    "F2_v2_hat",
    "m_star",
    "v1_star",
    "v2_star",
    "F1_v1_star",
    "F2_v2_star",
    "GT_rhs",
    "GT_condition",
    "loader_error_code",
    "loader_error_detail",
    "min1",
    "max1",
    "min2",
    "max2",
    "a1",
    "a2",
    "c1",
    "c2",
    "p",
)

_SOLUTION_COLS = {
    "v1_hat", "v2_hat", "in_support", "F1_v1_hat", "F2_v2_hat", "m_star",
}

_DERIVED_FLOAT_COLS = ("v1_star", "v2_star", "F1_v1_star", "F2_v2_star", "GT_rhs")


def _fmt_float(v: float) -> str:
    return f"{v:.10g}"


def _fmt_bool(v: bool) -> str:
    return "true" if v else "false"


def flatten(
    record: CaseRecord | LoaderError,
    result: KernelResult | None,
) -> list[dict[str, str]]:
    if isinstance(record, LoaderError):
        row: dict[str, str] = {
            "case_id": record.case_id,
            "status": "loader_rejected",
            "status_detail": record.reason_code,
            "scenario": "",
            "solver_mode": "",
            "root_index": "",
            "is_selected": "",
            "loader_error_code": record.reason_code,
            "loader_error_detail": record.reason_detail,
        }
        for col in _SOLUTION_COLS:
            row[col] = ""
        for col in _DERIVED_FLOAT_COLS:
            row[col] = ""
        row["GT_condition"] = ""
        _fill_kernel_fields(row, record.raw_fields)
        row.update(record.metadata)
        return [row]

    assert result is not None
    status = result.summary.status

    if status == "validation_failed":
        row = {
            "case_id": record.case_id,
            "status": "validation_failed",
            "status_detail": result.summary.status_detail,
            "scenario": "",
            "solver_mode": "",
            "root_index": "",
            "is_selected": "",
            "loader_error_code": "",
            "loader_error_detail": "",
        }
        for col in _SOLUTION_COLS:
            row[col] = ""
        _fill_derived(row, result.derived)
        _fill_kernel_fields(row, record.raw_fields)
        row.update(record.metadata)
        return [row]

    if status == "solver_no_valid_solution":
        row = {
            "case_id": record.case_id,
            "status": "solver_no_valid_solution",
            "status_detail": result.summary.status_detail,
            "scenario": result.branch.scenario,
            "solver_mode": result.branch.solver_mode,
            "root_index": "",
            "is_selected": "",
            "loader_error_code": "",
            "loader_error_detail": "",
        }
        for col in _SOLUTION_COLS:
            row[col] = ""
        _fill_derived(row, result.derived)
        _fill_kernel_fields(row, record.raw_fields)
        row.update(record.metadata)
        return [row]

    # solver_has_valid_solution
    rows = []
    for sol in result.solutions:
        r: dict[str, str] = {
            "case_id": record.case_id,
            "status": "solver_has_valid_solution",
            "status_detail": result.summary.status_detail,
            "scenario": result.branch.scenario,
            "solver_mode": result.branch.solver_mode,
            "root_index": str(sol.root_index),
            "is_selected": _fmt_bool(sol.root_index == result.summary.selected_solution_index),
            "v1_hat": _fmt_float(sol.v1_hat),
            "v2_hat": _fmt_float(sol.v2_hat),
            "in_support": _fmt_bool(sol.in_support),
            "F1_v1_hat": _fmt_float(sol.F1_v1_hat),
            "F2_v2_hat": _fmt_float(sol.F2_v2_hat),
            "m_star": _fmt_float(sol.m_star) if sol.m_star is not None else "",
            "loader_error_code": "",
            "loader_error_detail": "",
        }
        _fill_derived(r, result.derived)
        _fill_kernel_fields(r, record.raw_fields)
        r.update(record.metadata)
        rows.append(r)
    return rows


def _fill_derived(row: dict[str, str], derived: object) -> None:
    if derived is None:
        for col in _DERIVED_FLOAT_COLS:
            row[col] = ""
        row["GT_condition"] = ""
    else:
        for col in _DERIVED_FLOAT_COLS:
            row[col] = _fmt_float(getattr(derived, col))
        row["GT_condition"] = _fmt_bool(derived.GT_condition)


def _fill_kernel_fields(row: dict[str, str], raw_fields: object) -> None:
    from gaming_research.loader.schema import KERNEL_FIELDS
    for field in KERNEL_FIELDS:
        row[field] = raw_fields.get(field, "")


def write_rows(
    path: str | os.PathLike,
    rows: Iterable[dict[str, str]],
    metadata_columns: tuple[str, ...],
) -> None:
    full_columns = (
        ("case_id",)
        + metadata_columns
        + OUTPUT_COLUMNS[1:]
    )
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(full_columns)
        for row in rows:
            writer.writerow([row.get(col, "") for col in full_columns])
