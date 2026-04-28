from __future__ import annotations

import subprocess
from pathlib import Path


def test_end_to_end(tmp_path):
    input_csv = Path("tests/fixtures/loader/input.csv")
    expected = Path("tests/fixtures/loader/expected_output.csv")
    output = tmp_path / "out.csv"
    result = subprocess.run(
        ["python", "-m", "gaming_research.loader", str(input_csv), "-o", str(output)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert output.read_text(encoding="utf-8") == expected.read_text(encoding="utf-8")
