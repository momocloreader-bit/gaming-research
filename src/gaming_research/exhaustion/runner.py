from __future__ import annotations

from collections.abc import Iterator

from gaming_research.kernel.types import KernelResult, Options
from gaming_research.loader.runner import run as loader_run
from gaming_research.loader.schema import CaseRecord, LoaderError
from gaming_research.exhaustion.spec import GridSpec
from gaming_research.exhaustion.enumerate import enumerate_cases


def run_all(
    spec: GridSpec,
    options: Options,
) -> Iterator[tuple[CaseRecord | LoaderError, KernelResult | None]]:
    for record in enumerate_cases(spec, options):
        yield loader_run(record, options)
