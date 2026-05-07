from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _tiny_spec_dict() -> dict:
    return {
        "schema_version": 1,
        "min1_values": ["2"],
        "min2_values": ["1"],
        "span1": "15",
        "span2": "15",
        "a1": "0.5",
        "a2": "0.5",
        "p_values": ["0.5"],
        "c1_min": "0.1",
        "c1_max": "24",
        "c1_step": "0.1",
        "c2_min": "0.1",
        "c2_max": "24",
        "c2_step": "0.1",
        "avg_diff_min": "1",
    }


def _run_cli(*extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "gaming_research.exhaustion", *extra_args],
        capture_output=True,
        text=True,
    )


def test_spec_file_happy_path(tmp_path: Path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(_tiny_spec_dict()), encoding="utf-8")
    out_path = tmp_path / "out.csv"

    result = _run_cli("-o", str(out_path), "--spec-file", str(spec_path))
    assert result.returncode == 0, result.stderr

    meta = json.loads((tmp_path / "out.metadata.json").read_text(encoding="utf-8"))
    assert meta["spec_source"] == str(spec_path)
    assert meta["ran_case_count"] == 16
    assert meta["reduction_path"] == "analytical_reduction"
    expected_spec = {k: v for k, v in _tiny_spec_dict().items() if k != "schema_version"}
    assert meta["spec"] == expected_spec


def test_spec_file_missing_path(tmp_path: Path):
    out_path = tmp_path / "out.csv"
    result = _run_cli(
        "-o", str(out_path), "--spec-file", str(tmp_path / "no-such.json"),
    )
    assert result.returncode == 2
    assert "cannot load --spec-file" in result.stderr
    assert not out_path.exists()


def test_spec_file_invalid_field_value(tmp_path: Path):
    bad = _tiny_spec_dict()
    bad["c1_min"] = "30"  # > c1_max
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(bad), encoding="utf-8")
    out_path = tmp_path / "out.csv"

    result = _run_cli("-o", str(out_path), "--spec-file", str(spec_path))
    assert result.returncode == 2
    assert "cannot load --spec-file" in result.stderr
    assert "c1_min" in result.stderr


def test_spec_file_numeric_value_rejected(tmp_path: Path):
    bad = _tiny_spec_dict()
    bad["c1_step"] = 0.1  # number instead of string
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(bad), encoding="utf-8")
    out_path = tmp_path / "out.csv"

    result = _run_cli("-o", str(out_path), "--spec-file", str(spec_path))
    assert result.returncode == 2
    assert "must be a string" in result.stderr


def test_spec_file_custom_a1_falls_through_to_full_grid(tmp_path: Path):
    custom = _tiny_spec_dict()
    custom["a1"] = "0.7"
    custom["c1_max"] = "0.5"  # keep grid small
    custom["c2_max"] = "0.5"
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(custom), encoding="utf-8")
    out_path = tmp_path / "out.csv"

    result = _run_cli("-o", str(out_path), "--spec-file", str(spec_path))
    assert result.returncode == 0, result.stderr

    meta = json.loads((tmp_path / "out.metadata.json").read_text(encoding="utf-8"))
    assert meta["reduction_path"] == "full_grid"
