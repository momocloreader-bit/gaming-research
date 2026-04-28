from __future__ import annotations

import os
import tempfile
from decimal import Decimal

import pytest

from gaming_research.loader.reader import read_cases
from gaming_research.loader.schema import CaseRecord, LoaderError, KERNEL_FIELDS


VALID_HEADER = "case_id,min1,max1,min2,max2,a1,a2,c1,c2,p\n"
VALID_ROW = "c1,1,10,1,10,3,4,6,5.5,0.5\n"


def _write_tmp(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    return path


def _results(content: str) -> list[CaseRecord | LoaderError]:
    path = _write_tmp(content)
    try:
        return list(read_cases(path))
    finally:
        os.unlink(path)


def test_missing_required_column():
    content = "case_id,min1,max1,min2,max2,a1,a2,c1,p\n" + "r1,1,10,1,10,3,4,6,0.5\n"
    results = _results(content)
    errors = [r for r in results if isinstance(r, LoaderError)]
    assert any(e.reason_code == "missing_required_column" and e.reason_detail == "c2" for e in errors)


def test_unparseable_decimal():
    content = VALID_HEADER + "bad,1,10,1,10,3,4,6,5.5,abc\n"
    results = _results(content)
    assert len(results) == 1
    e = results[0]
    assert isinstance(e, LoaderError)
    assert e.reason_code == "unparseable_decimal"
    assert e.reason_detail == "p"


def test_whitespace_only_cell():
    content = VALID_HEADER + "bad,   ,10,1,10,3,4,6,5.5,0.5\n"
    results = _results(content)
    assert len(results) == 1
    e = results[0]
    assert isinstance(e, LoaderError)
    assert e.reason_code == "empty_value"
    assert e.reason_detail == "min1"


def test_auto_id_when_no_case_id_column():
    content = "min1,max1,min2,max2,a1,a2,c1,c2,p\n1,10,1,10,3,4,6,5.5,0.5\n1,10,1,10,3,4,6,5.5,0.5\n"
    results = _results(content)
    ids = [r.case_id for r in results]
    assert ids == ["row_00001", "row_00002"]
    assert all(isinstance(r, CaseRecord) for r in results)


def test_case_id_column_used_when_present():
    content = VALID_HEADER + "my_id,1,10,1,10,3,4,6,5.5,0.5\n"
    results = _results(content)
    assert len(results) == 1
    assert results[0].case_id == "my_id"


def test_empty_case_id_cell_yields_error():
    content = VALID_HEADER + ",1,10,1,10,3,4,6,5.5,0.5\n"
    results = _results(content)
    assert len(results) == 1
    e = results[0]
    assert isinstance(e, LoaderError)
    assert e.reason_code == "empty_value"
    assert e.reason_detail == "case_id"


def test_extra_columns_in_metadata():
    content = "case_id,note,min1,max1,min2,max2,a1,a2,c1,c2,p\nrow1,hello,1,10,1,10,3,4,6,5.5,0.5\n"
    results = _results(content)
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, CaseRecord)
    assert r.metadata == {"note": "hello"}


def test_duplicate_case_ids_both_yield_case_record():
    content = VALID_HEADER + "same,1,10,1,10,3,4,6,5.5,0.5\nsame,1,10,1,10,3,4,6,5.5,0.5\n"
    results = _results(content)
    assert len(results) == 2
    assert all(isinstance(r, CaseRecord) for r in results)


def test_utf8_bom_consumed():
    bom = b"\xef\xbb\xbf"
    content = bom + (VALID_HEADER + VALID_ROW).encode("utf-8")
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.write(fd, content)
    os.close(fd)
    try:
        results = list(read_cases(path))
    finally:
        os.unlink(path)
    assert len(results) == 1
    assert isinstance(results[0], CaseRecord)


def test_leading_trailing_spaces_stripped_in_kernel_field():
    content = VALID_HEADER + "spaced,  1 ,10,1,10,3,4,6,5.5,0.5\n"
    results = _results(content)
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, CaseRecord)
    assert r.raw_fields["min1"] == "1"
    assert r.params.min1 == Decimal("1")
