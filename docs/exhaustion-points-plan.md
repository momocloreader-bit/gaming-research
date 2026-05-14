# Exhaustion: c1/c2 Discrete-Points Upgrade

## Goal

把 `exhaustion` 模块里 `c1` / `c2` 两条轴从单一 `min/max/step` 三元组升级成 **segment-union** 形式，让 c1/c2 可以表达任意离散点集、任意 range、以及二者的任意并集。一次到位，不留中间形态。

`min1` / `min2` / `p` 三条轴**不动**——它们已经是点列表，无需改造。

## Scope

In:
- `src/gaming_research/exhaustion/spec.py`：`GridSpec` 字段、`from_dict` 解析、`_validate_spec`、`estimate_case_count`、`CURRENT_SPEC` 默认值
- `src/gaming_research/exhaustion/enumerate.py`：`_full_grid_cases`、`_reduction_cases`
- spec JSON schema：`schema_version: 1 → 2`，含迁移
- `tests/`：新增 segment 解析、轴展开、reduction 过滤、迁移测试
- `samples/exhaustion_spec.example.json`、`docs/exhaustion-usage.md`：同步更新

Out:
- 不改 `min1_values` / `min2_values` / `p_values` 的格式
- 不引入 spec 顶层 multi-block
- 不动 `loader/`，worksheet1.csv 类需求继续走 loader

## Schema v2

`c1` / `c2` 各自变成一个 segment 列表，segment 形如：

```json
{"type": "range",  "min": "5.11", "max": "5.19", "step": "0.01"}
{"type": "points", "values": ["5.2", "5.5"]}
```

完整 v2 spec：

```json
{
  "schema_version": 2,
  "min1_values": ["2"],
  "min2_values": ["1"],
  "span1": "15",
  "span2": "15",
  "a1": "0.5",
  "a2": "0.5",
  "p_values": ["0.3"],
  "c1": [{"type": "range", "min": "5.1", "max": "5.6", "step": "0.01"}],
  "c2": [{"type": "range", "min": "11.2", "max": "11.7", "step": "0.01"}],
  "avg_diff_min": "1"
}
```

**删除的字段**：`c1_min`、`c1_max`、`c1_step`、`c2_min`、`c2_max`、`c2_step`。整体范围由 segment 自身表达，不需要再来一道全局过滤。

## 关键决策

1. **缩域窗口边界**：保持当前实现的"两端都开"语义，即 `p*max1 < c1 < p*max1 + a1`、`(1-p)*max2 < c2 < (1-p)*max2 + a2`。理由：与旧实现一致，避免悄悄修改语义。
2. **版本判定（infer-fallback）**：`schema_version` 字段优先；缺失时根据字段形态推断（出现 `c1_min` → v1，出现 `c1` 列表 → v2）。与现有 `from_dict` 容忍 `schema_version` 缺失的风格一致。
3. **v1/v2 字段混用 → 硬报错**：若同一份 spec 既有 `c1_min` 又有 `c1`（或 c2 同理），直接抛 `ValueError`。与现有 `unknown spec field` / `missing spec field` 的严格风格一致。
4. **v1 自动迁移 + stderr 一行提示**：检测到 v1 时自动转成单个 range segment 后继续走 v2 流程，并在 stderr 打一行 `note: detected schema_version=1 spec, auto-migrated to v2 in-memory`。stdout 保持干净，便于用户察觉自己用的是旧格式。

## GridSpec 数据结构

```python
@dataclass(frozen=True)
class RangeSegment:
    min: Decimal
    max: Decimal
    step: Decimal

@dataclass(frozen=True)
class PointsSegment:
    values: tuple[Decimal, ...]

AxisSegment = RangeSegment | PointsSegment

@dataclass(frozen=True)
class GridSpec:
    min1_values:  tuple[Decimal, ...]
    min2_values:  tuple[Decimal, ...]
    span1:        Decimal
    span2:        Decimal
    a1:           Decimal
    a2:           Decimal
    p_values:     tuple[Decimal, ...]
    c1:           tuple[AxisSegment, ...]
    c2:           tuple[AxisSegment, ...]
    avg_diff_min: Decimal
```

## 轴展开

新增 `enumerate.py` 内部函数 `_materialize_axis(segments) -> tuple[Decimal, ...]`：

- `RangeSegment`：从 `min` 开始以 `step` 步进，`while v <= max` 收集
- `PointsSegment`：直接展开 `values`
- 拼接所有 segment，**去重 + 排序**后返回（去重以 `Decimal` 等价为准；排序便于结果稳定和阅读）

`_full_grid_cases` 改为对 `_materialize_axis(spec.c1)` × `_materialize_axis(spec.c2)` 双循环，删掉原本的 step-walk。

`_reduction_cases` 改为对 `_materialize_axis(spec.c1)` 做窗口过滤 `c1_lo < c < c1_hi`（两端都开），c2 同理，删掉原本的步进起点偏移。

`estimate_case_count`：把 `n_c1 = floor(...) + 1` 改成 `len(_materialize_axis(spec.c1))`；reduction 分支也改成对 materialized 点列表过滤后计数。

## 校验规则与错误信息

沿用 `spec.py` 现有 `"field X must be a string, got Y"` / `"unknown spec field: ..."` 风格。新增 / 修改的校验条目：

- `c1` 必须是 list，否则 `"field c1 must be a list, got <type>"`
- `c1` 必须非空，否则 `"c1 must contain at least one segment"`（c2 同理）
- segment 必须是 dict，否则 `"field c1[<i>] must be an object, got <type>"`
- segment 必须含 `type` 字段且取值为 `"range"` 或 `"points"`，否则 `"c1[<i>].type must be 'range' or 'points', got <val>"`
- `RangeSegment`：必须含 `min` / `max` / `step` 三个字符串字段；`step > 0`，否则 `"c1[<i>].step (<step>) must be > 0"`；`min <= max`，否则 `"c1[<i>].min (<min>) must be <= max (<max>)"`
- `PointsSegment`：必须含 `values` 列表字段；非空，否则 `"c1[<i>].values must be a non-empty list"`；每项必须是字符串
- 段内、段间允许重复点（materialize 时去重），不 warn

### 版本判定与混用检测

`from_dict` 入口流程：

1. 读取 `schema_version`（若有）
2. 检测 `c1_min/c1_max/c1_step/c2_min/c2_max/c2_step`（v1 标志字段集合）和 `c1/c2`（v2 标志字段集合）的出现情况
3. 判定：
   - 显式 `schema_version=2` 且检测到任意 v1 字段 → 报错 `"schema_version=2 spec must not contain legacy field: c1_min"`（举第一个出现的）
   - 显式 `schema_version=1` 且检测到任意 v2 字段 → 报错 `"schema_version=1 spec must not contain v2 field: c1"`
   - 显式 `schema_version=2` → 走 v2 解析
   - 显式 `schema_version=1` → 走 v1→v2 迁移
   - `schema_version` 缺失：若 v1 字段和 v2 字段都出现 → 报错 `"spec mixes v1 fields (c1_min) and v2 fields (c1); set schema_version explicitly"`；只出现一种 → 按其形态走对应路径

## 迁移函数

`spec.py` 新增模块级函数：

```python
def _migrate_v1_to_v2(payload: dict) -> dict:
    """Return a new dict in v2 shape. Caller is responsible for emitting the
    stderr notice; this function is pure."""
```

行为：
- 输入：含 `c1_min/c1_max/c1_step`（和 c2 同理）的 dict
- 输出：移除这六个字段，新增 `c1` / `c2` 字段为单元素列表：
  `[{"type": "range", "min": payload["c1_min"], "max": payload["c1_max"], "step": payload["c1_step"]}]`
- 不修改 `schema_version`（由调用方决定是否写）
- 不做语义校验（留给 v2 校验路径统一处理）

`from_dict` 在判定为"走迁移路径"分支时调它，把迁移产物喂给 v2 校验路径，并向调用方返回一个迁移标志（具体 API：`from_dict(payload) -> tuple[GridSpec, bool]` 或新增 `from_dict_with_meta`——实施时择一定型）。**`spec.py` 自身不写 stderr**，以保住 `implementation.md` 的 "I/O confined" 规则。stderr 的一行 `note: detected schema_version=1 spec, auto-migrated to v2 in-memory` 由 `cli.py` 在拿到迁移标志为真时打一次。

`CURRENT_SPEC` 用 v2 形式重写（语义不变：c1 / c2 各一个 range segment，min=0.1 / max=24 / step=0.1）。

## Fixtures

`tests/fixtures/exhaustion/` 新增：

- `v1_spec.json` —— 完整 v1 spec（schema_version=1，含 `c1_min/c1_max/c1_step`），直接复用现有 `exhaustion_spec.0514.json` 的内容。用于迁移回归。
- `v2_spec.json` —— `v1_spec.json` 的预期迁移结果（schema_version=2，含 `c1` / `c2` 单 range segment）。用于断言迁移产物。
- `points_spec.json` —— 一个真正用到 segment-union 的 v2 spec：`c1` 含 1 个 range + 1 个 points 段，`c2` 含 2 个 range 段。覆盖 worksheet1 风格的研究形态。

现存 `tiny_spec.py::TINY_SPEC` 同步升级到 v2 形式（单 range segment）；保留命名与现有 import 兼容。

## 测试覆盖

`tests/test_exhaustion_spec.py`（扩充）：
- v2 spec 完整解析成功
- v1 spec 自动迁移，解析后字段与 `v2_spec.json` 等价；同时 capsys 捕获 stderr 包含 `auto-migrated`
- `schema_version=2` 但出现 `c1_min` → 报错且 message 含 `must not contain legacy field`
- `schema_version=1` 但出现 `c1` 列表 → 报错且 message 含 `must not contain v2 field`
- `schema_version` 缺失且同时含 `c1_min` 和 `c1` → 报错且 message 含 `mixes v1 fields ... and v2 fields`
- segment 列表为空 → 报错
- segment `type` 缺失或非法 → 报错
- `RangeSegment.step <= 0` → 报错
- `RangeSegment.min > max` → 报错
- `PointsSegment.values` 为空 → 报错

`tests/test_exhaustion_enumerate.py`（扩充）：
- 单 range segment 的 full-grid case 集合与 v1 golden CSV 逐行一致（回归保护，沿用 `expected_cases.csv`）
- 单 points segment：枚举出的 case 数和 (c1, c2) 取值与显式列表匹配
- 多 segment 并集：c1 含两段不相邻 range，断言 materialize 后**去重 + 升序**
- reduction 两端开的回归：构造 spec 使 `p*max1` 恰好等于某个 points 段中的点 v；断言结果中**不**包含 c1=v 的 case
- reduction 与 points 段组合：构造 spec 使 points 段一半在窗口内一半在窗口外，断言只有窗口内的被保留

`tests/test_exhaustion_end_to_end.py`（扩充）：
- 把 `points_spec.json` 端到端跑通，断言生成的 `cases.csv` 行数 = 估算 case 数

## 样例与文档

- `samples/exhaustion_spec.example.json`：升级到 v2
- `samples/exhaustion_default.csv` / `.metadata.json`：若 metadata 里写了 schema_version 也要同步
- `docs/exhaustion-usage.md`：新增 segment 语法章节、迁移说明
- `docs/exhaustion-design.md`：在 Locked Design Decisions 区追加"c1/c2 升级为 segment-union（schema v2）"

## 实施顺序

1. `spec.py`：加 segment 类型、改 `GridSpec`、写 v1→v2 迁移、改 `from_dict` / `_validate_spec` / `estimate_case_count` / `CURRENT_SPEC`
2. `enumerate.py`：加 `_materialize_axis`、改 `_full_grid_cases` / `_reduction_cases`
3. 跑现有测试，修崩掉的；旧 `exhaustion_spec.0514.json` 走迁移路径应仍可用
4. 加新测试（spec、enumerate）
5. 升级 sample 和文档
6. 端到端 smoke：拿 worksheet1 的 c1/c2 取值写一个 v2 spec，跑通 → 用结果和 loader 跑 worksheet1.csv 的结果在重叠 case 上对账

## 开放问题

无。所有先前的开放问题已并入"关键决策"与"校验规则与错误信息"两节。
