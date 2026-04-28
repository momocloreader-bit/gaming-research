# Loader Implementation Plan

## Purpose
This document records the concrete implementation decisions for **Phase 2** of `gaming-research`. It sits one level below `loader-design.md`: the design doc defines *what* the loader must do; this plan fixes *how* it will be built.

All decisions here were reviewed and approved before any code was written. If this document contradicts `loader-design.md`, the design doc wins — stop and ask before implementing the disagreeing piece.

## Locked Implementation Decisions
- Stdlib `csv.DictReader` only; no pandas, no polars.
- Per-row failures are `LoaderError` values; no exception propagates past `read_cases`.
- `CaseRecord` and `LoaderError` are `@dataclass(frozen=True)`.
- Decimal text round-trips byte-for-byte through the 9 kernel-field columns.
- Computed `float` quantities use `{:.10g}` format.
- Bool columns (`in_support`, `GT_condition`, `is_selected`) write as `true` / `false` (lowercase).
- Empty cells write as the empty string — never `NaN`, never `None`.
- Output is long format (one row per `Solution`), LF line endings, UTF-8 (no BOM).
- Input is read with `encoding="utf-8-sig"` to silently consume Excel-style BOM.
- Output column order is fixed and owned by a single tuple constant in `writer.py`.
- CLI exposes exactly three flags: `--bluffing-mode`, `--enforce-war-payoff-s1`, `--enforce-war-payoff-s2`.

## Package Layout
```
src/gaming_research/
  loader/
    __init__.py      # re-exports: read_cases, run, CaseRecord, LoaderError
    schema.py        # column constants, auto-id format, CaseRecord, LoaderError
    reader.py        # read_cases(path) -> Iterator[CaseRecord | LoaderError]
    runner.py        # run(record_or_error, options) -> KernelResult | LoaderError
    writer.py        # OUTPUT_COLUMNS tuple; flatten(); write_rows()
    cli.py           # python -m gaming_research.loader entry point
tests/
  fixtures/
    loader/
      input.csv          # 4-row golden input
      expected_output.csv  # 4-row golden output (byte-for-byte reference)
  test_loader_reader.py
  test_loader_writer.py
  test_loader_end_to_end.py
```

No files under `src/gaming_research/kernel/` are modified.

## Data Shapes

### Schema constants (`schema.py`)
```python
KERNEL_FIELDS: tuple[str, ...] = (
    "min1", "max1", "min2", "max2", "a1", "a2", "c1", "c2", "p"
)
ID_COLUMN: str = "case_id"
AUTO_ID_FORMAT: str = "row_{:05d}"   # 1-based row index
```

### `CaseRecord`
```python
@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    params: Params
    raw_fields: Mapping[str, str]   # original strings for the 9 kernel fields
    metadata: Mapping[str, str]     # passthrough columns, raw strings, input order
```

`raw_fields` holds the exact CSV strings (after strip-and-empty check passes) so the writer can echo them byte-for-byte without re-serialising `Decimal`.

### `LoaderError`
```python
@dataclass(frozen=True)
class LoaderError:
    case_id: str                    # resolved or auto-generated
    reason_code: str                # stable contract: see table below
    reason_detail: str              # short English, e.g. field name
    raw_fields: Mapping[str, str]   # whatever kernel-field strings were present (may be partial)
    metadata: Mapping[str, str]     # passthrough columns from the offending row
```

#### `reason_code` values
| Code | Trigger |
|---|---|
| `missing_required_column` | A column named in `KERNEL_FIELDS` is absent from the CSV header |
| `empty_value` | A kernel-field cell is empty or whitespace-only after `strip()` |
| `unparseable_decimal` | `Decimal(cell.strip())` raises `InvalidOperation` |

`missing_required_column` triggers once per missing column name (checked at header-read time, not per row). All subsequent rows are still attempted for the remaining columns; a row missing only the absent column is also rejected with this code.

When `case_id` is missing or empty the `case_id` field of `LoaderError` is set to the auto-generated id for that row position.

## Reader (`reader.py`)

### Signature
```python
def read_cases(path: str | os.PathLike) -> Iterator[CaseRecord | LoaderError]:
```

### Behaviour
1. Open with `open(path, encoding="utf-8-sig", newline="")`.
2. Wrap in `csv.DictReader`. Header row defines column names.
3. Identify missing required columns at startup (before iterating rows). Yield one `LoaderError(reason_code="missing_required_column", reason_detail=col_name)` per missing column, with `case_id="row_00000"` (sentinel for header-level errors) and empty `raw_fields` / `metadata`.
4. For each data row (1-based index `n`):
   a. Resolve `case_id`:
      - If `ID_COLUMN` not in header: auto-generate `row_{n:05d}`.
      - If `ID_COLUMN` in header and cell is non-empty after strip: use it.
      - If `ID_COLUMN` in header and cell is empty after strip: yield `LoaderError(reason_code="empty_value", reason_detail="case_id", case_id=auto_id)`, skip to next row.
   b. Extract metadata: all columns that are not `ID_COLUMN` and not in `KERNEL_FIELDS`, in the order they appear in the CSV header. Values are raw strings, no transformation.
   c. Parse each kernel field in `KERNEL_FIELDS` order:
      - Strip the cell string. If empty: yield `LoaderError(reason_code="empty_value", reason_detail=field_name, ...)`, skip row.
      - Attempt `Decimal(stripped)`. If `InvalidOperation`: yield `LoaderError(reason_code="unparseable_decimal", reason_detail=field_name, ...)`, skip row.
      - Store the stripped string in `raw_fields[field_name]` for the writer.
   d. Build `Params` from the nine `Decimal` values.
   e. Yield `CaseRecord(case_id, params, raw_fields, metadata)`.
5. Duplicate `case_id` values are silently accepted; each row is processed independently.
6. `raw_fields` in a `LoaderError` holds whichever kernel-field strings were successfully stripped before the failure; the failing field and all later fields are absent.

## Runner (`runner.py`)

### Signature
```python
def run(
    record: CaseRecord | LoaderError,
    options: Options,
) -> tuple[CaseRecord | LoaderError, KernelResult | None]:
```

### Behaviour
- If `record` is `LoaderError`: return `(record, None)` immediately.
- If `record` is `CaseRecord`: call `evaluate_case(record.params, options)`, return `(record, result)`.
- No I/O. No `print`. No `open`. Pure function.

## Writer (`writer.py`)

### Output column order
The canonical column tuple, owned here and nowhere else:

```python
OUTPUT_COLUMNS: tuple[str, ...] = (
    "case_id",
    # metadata columns are inserted here dynamically (see write_rows)
    "status",
    "status_detail",
    "scenario",
    "solver_mode",
    "root_index",
    "is_selected",
    "v1_hat",
    "v2_hat",
    "in_support",
    "F1_v1_hat",
    "F2_v2_hat",
    "m_star",
    "v1_star",
    "v2_star",
    "F1_v1_star",
    "F2_v2_star",
    "GT_rhs",
    "GT_condition",
    "loader_error_code",
    "loader_error_detail",
    "min1",
    "max1",
    "min2",
    "max2",
    "a1",
    "a2",
    "c1",
    "c2",
    "p",
)
```

Metadata columns are injected between `case_id` and `status` in the order they appear in the input CSV header. `write_rows` receives the metadata column names as a parameter and builds the full header tuple once.

### Formatting rules
| Value type | Format |
|---|---|
| Kernel-field string (from `raw_fields`) | Exact input string, no transformation |
| `float` quantity | `f"{value:.10g}"` |
| `bool` | `"true"` or `"false"` |
| `int` (e.g. `root_index`) | `str(value)` |
| `None` | `""` (empty string) |
| Missing / not applicable | `""` (empty string) |

### Row expansion rules

**`LoaderError` input (status = `loader_rejected`)**
- `status` = `"loader_rejected"`
- `status_detail` = `record.reason_code` (duplicate of `loader_error_code`)
- `scenario`, `solver_mode` = `""`
- `root_index`, `is_selected` = `""`
- All solution columns (`v1_hat` … `GT_condition`) = `""`
- `loader_error_code` = `record.reason_code`
- `loader_error_detail` = `record.reason_detail`
- Kernel-field columns = values from `record.raw_fields` if present, else `""`
- Metadata columns = values from `record.metadata`
- Emits exactly **1 row**.

**`KernelResult` with `status = "validation_failed"`**
- `status` = `"validation_failed"`
- `status_detail` = `result.summary.status_detail` (kernel's comma-joined failure codes)
- `scenario`, `solver_mode` = `""`
- `root_index`, `is_selected` = `""`
- All solution columns = `""`
- `loader_error_code`, `loader_error_detail` = `""`
- Derived columns (`v1_star`, `v2_star`, `F1_v1_star`, `F2_v2_star`, `GT_rhs`) = from `result.derived` if not `None`, else `""`
- `GT_condition` = from `result.derived` if not `None`, else `""`
- Kernel-field columns = from `record.raw_fields`
- Emits exactly **1 row**.

**`KernelResult` with `status = "solver_no_valid_solution"`**
- Same as `validation_failed` except `scenario` and `solver_mode` are populated from `result.branch`.
- Derived columns and `GT_condition` are always populated (validation passed).
- Emits exactly **1 row**.

**`KernelResult` with `status = "solver_has_valid_solution"` (k ≥ 1 solutions)**
- Emits exactly **k rows**, one per entry in `result.solutions`.
- Per-row fields:
  - `status` = `"solver_has_valid_solution"`
  - `status_detail` = `result.summary.status_detail`
  - `scenario` = `result.branch.scenario`
  - `solver_mode` = `result.branch.solver_mode`
  - `root_index` = `str(solution.root_index)`
  - `is_selected` = `"true"` if `solution.root_index == result.summary.selected_solution_index` else `"false"`
  - `v1_hat`, `v2_hat` = `{:.10g}` formatted
  - `in_support` = `"true"` / `"false"`
  - `F1_v1_hat`, `F2_v2_hat` = `{:.10g}` formatted
  - `m_star` = `{:.10g}` formatted, or `""` if `None`
  - Derived columns = `{:.10g}` formatted from `result.derived`
  - `GT_condition` = `"true"` / `"false"` from `result.derived.GT_condition`
  - `loader_error_code`, `loader_error_detail` = `""`
  - Kernel-field columns = from `record.raw_fields`

### `write_rows` signature
```python
def write_rows(
    path: str | os.PathLike,
    rows: Iterable[dict[str, str]],
    metadata_columns: tuple[str, ...],
) -> None:
```
Opens with `open(path, "w", newline="", encoding="utf-8")`.  
Uses `csv.writer` with `lineterminator="\n"`.  
Writes header as first row (full column tuple with metadata injected).  
Then writes each row dict in column order; missing keys write as `""`.

### `flatten` signature
```python
def flatten(
    record: CaseRecord | LoaderError,
    result: KernelResult | None,
) -> list[dict[str, str]]:
```
Returns 1 or more row dicts. Each dict contains every non-metadata column key. Metadata keys are merged in by `write_rows` — `flatten` does not handle them.

## CLI (`cli.py`)

### Invocation
```
python -m gaming_research.loader INPUT.csv -o OUTPUT.csv \
    [--bluffing-mode {compat,research}] \
    [--enforce-war-payoff-s1 {true,false}] \
    [--enforce-war-payoff-s2 {true,false}]
```

### Argument parsing (argparse)
| Flag | Type | Default | Maps to |
|---|---|---|---|
| `INPUT` | positional str | required | input path |
| `-o` / `--output` | str | required | output path |
| `--bluffing-mode` | `{compat,research}` | `research` | `Options.bluffing_solver_mode` |
| `--enforce-war-payoff-s1` | `{true,false}` | `true` | `Options.enforce_war_payoff_s1` |
| `--enforce-war-payoff-s2` | `{true,false}` | `true` | `Options.enforce_war_payoff_s2` |

`--enforce-war-payoff-s1/s2` accept the strings `"true"` and `"false"` and convert them to `bool`. Unrecognised values cause argparse to exit with code 2.

### Main loop
```python
records = list(read_cases(input_path))
metadata_columns = _infer_metadata_columns(records)
options = Options(
    bluffing_solver_mode=args.bluffing_mode,
    enforce_war_payoff_s1=args.enforce_war_payoff_s1,
    enforce_war_payoff_s2=args.enforce_war_payoff_s2,
)
pairs = [run(r, options) for r in records]
all_rows = [row for record, result in pairs for row in flatten(record, result)]
write_rows(output_path, all_rows, metadata_columns)
```

`_infer_metadata_columns` scans the resolved records for the first `CaseRecord` and reads its `metadata` keys in order; falls back to empty tuple if all records are `LoaderError`.

### Exit codes
| Condition | Code |
|---|---|
| Normal completion (≥0 rows attempted) | `0` |
| Input file not found or not readable | `2` |
| Output path not writable | `2` |
| Invalid CLI arguments (argparse) | `2` |

All per-row failures (loader_rejected, validation_failed, solver_no_valid_solution) do **not** change the exit code; they produce output rows.

### stderr summary (always printed on exit)
```
loader: {n_rows} rows read, {n_loader_rejected} rejected at loader, {n_validation_failed} failed validation, {n_solved} solved, {n_total_solutions} total solution rows
```
`n_rows` = total rows in input.  
`n_loader_rejected` = rows that yielded `LoaderError`.  
`n_validation_failed` = rows where `result.summary.status == "validation_failed"`.  
`n_solved` = rows where `result.summary.status == "solver_has_valid_solution"`.  
`n_total_solutions` = total output rows from solved cases (sum of `len(result.solutions)` over solved cases).

Printed to `sys.stderr` via `print(..., file=sys.stderr)` immediately before `sys.exit`.

## Tests

### `test_loader_reader.py`
Unit tests for `read_cases`. Inputs are constructed via `io.StringIO` wrapped in a helper that writes a temporary file, or by writing small CSV fixtures inline.

Required cases:
- Missing required column (`c2` absent from header) → `LoaderError(reason_code="missing_required_column", reason_detail="c2")`.
- Unparseable decimal (`p="abc"`) → `LoaderError(reason_code="unparseable_decimal", reason_detail="p")`.
- Whitespace-only cell (`min1="   "`) → `LoaderError(reason_code="empty_value", reason_detail="min1")`.
- No `case_id` column → auto-generated ids `row_00001`, `row_00002`, ... for each row.
- `case_id` column present and non-empty → used as-is.
- `case_id` column present but empty cell → `LoaderError(reason_code="empty_value", reason_detail="case_id")`.
- Extra columns → appear in `metadata` in input column order.
- Two rows with the same `case_id` → both yield `CaseRecord`, no error.
- Input with UTF-8 BOM → header parsed correctly (BOM consumed).
- Valid row with leading/trailing spaces in a kernel-field cell → stripped value parsed successfully; `raw_fields` stores the stripped string.

### `test_loader_writer.py`
Unit tests for `flatten` and `write_rows`. Inputs are hand-constructed `CaseRecord` / `LoaderError` / `KernelResult` objects.

Required cases:
- `LoaderError` → single row with `status="loader_rejected"`, `status_detail` equals `reason_code`, solution columns all empty, kernel-field columns echo `raw_fields`.
- `validation_failed` result → single row, solution columns empty, `status_detail` = kernel's joined failure codes.
- `solver_no_valid_solution` result → single row, `scenario` and `solver_mode` populated.
- `solver_has_valid_solution` with **2 Solutions** (hand-crafted `KernelResult`) → 2 rows; exactly one row has `is_selected="true"`; `root_index` values are `"0"` and `"1"`; float columns format as `{:.10g}`; bool columns are `"true"` or `"false"`.
- `m_star=None` → writes `""`.
- Column order matches `OUTPUT_COLUMNS` with metadata injected.
- Output file uses LF line endings.

### `test_loader_end_to_end.py`
Compares full CLI output byte-for-byte against the checked-in golden CSV.

```python
def test_end_to_end(tmp_path):
    input_csv = Path("tests/fixtures/loader/input.csv")
    expected = Path("tests/fixtures/loader/expected_output.csv")
    output = tmp_path / "out.csv"
    result = subprocess.run(
        ["python", "-m", "gaming_research.loader", str(input_csv), "-o", str(output)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert output.read_text(encoding="utf-8") == expected.read_text(encoding="utf-8")
```

#### Fixture parameter sets (4 rows)

**Row 1 — GT valid** (`case_id = "gt_case"`)
```
min1=1, max1=10, min2=1, max2=10, a1=3, a2=4, c1=6, c2=5.5, p=0.5
```
Expected: `status=solver_has_valid_solution`, `status_detail=gt_valid_solution`, `scenario=GT`, `solver_mode=closed_form`, `root_index=0`, `is_selected=true`, `m_star=""`.

**Row 2 — bluffing single valid root** (`case_id = "bluff_case"`)
```
min1=1, max1=10, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=0.5
```
Run with default `--bluffing-mode research`.  
Expected: `status=solver_has_valid_solution`, `status_detail=bluffing_single_valid_root`, `scenario=bluffing`, `solver_mode=research`, `root_index=0`, `is_selected=true`, `m_star` non-empty.

**Row 3 — validation failed** (`case_id = "vf_case"`)
```
min1=1, max1=10, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=1
```
Expected: `status=validation_failed`, `status_detail=p_in_open_unit_interval`, all solution columns empty.

**Row 4 — loader rejected** (`case_id = "lr_case"`)
```
min1=1, max1=10, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=abc
```
Expected: `status=loader_rejected`, `status_detail=unparseable_decimal`, `loader_error_code=unparseable_decimal`, `loader_error_detail=p`.

#### Generating the golden file
After implementing all modules, run:
```bash
python -m gaming_research.loader tests/fixtures/loader/input.csv \
    -o tests/fixtures/loader/expected_output.csv
```
Inspect the output visually, verify all 4 rows are correct, then check it in. This is the byte-for-byte reference for `test_loader_end_to_end.py`.

#### `tests/fixtures/loader/input.csv` content
```
case_id,min1,max1,min2,max2,a1,a2,c1,c2,p
gt_case,1,10,1,10,3,4,6,5.5,0.5
bluff_case,1,10,1,10,3,3,6,6,0.5
vf_case,1,10,1,10,3,3,6,6,1
lr_case,1,10,1,10,3,3,6,6,abc
```

## Out of Scope (Deferred)
- Parquet, Excel, SQL, or streaming sources.
- Per-row option overrides via input columns.
- Parallel execution, async, or chunked processing.
- Resume / checkpoint / partial-output recovery.
- Run-id directory trees or summary `.md` reports.
- Wide-format output.
- `evaluate_csv(...)` facade in the kernel package.
- Any new field on `Options`, `Params`, `KernelResult`, or any other kernel type.
- Phase 3: `exhaustion/`.
