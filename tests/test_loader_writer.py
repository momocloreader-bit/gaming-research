from __future__ import annotations

import io
import os
import tempfile
from decimal import Decimal

import pytest

from gaming_research.kernel.types import (
    Branch, Derived, KernelResult, Params, Solution, Summary, Validation,
)
from gaming_research.loader.schema import CaseRecord, LoaderError
from gaming_research.loader.writer import OUTPUT_COLUMNS, flatten, write_rows


_PARAMS = Params(
    min1=Decimal("1"), max1=Decimal("10"),
    min2=Decimal("1"), max2=Decimal("10"),
    a1=Decimal("3"), a2=Decimal("4"),
    c1=Decimal("6"), c2=Decimal("5.5"),
    p=Decimal("0.5"),
)
_RAW = {"min1": "1", "max1": "10", "min2": "1", "max2": "10",
        "a1": "3", "a2": "4", "c1": "6", "c2": "5.5", "p": "0.5"}
_DERIVED = Derived(
    v1_star=4.0, v2_star=3.5,
    F1_v1_star=0.5, F2_v2_star=0.4,
    one_minus_F1_v1_star=0.5, one_minus_F2_v2_star=0.6,
    GT_rhs=0.3, GT_condition=True,
)
_VALIDATION_PASS = Validation(passed=True, failure_codes=(), failure_messages=())


def _record(metadata=None):
    return CaseRecord(
        case_id="test", params=_PARAMS,
        raw_fields=_RAW, metadata=metadata or {},
    )


def _error(reason_code="empty_value", reason_detail="p", raw=None, metadata=None):
    return LoaderError(
        case_id="err", reason_code=reason_code, reason_detail=reason_detail,
        raw_fields=raw or {}, metadata=metadata or {},
    )


def test_loader_error_single_row():
    rows = flatten(_error(), None)
    assert len(rows) == 1
    r = rows[0]
    assert r["status"] == "loader_rejected"
    assert r["status_detail"] == "empty_value"
    assert r["loader_error_code"] == "empty_value"
    assert r["loader_error_detail"] == "p"
    assert r["scenario"] == ""
    assert r["v1_hat"] == ""
    assert r["m_star"] == ""


def test_loader_error_kernel_fields_echoed_from_raw():
    raw = {"min1": "1", "max1": "10"}
    rows = flatten(_error(raw=raw), None)
    assert rows[0]["min1"] == "1"
    assert rows[0]["max1"] == "10"
    assert rows[0]["c2"] == ""


def test_validation_failed_single_row():
    result = KernelResult(
        params=_PARAMS,
        derived=None,
        validation=Validation(passed=False, failure_codes=("p_in_open_unit_interval",), failure_messages=("p must be in (0,1)",)),
        branch=None,
        solutions=(),
        summary=Summary(status="validation_failed", status_detail="p_in_open_unit_interval", valid_solution_count=0, selected_solution_index=None),
    )
    rows = flatten(_record(), result)
    assert len(rows) == 1
    r = rows[0]
    assert r["status"] == "validation_failed"
    assert r["status_detail"] == "p_in_open_unit_interval"
    assert r["scenario"] == ""
    assert r["v1_hat"] == ""
    assert r["loader_error_code"] == ""
    assert r["GT_condition"] == ""


def test_solver_no_valid_solution_row():
    result = KernelResult(
        params=_PARAMS,
        derived=_DERIVED,
        validation=_VALIDATION_PASS,
        branch=Branch(scenario="bluffing", solver_mode="research"),
        solutions=(),
        summary=Summary(status="solver_no_valid_solution", status_detail="bluffing_no_valid_root", valid_solution_count=0, selected_solution_index=None),
    )
    rows = flatten(_record(), result)
    assert len(rows) == 1
    r = rows[0]
    assert r["status"] == "solver_no_valid_solution"
    assert r["scenario"] == "bluffing"
    assert r["solver_mode"] == "research"
    assert r["v1_hat"] == ""


def test_solver_has_valid_solution_two_rows():
    sol0 = Solution(source="bluffing", root_kind="numerical", root_index=0, v1_hat=5.0, v2_hat=4.0, in_support=True, F1_v1_hat=0.6, F2_v2_hat=0.5, m_star=None)
    sol1 = Solution(source="bluffing", root_kind="numerical", root_index=1, v1_hat=6.0, v2_hat=5.0, in_support=True, F1_v1_hat=0.7, F2_v2_hat=0.6, m_star=0.123)
    result = KernelResult(
        params=_PARAMS,
        derived=_DERIVED,
        validation=_VALIDATION_PASS,
        branch=Branch(scenario="bluffing", solver_mode="research"),
        solutions=(sol0, sol1),
        summary=Summary(status="solver_has_valid_solution", status_detail="bluffing_multi_valid_root", valid_solution_count=2, selected_solution_index=0),
    )
    rows = flatten(_record(), result)
    assert len(rows) == 2
    r0, r1 = rows
    assert r0["root_index"] == "0"
    assert r0["is_selected"] == "true"
    assert r1["root_index"] == "1"
    assert r1["is_selected"] == "false"
    assert r0["m_star"] == ""
    assert r1["m_star"] == f"{0.123:.10g}"
    assert r0["in_support"] == "true"


def test_float_format():
    sol = Solution(source="GT", root_kind="closed_form", root_index=0, v1_hat=1.23456789012, v2_hat=2.0, in_support=True, F1_v1_hat=0.5, F2_v2_hat=0.4, m_star=None)
    result = KernelResult(
        params=_PARAMS,
        derived=_DERIVED,
        validation=_VALIDATION_PASS,
        branch=Branch(scenario="GT", solver_mode="closed_form"),
        solutions=(sol,),
        summary=Summary(status="solver_has_valid_solution", status_detail="gt_valid_solution", valid_solution_count=1, selected_solution_index=0),
    )
    rows = flatten(_record(), result)
    assert rows[0]["v1_hat"] == f"{1.23456789012:.10g}"


def test_m_star_none_writes_empty():
    sol = Solution(source="GT", root_kind="closed_form", root_index=0, v1_hat=4.0, v2_hat=3.5, in_support=True, F1_v1_hat=0.5, F2_v2_hat=0.4, m_star=None)
    result = KernelResult(
        params=_PARAMS, derived=_DERIVED, validation=_VALIDATION_PASS,
        branch=Branch(scenario="GT", solver_mode="closed_form"),
        solutions=(sol,),
        summary=Summary(status="solver_has_valid_solution", status_detail="gt_valid_solution", valid_solution_count=1, selected_solution_index=0),
    )
    rows = flatten(_record(), result)
    assert rows[0]["m_star"] == ""


def test_column_order_with_metadata():
    sol = Solution(source="GT", root_kind="closed_form", root_index=0, v1_hat=4.0, v2_hat=3.5, in_support=True, F1_v1_hat=0.5, F2_v2_hat=0.4, m_star=None)
    result = KernelResult(
        params=_PARAMS, derived=_DERIVED, validation=_VALIDATION_PASS,
        branch=Branch(scenario="GT", solver_mode="closed_form"),
        solutions=(sol,),
        summary=Summary(status="solver_has_valid_solution", status_detail="gt_valid_solution", valid_solution_count=1, selected_solution_index=0),
    )
    record = CaseRecord(case_id="x", params=_PARAMS, raw_fields=_RAW, metadata={"note": "hi"})
    rows = flatten(record, result)
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        write_rows(path, rows, ("note",))
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    finally:
        os.unlink(path)
    header = lines[0].split(",")
    assert header[0] == "case_id"
    assert header[1] == "note"
    assert header[2] == "status"
    assert header[-1] == "p"


def test_output_lf_line_endings():
    rows = flatten(_error(), None)
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        write_rows(path, rows, ())
        with open(path, "rb") as f:
            raw = f.read()
    finally:
        os.unlink(path)
    assert b"\r\n" not in raw
    assert b"\n" in raw
