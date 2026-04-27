# Exhaustion Design

## 目的
本文档用于规划“穷尽给定初始条件组合下解的情况”的批量分析功能。

当前目标不是修改 UI，而是建立一套可复用的批量分析流程，用于：

- 读取 `docs/exhaustion.txt` 中定义的初始条件范围与约束
- 穷举所有满足条件的参数组合
- 对每组参数运行与 `main.py` 一致的判定逻辑
- 输出完整明细与汇总结果，供后续研究和 UI 展示使用

## 当前约束来源
`docs/exhaustion.txt` 当前定义如下：

- `max1 - min1 = 15`
- `max2 - min2 = 15`
- `(max1 + min1) / 2 - (max2 + min2) / 2 >= 1`
- `min1: 2-9, 步长 1`
- `min2: 1-7, 步长 1`
- `a1 = 0.5`
- `a2 = 0.5`
- `c1: 0.1-24, 步长 0.1`
- `c2: 0.1-24, 步长 0.1`
- `p: 0.3-0.9, 步长 0.1`

## 搜索空间规模
若直接按照原始网格全扫：

- 有效 `(min1, min2)` 组合数：`35`
- `p` 取值数：`7`
- `c1` 取值数：`240`
- `c2` 取值数：`240`

原始总组合数：

- `35 * 7 * 240 * 240 = 14,112,000`

但在当前 `main.py` 的硬性校验下，可以先做解析缩域。

### 解析缩域
在当前参数设定下：

- `max1 = min1 + 15`
- `max2 = min2 + 15`
- `a1 = a2 = 0.5`

又因为 `main.py` 当前要求：

- `min1 < v1_star < max1`
- `min2 < v2_star < max2`
- `p * max1 - c1 < 0`
- `(1 - p) * max2 - c2 < 0`

结合：

- `v1_star = (c1 - a1) / p`
- `v2_star = (c2 - a2) / (1 - p)`

可以直接推出：

- `p * max1 < c1 < p * max1 + 0.5`
- `(1 - p) * max2 < c2 < (1 - p) * max2 + 0.5`

在 `0.1` 步长下，每组 `(min1, min2, p)`：

- `c1` 实际只有 `4` 个候选值
- `c2` 实际只有 `4` 个候选值

因此，当前硬约束下真正需要计算的组合数只有：

- `35 * 7 * 4 * 4 = 3920`

结论：

- 该功能不应做成“无脑全扫”
- 应做成“解析缩域 + 批量求解”

## 为什么不能直接批跑 `main.py`
当前 `main.py` 更适合单次运行，不适合批量穷举，原因如下：

1. `run_calculation(...)` 会写入：
   - `results/audit.txt`
   - `results/audit_display.json`
2. `run_calculation(...)` 默认有输出行为
3. bluffing 分支当前通过：
   - 伪造 `input()`
   - 捕获 `stdout`
   - 用正则从 `gaming1030.py` 文本输出中回读 `v1_hat`、`v2_hat`

这套接口适合 CLI/UI，不适合批量研究。

因此，穷举功能实现前，应先抽出纯计算内核。

## 推荐架构
建议分成四层：

### 1. 纯计算内核层
负责：

- 接收单组 `params`
- 做输入校验
- 计算派生量
- 判断 `GT / bluffing`
- 调用对应求解逻辑
- 返回结构化结果

要求：

- 不写文件
- 不打印
- 不依赖 `input()`
- 不从文本中正则回读结果

### 2. 穷举规格解析层
负责解析 `docs/exhaustion.txt`：

- 常量项
- 区间项
- 步长
- 派生等式约束
- 布尔过滤条件

数值生成应优先使用 `Decimal`，避免 `0.1` 浮点误差。

### 3. 批量执行层
负责：

- 先按解析缩域生成候选参数
- 对每组参数调用纯计算内核
- 记录状态、解和失败原因
- 生成完整结果表

### 4. 汇总输出层
负责：

- 生成逐案例明细
- 生成按条件分组的统计汇总
- 输出后续 UI 可读取的结构化结果

## 推荐输出
建议输出到 `results/exhaustion/` 目录下。

### 1. 完整明细
例如：

- `results/exhaustion/cases.csv`

建议字段包括：

- 输入参数：`min1,max1,min2,max2,a1,a2,c1,c2,p`
- 派生量：`v1_star,v2_star,F1(v1_star),F2(v2_star),GT_rhs,GT_condition`
- 分类结果：`scenario,status,status_detail`
- 解：`v1_hat,v2_hat,F1(v1_hat),F2(v2_hat),m_star,v1_hat_m,v2_hat_m`
- 研究字段：`failure_reason_code,root_count,solver_note`

### 2. 汇总统计
例如：

- `results/exhaustion/summary.csv`
- `results/exhaustion/summary.md`

建议至少汇总：

- 总案例数
- GT / bluffing 数量
- `solver_has_valid_solution / solver_no_valid_solution` 数量
- 按 `(min1, min2, p)` 分组的数量分布
- 若做多根检测，再汇总 `0 根 / 1 根 / 多根`

### 3. 元数据
例如：

- `results/exhaustion/metadata.json`

用于记录：

- 解析到的穷举规格
- 运行时间
- 实际总案例数
- 是否启用了额外规则开关

## 对 bluffing 的特殊要求
GT 分支是闭式计算，成本低。

bluffing 分支是数值求解，研究用途下不应仅依赖当前“单中点初值 + `fsolve`”。

更稳妥的方案是：

1. 在 `[min1, max1]` 上做粗采样
2. 检查是否存在符号变化区间
3. 对每个候选区间做根求解
4. 记录根的个数

这样穷举结果更接近“每组参数下解的情况”，而不是“当前单次程序恰好找到的一个结果”。

## 开关前瞻
`docs/main-modified.txt` 中已经提到：

- `p * max1 - c1 < 0`
- `(1 - p) * max2 - c2 < 0`

后续可能做成可选开关。

这会显著改变穷举空间大小：

- 当前硬约束下：`3920`
- 若关闭这两条：会回到接近 `14,112,000`

因此，批量功能设计时应预留规则开关，而不要把当前硬约束写死在穷举器里。

## 推荐实施顺序
1. 先抽出纯计算内核
2. 再实现 `docs/exhaustion.txt` 的解析
3. 再实现按当前硬约束缩域后的批量执行
4. 再输出完整明细和汇总
5. 最后视需要决定是否升级为 bluffing 多根检测版本

## 当前建议
本阶段先不接 UI。

优先目标应是：

- 结果正确
- 结果可复查
- 批量运行稳定
- 输出适合后续研究分析
## Locked Design Decisions
The following design decisions are now fixed:

- exhaustion results should use research-oriented summary classification
- bluffing solving should support both `compat` and `research` modes
- multiple roots, when found, must be preserved in the kernel result and exposed to batch reporting

