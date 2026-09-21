# CUMCM 状态机与失效传播

## 正常路径

```text
01 doctor
  → 02 brainstorm（用户确认执行边界）
  → 03 project-start（用户确认开工）
  → 04 modeling
  → G1（用户确认模型）
  → 05 coding-visual
  → 06 result-mvp
  → G2（用户确认结果）
  → 07 drawio（按需）
  → 08 template
  → 09 writing
  → 10 latex
  → 11 verify
  → 12 docx（按需）
  → 13 paper-review
```

`00-cumcm-orchestrator` 是控制平面，不取代以上业务阶段。每个阶段只能由主控推进，专业 agent 只能完成自己的阶段并回报状态。

## 门禁语义

| 门 | 进入条件 | 允许继续的唯一证据 | 失效触发 |
|---|---|---|---|
| G1 | 候选模型、假设、约束、基线、验证计划齐全 | 用户明确写出问题范围、主模型、主要假设、基线并允许编码 | 题意、模型、约束或目标变化 |
| G2 | 3.5 MVP 三层检查全部通过且无 critical/high | 用户明确确认关键结果、异常解释、限制并允许进入论文 | 代码、数据口径、核心数字或结果验证变化 |
| 11 verify | 证据链、代码复现、PDF 页面和引用全部通过 | `reports/VERIFY_REPORT.md` 为 PASS | 任一 canonical 事实源在验收后变化 |

## 状态转换

允许：`NOT_STARTED → RUNNING → PASS`，或 `RUNNING → WAITING_USER/BLOCKED/FAIL`。
`WAITING_USER` 只能由用户明确确认或退回决定解除；不得由 agent 猜测。
`FAIL` 修复后必须创建新 `run_id` 或明确的重跑记录，不能直接把旧 FAIL 改成 PASS。

## 失效传播

- 题面/附件/数据结构变化：使 modeling、G1、coding、MVP、G2、writing、verify 失效。
- 模型/公式/约束变化：使 G1、coding、MVP、G2、writing、verify 失效。
- 代码/结果/随机种子/环境变化：使 MVP、G2、writing、verify 失效。
- 图表源数据变化：使嵌入图、writing、latex、verify 失效。
- 模板类文件或版式参数变化：使 template、writing、latex、verify 失效。
- 正文事实、公式、数字或引用变化：使 latex、verify、paper-review 失效。
- 纯措辞变化：至少使 writing、latex、verify、paper-review 重新检查；不自动使模型和结果失效。

每次传播都要在 `reports/INVALIDATION_LOG.csv` 登记源资产、受影响资产、原因、时间、run_id 和需要重跑的阶段。
