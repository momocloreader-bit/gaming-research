from __future__ import annotations

from gaming_research.kernel.api import evaluate_case
from gaming_research.kernel.types import KernelResult, Options
from gaming_research.loader.schema import CaseRecord, LoaderError


def run(
    record: CaseRecord | LoaderError,
    options: Options,
) -> tuple[CaseRecord | LoaderError, KernelResult | None]:
    if isinstance(record, LoaderError):
        return (record, None)
    return (record, evaluate_case(record.params, options))
