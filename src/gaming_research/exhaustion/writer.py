from __future__ import annotations

import json
import os
from typing import Iterable

from gaming_research.kernel.types import KernelResult
from gaming_research.loader.schema import CaseRecord, LoaderError
from gaming_research.loader.writer import flatten, write_rows


def write_cases(
    pairs: Iterable[tuple[CaseRecord | LoaderError, KernelResult | None]],
    cases_path: str | os.PathLike,
) -> int:
    rows = [row for record, result in pairs for row in flatten(record, result)]
    write_rows(cases_path, rows, metadata_columns=())
    return len(rows)


def write_metadata(meta: dict, metadata_path: str | os.PathLike) -> None:
    with open(metadata_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, sort_keys=True, indent=2)
        fh.write("\n")
