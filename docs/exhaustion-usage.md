# Exhaustion Enumerator — Usage Guide

## 用途

穷举器（exhaustion enumerator）自动枚举 `docs/exhaustion.txt` 定义的所有合法参数组合，对每组参数调用计算内核，并将结果写成 CSV 和 JSON 两个文件，供后续研究分析使用。

---

## 快速开始

环境要求：Python 3.11+，scipy >= 1.9。建议在虚拟环境中执行（venv 建立步骤见 README 的 Installation 一节）。

```bash
pip install -e .
python -m gaming_research.exhaustion -o results.csv
```

> 若未 `source .venv/bin/activate`，可直接用 `.venv/bin/python -m gaming_research.exhaustion …` 调用。

跑完后得到两个文件：

| 文件 | 内容 |
|---|---|
| `results.csv` | 长格式结果，每行对应一个参数组合的一个解 |
| `results.metadata.json` | 运行元信息：参数范围快照、选项、用时、case 数量等 |

---

## 完整命令格式

```bash
python -m gaming_research.exhaustion -o <path>.csv \
    [--bluffing-mode {compat,research}] \
    [--enforce-war-payoff-s1 {true,false}] \
    [--enforce-war-payoff-s2 {true,false}] \
    [--allow-large-grid] \
    [--spec-file PATH]
```

### 参数说明

| 参数 | 默认值 | 说明 |
|---|---|---|
| `-o` / `--output` | 必填 | 输出 CSV 路径，必须以 `.csv` 结尾 |
| `--bluffing-mode` | `research` | `research`：多根检测（推荐）；`compat`：单点 fsolve，兼容旧版 |
| `--enforce-war-payoff-s1` | `true` | 是否要求 `p * max1 - c1 < 0`（战争收益约束） |
| `--enforce-war-payoff-s2` | `true` | 是否要求 `(1-p) * max2 - c2 < 0` |
| `--allow-large-grid` | 否 | 绕过 10 万 case 安全门，允许全网格扫描 |
| `--spec-file` | 无 | 从 JSON 文件加载自定义 `GridSpec`；不传则使用内置 `CURRENT_SPEC` |

---

## 参数空间

参数范围编码在 `src/gaming_research/exhaustion/spec.py` 的 `CURRENT_SPEC` 常量里，对应 `docs/exhaustion.txt`：

| 参数 | 范围 | 步长 | 取值数 |
|---|---|---|---|
| `min1` | 2–9 | 1 | 8 |
| `min2` | 1–7 | 1 | 7 |
| `a1`, `a2` | 固定 0.5 | — | 1 |
| `p` | 0.3–0.9 | 0.1 | 7 |
| `c1` | segment-union（默认：0.1–24 step 0.1） | — | 240 |
| `c2` | segment-union（默认：0.1–24 step 0.1） | — | 240 |

`max1 = min1 + 15`，`max2 = min2 + 15`（固定跨度）。

`(min1, min2)` 还需满足均值差条件：`(min1 + max1)/2 - (min2 + max2)/2 ≥ 1`，化简为 `min1 - min2 ≥ 1`。满足条件的有效对共 **35 对**。

---

## 解析缩域（为什么只跑 3920 个 case）

当 `a1 = a2 = 0.5` 且两个战争收益约束都开启时，内核的校验逻辑隐含了如下不等式：

```
p * max1 < c1 < p * max1 + 0.5
(1-p) * max2 < c2 < (1-p) * max2 + 0.5
```

在 0.1 步长下，每组 `(min1, min2, p)` 中 `c1` 和 `c2` 各只有 **4 个合法候选值**，无需扫描全部 240 个。

```
35 对 × 7 个 p × 4 个 c1 × 4 个 c2 = 3920 个 case
```

`metadata.json` 的 `reduction_path` 字段会记录本次走的是哪条路径：`"analytical_reduction"` 或 `"full_grid"`。

---

## 自定义参数空间（`--spec-file`）

需要扫不同的网格时，无需改源码。把一份 JSON 传给 `--spec-file`，CLI 会用它替换 `CURRENT_SPEC` 跑一遍：

```bash
cp samples/exhaustion_spec.example.json my_spec.json
# 编辑 my_spec.json 里的字段
python -m gaming_research.exhaustion -o results.csv --spec-file my_spec.json
```

JSON 顶层是 `schema_version: 2`（当前格式）和 `GridSpec` 字段，与 `metadata.json` 的 `spec` 块一致——可以把上一次跑的 `metadata.json` 的 spec 块抽出来直接复用。

**所有数值字段必须是字符串**（保留 `Decimal` 精度，避免 IEEE-754 转换误差）。`c1` / `c2` 是 segment 列表，其余字段沿用旧形式：

```json
{
  "schema_version": 2,
  "min1_values": ["2", "3", "4"],
  "p_values":    ["0.3", "0.5", "0.7"],
  "a1":          "0.5",
  "a2":          "0.5",
  "c1": [{"type": "range", "min": "0.1", "max": "24", "step": "0.1"}],
  "c2": [{"type": "range", "min": "0.1", "max": "24", "step": "0.1"}],
  ...
}
```

完整字段清单参见 `samples/exhaustion_spec.example.json`。基本校验：列表非空，`span > 0`，segment 列表非空，`RangeSegment.step > 0`、`min <= max`，`PointsSegment.values` 非空，`a1/a2/avg_diff_min >= 0`；任何字段不合法，CLI 退出码 2 并把字段路径（如 `c1[0].step`）打到 stderr。

`metadata.json` 的 `"spec_source"` 字段：传 `--spec-file` 时记录该路径字符串，否则为 `"CURRENT_SPEC"`。

> ⚠️ 当 `a1` 或 `a2` ≠ `0.5` 时，自动 fallback 到全网格路径（`reduction_path: "full_grid"`），case 数可能从 ~3920 飙到千万级，会触发 10 万 case 安全门。确实要跑加 `--allow-large-grid`。

---

## Segment 语法（c1 / c2）

`c1` 和 `c2` 各自由一个 **segment 列表**定义，每个 segment 是一段 range 或一组离散 points。多个 segment 之间取**并集**，重复点自动去重，最终在轴上以**升序**展开。

### Range segment

```json
{"type": "range", "min": "5.1", "max": "5.6", "step": "0.01"}
```

效果等同于 Phase 3 时代的 `c1_min/c1_max/c1_step`。`min <= max`，`step > 0`。

### Points segment

```json
{"type": "points", "values": ["5.2", "5.5", "5.85"]}
```

任意离散点列表，无需等步长。

### 段并集（混合 / 多段）

需要既扫一个 range，又额外打几个离散点（或扫两个不相邻 range）时，把多个 segment 放到同一个轴的列表里：

```json
"c1": [
  {"type": "range",  "min": "5.11", "max": "5.19", "step": "0.01"},
  {"type": "range",  "min": "5.51", "max": "5.59", "step": "0.01"},
  {"type": "points", "values": ["5.2", "5.5"]}
]
```

上面这条 c1 轴 materialized 后是 `5.11, 5.12, ..., 5.19, 5.2, 5.5, 5.51, ..., 5.59` 共 20 个点。

### 缩域窗口语义（两端都开）

缩域路径（默认 options + `a1=a2=0.5`）下，c1 / c2 的取值会被以下窗口**严格开区间**过滤：

```
p * max1  <  c1  <  p * max1 + a1
(1-p) * max2  <  c2  <  (1-p) * max2 + a2
```

注意是 `<` 不是 `≤`：恰好落在窗口端点的点会被丢掉。这是从 Phase 3 沿用的语义，segment 升级时刻意保留以避免悄悄改语义。

---

## v1 → v2 自动迁移

旧的 schema v1 spec（含 `c1_min`/`c1_max`/`c1_step`、`c2_min`/`c2_max`/`c2_step`）仍可直接 `--spec-file` 传入：CLI 会**在内存里**自动把这六个字段转成一段 `range` segment，然后按 v2 流程跑。触发时 stderr 会打一行提示：

```
note: detected schema_version=1 spec, auto-migrated to v2 in-memory
```

迁移**不会回写**原 JSON 文件。如果想长期使用 v2 形态（避免每次跑都打这行 note），把 `c1_min/c1_max/c1_step` 改成：

```json
"c1": [{"type": "range", "min": "<旧c1_min>", "max": "<旧c1_max>", "step": "<旧c1_step>"}]
```

c2 同理。`schema_version` 改为 `2`。

混合写法（同一份 spec 里同时出现 `c1_min` 和 `c1` segment 列表）会被直接拒绝并报错，避免歧义。

---

## 安全门

当估算 case 数超过 **100,000** 时，CLI 直接退出（exit code 2）并打印提示：

```
exhaustion: estimated 14,112,000 cases exceeds the 100,000 threshold.
Pass --allow-large-grid to proceed.
```

默认选项（缩域路径）估算值为 3920，不会触发安全门。

关闭任一战争收益约束后退化为全网格（~1400 万 case），会触发安全门。确实要跑时加 `--allow-large-grid`，注意运行时间会很长。

---

## 结果 CSV 格式

长格式：bluffing 分支找到多个根时，每个根对应一行（`root_index` 区分）。

关键列说明：

| 列 | 说明 |
|---|---|
| `case_id` | 参数编码，如 `m1=2_m2=1_p=0.3_c1=5.2_c2=11.3` |
| `status` | `solver_has_valid_solution` / `solver_no_valid_solution` / `validation_failed` |
| `scenario` | `GT`（闭式解）或 `bluffing`（数值求解） |
| `solver_mode` | `closed_form` / `research` / `compat` |
| `root_index` | 多根时的根序号（0-based） |
| `is_selected` | `true` 表示被选中的根（唯一） |
| `v1_hat`, `v2_hat` | 均衡值 |
| `in_support` | 是否在支撑区间内 |
| `F1_v1_hat`, `F2_v2_hat` | 对应的 CDF 值 |
| `m_star` | GT 分支的 m* 值（bluffing 为空） |
| `v1_star`, `v2_star` | 派生量 |
| `GT_condition` | GT 条件是否成立 |
| `min1` … `p` | 原始参数字符串（原样回写） |

完整列顺序见 `src/gaming_research/loader/writer.py` 中的 `OUTPUT_COLUMNS`。

---

## metadata.json 结构

```json
{
  "schema_version": 1,
  "package_version": "0.1.0",
  "started_at": "2026-04-30T10:00:00.000000+00:00",
  "finished_at": "2026-04-30T10:00:01.000000+00:00",
  "elapsed_seconds": 1.0,
  "spec": { ... },
  "spec_source": "CURRENT_SPEC",
  "options": {
    "bluffing_solver_mode": "research",
    "enforce_war_payoff_s1": true,
    "enforce_war_payoff_s2": true,
    "bluffing_sample_count": 200,
    "denom_eps": 1e-12
  },
  "estimated_case_count": 3920,
  "ran_case_count": 3920,
  "output_row_count": 3920,
  "reduction_path": "analytical_reduction",
  "allow_large_grid_used": false,
  "truncated": false,
  "truncation_reason": null
}
```

`output_row_count` 与 `ran_case_count` 在所有 case 均为单根时相等；bluffing 多根 case 会使前者更大。

---

## 退出码

| 情况 | 退出码 |
|---|---|
| 正常完成 | `0` |
| `-o` 路径不以 `.csv` 结尾 | `2` |
| 安全门拒绝（未传 `--allow-large-grid`） | `2` |
| 输出文件不可写 | `2` |
| CLI 参数错误 | `2` |
