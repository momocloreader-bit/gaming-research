from __future__ import annotations

import csv
import os
from decimal import Decimal, InvalidOperation
from typing import Iterator

from gaming_research.kernel.types import Params
from gaming_research.loader.schema import (
    AUTO_ID_FORMAT,
    ID_COLUMN,
    KERNEL_FIELDS,
    CaseRecord,
    LoaderError,
)


def read_cases(path: str | os.PathLike) -> Iterator[CaseRecord | LoaderError]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []

        missing = [f for f in KERNEL_FIELDS if f not in header]
        for col in missing:
            yield LoaderError(
                case_id=AUTO_ID_FORMAT.format(0),
                reason_code="missing_required_column",
                reason_detail=col,
                raw_fields={},
                metadata={},
            )

        for n, row in enumerate(reader, start=1):
            auto_id = AUTO_ID_FORMAT.format(n)

            if ID_COLUMN not in header:
                case_id = auto_id
            else:
                cell = row.get(ID_COLUMN, "").strip()
                if not cell:
                    yield LoaderError(
                        case_id=auto_id,
                        reason_code="empty_value",
                        reason_detail=ID_COLUMN,
                        raw_fields={},
                        metadata=_extract_metadata(row, header),
                    )
                    continue
                case_id = cell

            metadata = _extract_metadata(row, header)

            raw_fields: dict[str, str] = {}
            decimals: dict[str, Decimal] = {}
            error: LoaderError | None = None

            for field in KERNEL_FIELDS:
                if field not in header:
                    error = LoaderError(
                        case_id=case_id,
                        reason_code="missing_required_column",
                        reason_detail=field,
                        raw_fields=dict(raw_fields),
                        metadata=metadata,
                    )
                    break
                stripped = row[field].strip()
                if not stripped:
                    error = LoaderError(
                        case_id=case_id,
                        reason_code="empty_value",
                        reason_detail=field,
                        raw_fields=dict(raw_fields),
                        metadata=metadata,
                    )
                    break
                try:
                    decimals[field] = Decimal(stripped)
                except InvalidOperation:
                    error = LoaderError(
                        case_id=case_id,
                        reason_code="unparseable_decimal",
                        reason_detail=field,
                        raw_fields=dict(raw_fields),
                        metadata=metadata,
                    )
                    break
                raw_fields[field] = stripped

            if error is not None:
                yield error
                continue

            params = Params(
                min1=decimals["min1"],
                max1=decimals["max1"],
                min2=decimals["min2"],
                max2=decimals["max2"],
                a1=decimals["a1"],
                a2=decimals["a2"],
                c1=decimals["c1"],
                c2=decimals["c2"],
                p=decimals["p"],
            )
            yield CaseRecord(
                case_id=case_id,
                params=params,
                raw_fields=raw_fields,
                metadata=metadata,
            )


def _extract_metadata(row: dict[str, str], header: list[str]) -> dict[str, str]:
    skip = {ID_COLUMN} | set(KERNEL_FIELDS)
    return {col: row[col] for col in header if col not in skip and col in row}
