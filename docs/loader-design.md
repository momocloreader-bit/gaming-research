# Loader Design

## Purpose
This document specifies the **table → kernel** input bridge: how rows of a parameter table are read, validated structurally, packaged into `CaseRecord` objects, fed to the kernel, and written back out as a per-row result table.

This is the second phase of `gaming-research`, planned to start **after** the kernel passes its tests. It is parallel to (not a replacement for) the exhaustion enumerator described in `exhaustion-design.md`:

- **exhaustion**: parameters generated from a constraint spec (`docs/exhaustion.txt`)
- **loader**: parameters read from an external table (CSV today, possibly other formats later)

Both reuse the same kernel and the same output row shape.

## Design Stance
This is a research project, not a production data pipeline. The loader is therefore deliberately small and opinionated rather than maximally configurable. The locked choices below favor short code, easy traceability, and minimal external dependencies over flexibility for hypothetical future use cases.

## Locked Decisions

### Schema lives in code, not in a config file
Column names and types are declared in a Python module (`loader/schema.py`), not a YAML/JSON config. If the table layout changes, you edit one Python file. Adding a config-file layer would buy nothing for a single-user research workflow and would add a parser to debug.

### Output format is long, not wide
Each kernel `Solution` produces one output row. A multi-root case becomes multiple rows distinguished by `root_index`. Wide format (e.g. `v1_hat_0`, `v1_hat_1`, ...) is rejected because the maximum root count is unknown ahead of time and because long format is what downstream analysis (pandas group-by, plotting) wants anyway.

### `case_id` is optional
If the input table has a `case_id` column, the loader uses it. If not, the loader auto-generates `row_00001`, `row_00002`, ... so you can throw any CSV at it without thinking. The auto-id format is fixed and zero-padded so lexical sort matches numeric sort.

### Input source is CSV, parsed by stdlib `csv`
Not pandas. The reason is precision: pandas reads numeric columns as `float` by default, which silently drops the `0.1`-step accuracy the upstream uses. Stdlib `csv` returns strings, which the loader converts directly to `Decimal`. No extra dependency, no precision loss. If a future need requires Parquet or SQL, swap the reader module — the rest of the pipeline does not change.

### Passthrough metadata is implicit
Any column that is neither `case_id` nor one of the nine kernel parameter fields is treated as passthrough metadata and forwarded to every output row produced by that input row. No allowlist needed.

### Loader-level validation is type/structure only
The loader checks: required column present, value parseable as `Decimal`. It does **not** duplicate the kernel's mathematical validation (`p` in unit interval, `c1 > a1`, etc.). The split:
- loader rejects -> data problem
- kernel `validation_failed` -> model-domain problem
- kernel `solver_no_valid_solution` -> solver outcome

### One bad row never aborts the batch
Loader rejection is recorded as one output row with `status = loader_rejected` and an error column. Processing continues. The CLI exit code is still `0` if at least one row was attempted; a summary line on stderr reports counts.

### Decimal preserved through to output
Numeric values are kept as `Decimal` from CSV string -> `Params` -> CSV string output. The kernel still converts to `float` internally for solving, but the original `Decimal` text is what gets written back. No silent reformatting.

### Single output file, no run-id directory tree
Output is one CSV at the path the user gives via `-o`. No `results/runs/<timestamp>/...` scheme. If the user wants multiple runs side by side they pick different filenames. Research-grade simplicity.

## Data Shapes

### Column schema (in `loader/schema.py`)
```python
KERNEL_FIELDS = ("min1", "max1", "min2", "max2", "a1", "a2", "c1", "c2", "p")
ID_COLUMN = "case_id"          # optional in input; auto-generated if missing
AUTO_ID_FORMAT = "row_{:05d}"  # 1-based row index, padded to 5 digits
```
That is the entire schema. There is no per-column type config; every kernel field is `Decimal` and required.

### CaseRecord envelope
```python
@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    params: Params
    metadata: Mapping[str, str]   # passthrough columns, raw strings
```

### LoaderError
```python
@dataclass(frozen=True)
class LoaderError:
    case_id: str
    reason_code: str             # missing_required_column | unparseable_decimal | empty_value
    reason_detail: str           # e.g. "c2"
    metadata: Mapping[str, str]  # passthrough columns from the offending row
```

The loader's reader yields a flat sequence of `CaseRecord | LoaderError`, not exceptions. Per-row failures are values, not control flow.

## Pipeline
```
CSV file
   |  csv.DictReader  (strings only)
   v
[ for each row ]
   |  - resolve case_id (column or auto)
   |  - extract metadata (everything not id and not kernel field)
   |  - parse 9 kernel fields as Decimal
   v
CaseRecord  or  LoaderError
   |
   |  if CaseRecord: kernel.evaluate_case(record.params, options)
   v
KernelResult or LoaderError
   |
   |  flatten to one or more output rows:
   |    - LoaderError                  -> 1 row, status=loader_rejected
   |    - validation_failed             -> 1 row, no solution columns
   |    - solver result with 0 solutions-> 1 row, no solution columns
   |    - solver result with k>=1       -> k rows, root_index 0..k-1
   v
output CSV
```

## Output Schema (long format)
Fixed column order:
```
case_id, <metadata columns in input order>,
status, status_detail, scenario, solver_mode,
root_index, v1_hat, v2_hat, in_support, F1_v1_hat, F2_v2_hat, m_star,
v1_star, v2_star, F1_v1_star, F2_v2_star, GT_rhs, GT_condition,
loader_error_code, loader_error_detail,
min1, max1, min2, max2, a1, a2, c1, c2, p
```

Empty cells are written as the empty string, not `NaN` / `None`. Numeric columns preserve `Decimal` text where the source was `Decimal`; computed `float` quantities are written with a fixed format (`{:.10g}`).

## CLI
```
python -m gaming_research.loader INPUT.csv -o OUTPUT.csv [--bluffing-mode research|compat]
```
Defaults: `--bluffing-mode research`. Anything else (tolerances, sample count) stays at kernel defaults; expose more flags only when a real research case requires it.

stderr summary on exit:
```
loader: <n_rows> rows read, <n_loader_rejected> rejected at loader, <n_validation_failed> failed validation, <n_solved> solved, <n_total_solutions> total solution rows
```

## Module Layout (additive to phase one)
```
src/gaming_research/
  loader/
    __init__.py
    schema.py        # column constants, auto-id format
    reader.py        # CSV -> Iterable[CaseRecord | LoaderError]
    runner.py        # CaseRecord -> KernelResult, plus error pass-through
    writer.py        # results -> long-format CSV rows
    cli.py           # python -m gaming_research.loader entry point
tests/
  test_loader_reader.py
  test_loader_writer.py
  test_loader_end_to_end.py   # tiny CSV in, expected CSV out
```

## Test Plan (when implemented)
- `test_loader_reader.py`: missing required column, unparseable decimal, empty value, no `case_id` column triggers auto-id, extra columns become metadata.
- `test_loader_writer.py`: multi-root case expands to multiple rows; loader-rejected rows have empty solution columns; column order is stable.
- `test_loader_end_to_end.py`: a 5-row fixture covering one GT case, one bluffing single-root, one bluffing multi-root, one kernel `validation_failed`, one loader-rejected row. Compare full output CSV byte-for-byte against a checked-in golden file.

## Out of Scope
- Parquet, Excel, SQL, or streaming sources. CSV only for now.
- Parallel execution across rows. Single-process loop is fine at research data sizes; revisit only if a real run is too slow.
- Resume / checkpointing. Re-run the whole file.
- Per-row option overrides via columns (e.g. row-specific bluffing mode). Single CLI flag applies to the whole run.
- Schema migration helpers, column auto-detection, fuzzy column matching. Column names must match exactly.

## Phase Sequencing
1. Finish the kernel per `kernel-implementation-plan.md` and pass its tests.
2. Then build `loader/` per this document.
3. Exhaustion enumerator (`exhaustion-design.md`) is independent of the loader and can be sequenced before, after, or in parallel.

This document does not unlock implementation work yet. It exists so that when the kernel is done, the loader's shape is already decided.
