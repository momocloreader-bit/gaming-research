# Exhaustion Implementation Plan

## Purpose
This document records the concrete implementation decisions for **Phase 3** of
`gaming-research`. It sits one level below `exhaustion-design.md`: the design
doc defines *what* the enumerator must do; this plan fixes *how* it will be
built.

All decisions here were reviewed and approved before any code was written. If
this document contradicts `exhaustion-design.md` on a **locked decision** (the
three at the bottom of the design doc), the design doc wins — stop and ask
before implementing the disagreeing piece. Where this doc diverges from the
design doc's *recommendations* (e.g. output file count, directory layout), this
plan wins because Phase 3 scope was narrowed during design review.

## Locked Implementation Decisions
- `GridSpec` is a `@dataclass(frozen=True)`; `CURRENT_SPEC` is a module-level
  constant in `spec.py`. `docs/exhaustion.txt` is never parsed at runtime.
- Every kernel-field value the enumerator generates uses `str(Decimal_value)`
  after Decimal arithmetic. The per-field expected forms are pinned in the
  Decimal Text Formatting section below.
- Domain reduction is gated by an explicit `reduction_eligible(spec, options)`
  predicate (exact text below). Only one path runs per invocation; the chosen
  path is recorded in `metadata.json`.
- Output is exactly two files: `cases.csv` (loader column set) and
  `cases.metadata.json` (derived from cases path via stem replacement).
- `cases.csv` is produced by delegating to `loader.writer.flatten` and
  `loader.writer.write_rows` — no column logic is duplicated in the exhaustion
  package.
- `case_id` encodes the five varying parameters:
  `m1=<min1>_m2=<min2>_p=<p>_c1=<c1>_c2=<c2>`.
- Safety gate default threshold: **100 000**. When
  `estimate_case_count(spec, options) > 100_000` the CLI exits `2` unless
  `--allow-large-grid` is passed.
- Metadata path derivation: replace the `.csv` suffix of the `-o` path with
  `.metadata.json`. The CLI requires the `-o` path to end with `.csv`; if it
  does not, exit `2`.
- Exit code for zero cases (empty reduction window): `0`. `metadata.json`
  records `ran_case_count: 0`.
- Two parallel top-level CLIs: `gaming_research.exhaustion` and
  `gaming_research.loader`. No unified subcommand wrapper.
- Stdlib only; no new runtime dependencies. `pyproject.toml` deps remain
  `["scipy"]`.

## Package Layout

```
src/gaming_research/
  exhaustion/
    __init__.py      # re-exports: enumerate_cases, GridSpec, CURRENT_SPEC
    __main__.py      # calls exhaustion.cli.main()
    spec.py          # GridSpec dataclass; CURRENT_SPEC; estimate_case_count; reduction_eligible
    enumerate.py     # enumerate_cases(spec, options) -> Iterator[CaseRecord]
    runner.py        # run_all(spec, options) -> Iterator[tuple[CaseRecord|LoaderError, KernelResult|None]]
    writer.py        # write_cases(pairs, path); write_metadata(meta, path)
    cli.py           # python -m gaming_research.exhaustion entry point
tests/
  fixtures/
    exhaustion/
      tiny_spec.py              # TINY_SPEC constant (imported by tests)
      expected_cases.csv        # golden cases.csv (byte-for-byte reference)
      expected_metadata.json    # golden metadata.json (schema reference)
  test_exhaustion_spec.py
  test_exhaustion_enumerate.py
  test_exhaustion_writer.py
  test_exhaustion_end_to_end.py
```

Files under `src/gaming_research/kernel/` and `src/gaming_research/loader/` are
not modified.

## `spec.py`

### `GridSpec` dataclass

```python
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class GridSpec:
    min1_values:  tuple[Decimal, ...]
    min2_values:  tuple[Decimal, ...]
    span1:        Decimal          # max1 = min1 + span1
    span2:        Decimal          # max2 = min2 + span2
    a1:           Decimal
    a2:           Decimal
    p_values:     tuple[Decimal, ...]
    c1_min:       Decimal
    c1_max:       Decimal
    c1_step:      Decimal
    c2_min:       Decimal
    c2_max:       Decimal
    c2_step:      Decimal
    avg_diff_min: Decimal          # (avg1 - avg2) >= avg_diff_min filter
```

`max1` and `max2` are derived as `min1 + span1` and `min2 + span2` at
enumeration time; they are not stored in `GridSpec`.

### `CURRENT_SPEC` constant

Encodes `docs/exhaustion.txt` exactly. All values as `Decimal` strings.

```python
CURRENT_SPEC = GridSpec(
    min1_values  = tuple(Decimal(i) for i in range(2, 10)),   # 2..9
    min2_values  = tuple(Decimal(i) for i in range(1, 8)),    # 1..7
    span1        = Decimal("15"),
    span2        = Decimal("15"),
    a1           = Decimal("0.5"),
    a2           = Decimal("0.5"),
    p_values     = tuple(Decimal("0.1") * i for i in range(3, 10)),  # 0.3..0.9
    c1_min       = Decimal("0.1"),
    c1_max       = Decimal("24"),
    c1_step      = Decimal("0.1"),
    c2_min       = Decimal("0.1"),
    c2_max       = Decimal("24"),
    c2_step      = Decimal("0.1"),
    avg_diff_min = Decimal("1"),
)
```

### Helper functions

```python
def estimate_case_count(spec: GridSpec, options: Options) -> int:
```
Returns the estimated number of kernel calls (before kernel validation
filtering). Used by the CLI safety gate.

- If `reduction_eligible(spec, options)`: count valid `(min1, min2)` pairs ×
  `len(p_values)` × `c1_candidates_per_triple` × `c2_candidates_per_triple`,
  where candidate counts are computed analytically (window width ÷ step,
  rounded down, capped at 0).
- Otherwise: count valid `(min1, min2)` pairs × `len(p_values)` ×
  `floor((c1_max - c1_min) / c1_step + 1)` × `floor((c2_max - c2_min) /
  c2_step + 1)`.

A valid `(min1, min2)` pair satisfies:
`(min1 + span1 + min1)/2 - (min2 + span2 + min2)/2 >= avg_diff_min`,
which simplifies (when `span1 == span2`) to `min1 - min2 >= avg_diff_min`.

```python
def reduction_eligible(spec: GridSpec, options: Options) -> bool:
```
Returns `True` when all four conditions hold:

```python
return (
    options.enforce_war_payoff_s1
    and options.enforce_war_payoff_s2
    and spec.a1 == Decimal("0.5")
    and spec.a2 == Decimal("0.5")
)
```

Both functions are pure; no I/O.

## Decimal Text Formatting

Every kernel-field value in a generated `CaseRecord.raw_fields` is the result
of `str(decimal_value)` where `decimal_value` was produced by Decimal
arithmetic on spec constants. The table below pins the expected string form for
each field given representative inputs.

| Field | How produced | Example input | Expected string |
|-------|-------------|---------------|-----------------|
| `min1` | `Decimal(int)` directly | `2` | `"2"` |
| `max1` | `min1 + span1` | `Decimal("2") + Decimal("15")` | `"17"` |
| `min2` | `Decimal(int)` directly | `Decimal("1")` | `"1"` |
| `max2` | `min2 + span2` | `Decimal("1") + Decimal("15")` | `"16"` |
| `a1`   | from `spec.a1` | `Decimal("0.5")` | `"0.5"` |
| `a2`   | from `spec.a2` | `Decimal("0.5")` | `"0.5"` |
| `p`    | from `spec.p_values` | `Decimal("0.1") * 3` | `"0.3"` |
| `c1`   | `p * max1 + c1_step * k` | `Decimal("0.3") * 17 + Decimal("0.1") * 1` | `"5.2"` |
| `c2`   | `(1-p) * max2 + c2_step * k` | `Decimal("0.7") * 16 + Decimal("0.1") * 1` | `"11.3"` |

Note: `Decimal("0.1") * 3` yields `Decimal("0.3")` (str → `"0.3"`), not
`Decimal("0.30")`. The arithmetic must be done with the spec's step constants
(`Decimal("0.1")` literals), not by dividing or multiplying floats.

For the full-grid path, `c1` and `c2` are generated by:

```python
c = c_min
while c <= c_max:
    yield c
    c += c_step
```

This keeps the Decimal context consistent and avoids accumulated error.

## `case_id` Template

Format: `m1=<min1>_m2=<min2>_p=<p>_c1=<c1>_c2=<c2>`

Each value is the same canonical `str(Decimal)` string placed in
`raw_fields`. Fields `a1`, `a2`, `max1`, `max2` are omitted because they are
fully determined by the spec for the current locked grid.

Examples:

| min1 | min2 | p   | c1  | c2   | case_id |
|------|------|-----|-----|------|---------|
| 2    | 1    | 0.3 | 5.2 | 11.3 | `m1=2_m2=1_p=0.3_c1=5.2_c2=11.3` |
| 9    | 7    | 0.9 | 21.7 | 1.8 | `m1=9_m2=7_p=0.9_c1=21.7_c2=1.8` |

## `enumerate.py`

### Signature

```python
from collections.abc import Iterator
from gaming_research.loader.schema import CaseRecord

def enumerate_cases(spec: GridSpec, options: Options) -> Iterator[CaseRecord]:
```

Pure generator; no I/O. Yields `CaseRecord` objects with:
- `case_id`: formatted per the template above
- `params`: a `Params` instance built from the five generated Decimal values
  plus `max1 = min1 + span1`, `max2 = min2 + span2`, `a1`, `a2`
- `raw_fields`: `{field: str(decimal_value)}` for all 9 kernel fields
- `metadata`: `{}` (empty — no passthrough columns from CSV)

### Outer loop (shared by both paths)

```python
for min1 in spec.min1_values:
    max1 = min1 + spec.span1
    for min2 in spec.min2_values:
        max2 = min2 + spec.span2
        avg1 = min1 + spec.span1 / 2
        avg2 = min2 + spec.span2 / 2
        if avg1 - avg2 < spec.avg_diff_min:
            continue                 # prune invalid (min1, min2) pairs
        for p in spec.p_values:
            if reduction_eligible(spec, options):
                yield from _reduction_cases(spec, min1, max1, min2, max2, p)
            else:
                yield from _full_grid_cases(spec, min1, max1, min2, max2, p)
```

The `reduction_eligible` check is inside the loop but its result is constant
for a given run. The redundant checks are cheap; keeping the predicate call
inside avoids a separate flag variable.

### Reduction path (`_reduction_cases`)

For each `(min1, max1, min2, max2, p)`:

1. Compute `c1_lo = p * max1` and `c1_hi = p * max1 + spec.a1`.
2. Iterate `c1` over the open interval `(c1_lo, c1_hi)` using `spec.c1_step`:

```python
c1 = c1_lo + spec.c1_step
while c1 < c1_hi:
    # clamp to spec range
    if spec.c1_min <= c1 <= spec.c1_max:
        ...
    c1 += spec.c1_step
```

3. Similarly compute `c2_lo = (1 - p) * max2`, `c2_hi = c2_lo + spec.a2`,
   iterate `c2` over `(c2_lo, c2_hi)`.
4. For each `(c1, c2)` pair, yield one `CaseRecord`.

For `CURRENT_SPEC` with default options, this yields exactly **3920** records:
35 valid `(min1, min2)` pairs × 7 `p` values × 4 `c1` candidates × 4 `c2`
candidates. The count 35 follows from `min1 - min2 >= 1` with
`min1 ∈ [2,9]`, `min2 ∈ [1,7]`.

### Full-grid path (`_full_grid_cases`)

For each `(min1, max1, min2, max2, p)`:

```python
c1 = spec.c1_min
while c1 <= spec.c1_max:
    c2 = spec.c2_min
    while c2 <= spec.c2_max:
        yield _make_record(min1, max1, min2, max2, p, c1, c2, spec)
        c2 += spec.c2_step
    c1 += spec.c1_step
```

No kernel validation is applied here; the kernel rejects invalid combinations
and they appear in `cases.csv` with `status = "validation_failed"`.

### `_make_record` helper

```python
def _make_record(
    min1: Decimal, max1: Decimal,
    min2: Decimal, max2: Decimal,
    p: Decimal, c1: Decimal, c2: Decimal,
    spec: GridSpec,
) -> CaseRecord:
    raw: dict[str, str] = {
        "min1": str(min1), "max1": str(max1),
        "min2": str(min2), "max2": str(max2),
        "a1":   str(spec.a1), "a2": str(spec.a2),
        "c1":   str(c1), "c2": str(c2),
        "p":    str(p),
    }
    from gaming_research.kernel.types import Params
    params = Params(
        min1=min1, max1=max1, min2=min2, max2=max2,
        a1=spec.a1, a2=spec.a2, c1=c1, c2=c2, p=p,
    )
    case_id = f"m1={raw['min1']}_m2={raw['min2']}_p={raw['p']}_c1={raw['c1']}_c2={raw['c2']}"
    return CaseRecord(case_id=case_id, params=params, raw_fields=raw, metadata={})
```

## `runner.py`

Thin wrapper; no I/O.

```python
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
```

`loader_run` signature: `run(record, options) -> (record, result_or_none)`.
Because `enumerate_cases` only yields `CaseRecord` (never `LoaderError`),
every yielded result will be `(CaseRecord, KernelResult)`. The return type
mirrors `loader.runner.run` for symmetry and forward-compatibility.

## `writer.py`

### `write_cases`

```python
def write_cases(
    pairs: Iterable[tuple[CaseRecord | LoaderError, KernelResult | None]],
    cases_path: str | os.PathLike,
) -> int:
```

Returns the total number of output rows written (after multi-root expansion).

Implementation:
1. Collect `flatten(record, result)` for each pair into a flat list of row
   dicts (delegates entirely to `loader.writer.flatten`).
2. Call `loader.writer.write_rows(cases_path, rows, metadata_columns=())`.
   `metadata_columns` is empty because exhaustion records carry no passthrough
   CSV columns.
3. Returns `len(rows)`.

### `write_metadata`

```python
def write_metadata(meta: dict, metadata_path: str | os.PathLike) -> None:
```

Writes `meta` as JSON with `json.dump(meta, fh, sort_keys=True, indent=2)`,
UTF-8, LF. Opens with `open(path, "w", encoding="utf-8", newline="\n")`.

### `metadata.json` schema

All Decimal values serialised as `str`. All datetimes as ISO-8601 UTC strings.

```json
{
  "schema_version": 1,
  "package_version": "<importlib.metadata.version('gaming-research')>",
  "started_at": "2026-04-29T10:30:00.000000+00:00",
  "finished_at": "2026-04-29T10:34:23.451000+00:00",
  "elapsed_seconds": 263.451,
  "spec": {
    "min1_values":  ["2","3","4","5","6","7","8","9"],
    "min2_values":  ["1","2","3","4","5","6","7"],
    "span1":        "15",
    "span2":        "15",
    "a1":           "0.5",
    "a2":           "0.5",
    "p_values":     ["0.3","0.4","0.5","0.6","0.7","0.8","0.9"],
    "c1_min":       "0.1",
    "c1_max":       "24",
    "c1_step":      "0.1",
    "c2_min":       "0.1",
    "c2_max":       "24",
    "c2_step":      "0.1",
    "avg_diff_min": "1"
  },
  "options": {
    "bluffing_solver_mode":   "research",
    "enforce_war_payoff_s1":  true,
    "enforce_war_payoff_s2":  true,
    "bluffing_sample_count":  200,
    "denom_eps":              1e-12
  },
  "estimated_case_count": 3920,
  "ran_case_count":        3920,
  "output_row_count":      4123,
  "reduction_path":        "analytical_reduction",
  "allow_large_grid_used": false,
  "truncated":             false,
  "truncation_reason":     null
}
```

`reduction_path` is `"analytical_reduction"` when `reduction_eligible` held,
`"full_grid"` otherwise. `truncated` is always `false` in Phase 3 (no
`--max-cases` flag). `ran_case_count` is the number of `CaseRecord` objects
yielded; `output_row_count` is the total flattened rows in `cases.csv`
(header not counted).

## CLI (`cli.py` + `__main__.py`)

### Invocation

```
python -m gaming_research.exhaustion -o cases.csv \
    [--bluffing-mode {compat,research}] \
    [--enforce-war-payoff-s1 {true,false}] \
    [--enforce-war-payoff-s2 {true,false}] \
    [--allow-large-grid]
```

### Argument table

| Flag | Type | Default | Notes |
|------|------|---------|-------|
| `-o` / `--output` | str | required | Path for `cases.csv`. Must end with `.csv`. |
| `--bluffing-mode` | `{compat,research}` | `research` | Maps to `Options.bluffing_solver_mode`. |
| `--enforce-war-payoff-s1` | `{true,false}` | `true` | Maps to `Options.enforce_war_payoff_s1`. |
| `--enforce-war-payoff-s2` | `{true,false}` | `true` | Maps to `Options.enforce_war_payoff_s2`. |
| `--allow-large-grid` | flag | `False` | Bypasses the 100 000 safety gate. |

`--enforce-war-payoff-s1/s2` use the same `_bool_arg` helper as the loader CLI
(`"true"` → `True`, `"false"` → `False`; other values → argparse exit 2).

### Metadata path derivation

```python
if not output_path.endswith(".csv"):
    print("exhaustion: -o path must end with .csv", file=sys.stderr)
    sys.exit(2)
metadata_path = output_path[:-4] + ".metadata.json"
# e.g. "/tmp/cases.csv" -> "/tmp/cases.metadata.json"
```

### Safety gate

```python
estimated = estimate_case_count(CURRENT_SPEC, options)
if estimated > 100_000 and not args.allow_large_grid:
    print(
        f"exhaustion: estimated {estimated:,} cases exceeds the 100,000 "
        f"threshold. Pass --allow-large-grid to proceed.",
        file=sys.stderr,
    )
    sys.exit(2)
```

### Main loop

```python
started_at = datetime.now(timezone.utc)
pairs = list(run_all(CURRENT_SPEC, options))
finished_at = datetime.now(timezone.utc)

output_row_count = write_cases(pairs, output_path)
meta = {
    "schema_version": 1,
    "package_version": importlib.metadata.version("gaming-research"),
    "started_at": started_at.isoformat(),
    "finished_at": finished_at.isoformat(),
    "elapsed_seconds": (finished_at - started_at).total_seconds(),
    "spec": _spec_to_dict(CURRENT_SPEC),
    "options": _options_to_dict(options),
    "estimated_case_count": estimated,
    "ran_case_count": len(pairs),
    "output_row_count": output_row_count,
    "reduction_path": "analytical_reduction" if reduction_eligible(CURRENT_SPEC, options) else "full_grid",
    "allow_large_grid_used": args.allow_large_grid,
    "truncated": False,
    "truncation_reason": None,
}
write_metadata(meta, metadata_path)
```

`_spec_to_dict` serialises all `Decimal` fields to `str` and all tuples to
lists of `str`. `_options_to_dict` serialises the relevant `Options` fields.

### Exit codes

| Condition | Code |
|-----------|------|
| Normal completion | `0` |
| `-o` path does not end with `.csv` | `2` |
| Safety gate refused (no `--allow-large-grid`) | `2` |
| Output file not writable | `2` |
| Invalid CLI arguments (argparse) | `2` |

### stderr summary (printed immediately before `sys.exit`)

```
exhaustion: {ran_case_count} cases, {output_row_count} output rows, {elapsed:.1f}s [{reduction_path}]
```

Example:
```
exhaustion: 3920 cases, 4123 output rows, 263.5s [analytical_reduction]
```

## Tests

### `test_exhaustion_spec.py`

- `test_current_spec_valid_pair_count`: assert `len([…])` over all
  `(min1, min2)` pairs passing the `avg_diff_min` filter equals **35**.
- `test_estimate_case_count_reduction`: with default options,
  `estimate_case_count(CURRENT_SPEC, default_options)` returns **3920**.
- `test_estimate_case_count_full_grid`: with `enforce_war_payoff_s1=False`,
  `estimate_case_count` returns **14 112 000**.
- `test_reduction_eligible_default`: `reduction_eligible(CURRENT_SPEC,
  default_options)` returns `True`.
- `test_reduction_eligible_war_payoff_off`: `reduction_eligible(CURRENT_SPEC,
  Options(enforce_war_payoff_s1=False))` returns `False`.

### `test_exhaustion_enumerate.py`

- `test_reduction_path_case_count`: `sum(1 for _ in enumerate_cases(CURRENT_SPEC, default_options))` equals **3920**.
- `test_reduction_path_c1_values`: for `(min1=2, min2=1, p=0.3)` the c1 values
  in all emitted records equal `{"5.2", "5.3", "5.4", "5.5"}`.
- `test_reduction_path_c2_values`: for same triple, c2 values equal
  `{"11.3", "11.4", "11.5", "11.6"}`.
- `test_case_id_format`: first record from `enumerate_cases(CURRENT_SPEC, …)`
  has `case_id` matching `"m1=2_m2=1_p=0.3_c1=5.2_c2=11.3"`.
- `test_raw_fields_decimal_text`: `raw_fields["min1"]` is `"2"` (not `"2.0"`);
  `raw_fields["p"]` is `"0.3"`; `raw_fields["a1"]` is `"0.5"`.
- `test_full_grid_path_no_reduction`: with `enforce_war_payoff_s1=False`,
  first yielded record has `raw_fields["c1"] == "0.1"` and
  `raw_fields["c2"] == "0.1"`.
- `test_avg_diff_min_filter`: pair `(min1=1, min2=1)` is skipped (avg diff = 0
  < 1); construct a `GridSpec` where this pair would appear and verify it is
  absent.

### `test_exhaustion_writer.py`

- `test_write_cases_row_count`: run `write_cases` on 2 known pairs and verify
  the written CSV has the expected line count.
- `test_metadata_json_keys`: `write_metadata` output parses as JSON and
  contains all required top-level keys from the schema above.
- `test_metadata_path_derivation`: helper (or inline): `"cases.csv"` →
  `"cases.metadata.json"`.

### `test_exhaustion_end_to_end.py`

Uses `TINY_SPEC` (defined below) with default options. Calls the CLI via
`subprocess.run` or by importing `cli.main` with patched `sys.argv`. Compares:

1. `cases.csv` byte-for-byte against `tests/fixtures/exhaustion/expected_cases.csv`.
2. `metadata.json` key-by-key against `tests/fixtures/exhaustion/expected_metadata.json`
   (excluding timing fields `started_at`, `finished_at`, `elapsed_seconds`).

### Fixture spec (`TINY_SPEC`)

Defined in `tests/fixtures/exhaustion/tiny_spec.py` (imported by tests).

```python
from decimal import Decimal
from gaming_research.exhaustion.spec import GridSpec

TINY_SPEC = GridSpec(
    min1_values  = (Decimal("2"),),
    min2_values  = (Decimal("1"),),
    span1        = Decimal("15"),
    span2        = Decimal("15"),
    a1           = Decimal("0.5"),
    a2           = Decimal("0.5"),
    p_values     = (Decimal("0.5"),),
    c1_min       = Decimal("0.1"),
    c1_max       = Decimal("24"),
    c1_step      = Decimal("0.1"),
    c2_min       = Decimal("0.1"),
    c2_max       = Decimal("24"),
    c2_step      = Decimal("0.1"),
    avg_diff_min = Decimal("1"),
)
```

With default options (reduction eligible):

- `(min1=2, min2=1)` — valid pair (avg diff = 1 ≥ 1).
- `p=0.5`, `max1=17`, `max2=16`.
- `c1` window: `(0.5·17, 0.5·17+0.5)` = `(8.5, 9.0)` →
  candidates `{8.6, 8.7, 8.8, 8.9}` (4 values).
- `c2` window: `(0.5·16, 0.5·16+0.5)` = `(8.0, 8.5)` →
  candidates `{8.1, 8.2, 8.3, 8.4}` (4 values).
- Total: **16 cases**.

### Golden file rows (`expected_cases.csv`)

The golden file is generated once by running the end-to-end test in
write-golden mode, then checked in and frozen. It must have exactly:

- 1 header row
- N data rows (one per Solution across all 16 cases; actual count depends on
  solver; must be verified when goldens are first generated)

Column order follows `loader.writer.OUTPUT_COLUMNS` with no metadata columns
(empty metadata).

The golden `expected_metadata.json` covers all fields except timing; timing
fields are excluded from comparison in `test_exhaustion_end_to_end.py`.

### Generating goldens

Run once after implementing Steps 2–6:

```bash
python -m gaming_research.exhaustion \
    --spec tests/fixtures/exhaustion/tiny_spec.py \
    -o tests/fixtures/exhaustion/expected_cases.csv
cp tests/fixtures/exhaustion/expected_cases.metadata.json \
   tests/fixtures/exhaustion/expected_metadata.json
```

Then audit both files manually, commit them, and lock them as the reference.
