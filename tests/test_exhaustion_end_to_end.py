from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from gaming_research.kernel.types import Options
from gaming_research.exhaustion.runner import run_all
from gaming_research.exhaustion.writer import write_cases, write_metadata
from gaming_research.exhaustion.spec import estimate_case_count, reduction_eligible

FIXTURES = Path(__file__).parent / "fixtures" / "exhaustion"


def _load_tiny_spec():
    from tests.fixtures.exhaustion.tiny_spec import TINY_SPEC
    return TINY_SPEC


def _build_meta(spec, options, pairs, output_row_count):
    from datetime import datetime, timezone
    import importlib.metadata
    from gaming_research.exhaustion.cli import _spec_to_dict, _options_to_dict
    now = datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "package_version": importlib.metadata.version("gaming-research"),
        "started_at": now.isoformat(),
        "finished_at": now.isoformat(),
        "elapsed_seconds": 0.0,
        "spec": _spec_to_dict(spec),
        "options": _options_to_dict(options),
        "estimated_case_count": estimate_case_count(spec, options),
        "ran_case_count": len(pairs),
        "output_row_count": output_row_count,
        "reduction_path": "analytical_reduction" if reduction_eligible(spec, options) else "full_grid",
        "allow_large_grid_used": False,
        "truncated": False,
        "truncation_reason": None,
    }


_TIMING_KEYS = {"started_at", "finished_at", "elapsed_seconds"}


def test_cases_csv_matches_golden():
    spec = _load_tiny_spec()
    options = Options()
    pairs = list(run_all(spec, options))

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        cases_path = f.name
    try:
        write_cases(pairs, cases_path)
        golden = (FIXTURES / "expected_cases.csv").read_bytes()
        actual = Path(cases_path).read_bytes()
        assert actual == golden, (
            "cases.csv does not match golden.\n"
            f"expected {len(golden)} bytes, got {len(actual)} bytes"
        )
    finally:
        os.unlink(cases_path)


def test_metadata_json_matches_golden():
    spec = _load_tiny_spec()
    options = Options()
    pairs = list(run_all(spec, options))

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        cases_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        meta_path = f.name
    try:
        output_row_count = write_cases(pairs, cases_path)
        meta = _build_meta(spec, options, pairs, output_row_count)
        write_metadata(meta, meta_path)

        golden = json.loads((FIXTURES / "expected_metadata.json").read_text(encoding="utf-8"))
        actual = json.loads(Path(meta_path).read_text(encoding="utf-8"))

        for key in set(golden) | set(actual):
            if key in _TIMING_KEYS:
                continue
            assert actual.get(key) == golden.get(key), (
                f"metadata key {key!r} mismatch: {actual.get(key)!r} != {golden.get(key)!r}"
            )
    finally:
        os.unlink(cases_path)
        os.unlink(meta_path)
