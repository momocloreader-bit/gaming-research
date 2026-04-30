from __future__ import annotations

import json
import os
import tempfile
from decimal import Decimal

import pytest

from gaming_research.kernel.types import Options
from gaming_research.exhaustion.spec import GridSpec
from gaming_research.exhaustion.enumerate import enumerate_cases
from gaming_research.exhaustion.runner import run_all
from gaming_research.exhaustion.writer import write_cases, write_metadata


_MINI_SPEC = GridSpec(
    min1_values=(Decimal("2"),),
    min2_values=(Decimal("1"),),
    span1=Decimal("15"),
    span2=Decimal("15"),
    a1=Decimal("0.5"),
    a2=Decimal("0.5"),
    p_values=(Decimal("0.5"),),
    c1_min=Decimal("0.1"),
    c1_max=Decimal("24"),
    c1_step=Decimal("0.1"),
    c2_min=Decimal("0.1"),
    c2_max=Decimal("24"),
    c2_step=Decimal("0.1"),
    avg_diff_min=Decimal("1"),
)

_default_options = Options()


def test_write_cases_row_count():
    pairs = list(run_all(_MINI_SPEC, _default_options))
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = f.name
    try:
        row_count = write_cases(pairs, path)
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        # header + data rows; data rows == row_count
        assert len(lines) == row_count + 1
        assert row_count > 0
    finally:
        os.unlink(path)


def test_metadata_json_keys():
    required_keys = {
        "schema_version", "package_version", "started_at", "finished_at",
        "elapsed_seconds", "spec", "options", "estimated_case_count",
        "ran_case_count", "output_row_count", "reduction_path",
        "allow_large_grid_used", "truncated", "truncation_reason",
    }
    meta = {k: None for k in required_keys}
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        path = f.name
    try:
        write_metadata(meta, path)
        with open(path, encoding="utf-8") as fh:
            parsed = json.load(fh)
        assert required_keys <= set(parsed.keys())
    finally:
        os.unlink(path)


def test_metadata_path_derivation():
    cases_path = "/tmp/cases.csv"
    expected = "/tmp/cases.metadata.json"
    assert cases_path[:-4] + ".metadata.json" == expected
