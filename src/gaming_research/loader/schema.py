from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

KERNEL_FIELDS: tuple[str, ...] = (
    "min1", "max1", "min2", "max2", "a1", "a2", "c1", "c2", "p"
)
ID_COLUMN: str = "case_id"
AUTO_ID_FORMAT: str = "row_{:05d}"


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    params: object
    raw_fields: Mapping[str, str]
    metadata: Mapping[str, str]


@dataclass(frozen=True)
class LoaderError:
    case_id: str
    reason_code: str
    reason_detail: str
    raw_fields: Mapping[str, str]
    metadata: Mapping[str, str]
