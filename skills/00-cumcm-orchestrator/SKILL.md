---
name: 00-cumcm-orchestrator
description: "编排高教杯数学建模阶段、门禁、状态、文件锁与专业智能体协作。"
---

# 高教杯多智能体总控编排器

`00-cumcm-orchestrator` 是控制平面，不是普通业务阶段。它是唯一可以推进阶段、写入用户决策事实源、改变 G1/G2 状态和合并专业 agent 输出的角色。

## 阶段合同

```yaml
phase_id: 00-cumcm-orchestrator
display_name: 国赛总控编排
owner_agent: orchestrator
entry_conditions:
  - 本地项目根目录已确定
  - shared/PHASE_REGISTRY.json 可读
  - reports/WORKFLOW_STATE.json 存在或允许初始化
  - reports/locks/ 中没有冲突的 HELD 锁
inputs:
  - shared/PHASE_REGISTRY.json
  - shared/WORKFLOW_STATE.schema.json
  - reports/WORKFLOW_STATE.json
  - reports/DECISION_LEDGER.yaml
  - reports/locks/
  - 各阶段 packet、报告和 canonical 哈希
actions:
  - 校验当前阶段进入条件
  - 分派且只分派当前阶段 owner agent
  - 汇总阶段输出并记录 run_id、输入哈希和输出哈希
  - 管理 WAITING_USER、G1、G2 和交付确认
  - 传播失效并决定失败回退阶段
outputs:
  - reports/WORKFLOW_STATE.json
  - reports/DECISION_LEDGER.yaml
  - reports/USER_DECISIONS.md
  - reports/INVALIDATION_LOG.csv
  - reports/locks/
  - 阶段调度记录和交付 manifest
exit_conditions:
  - 当前阶段达到 PASS，且下一阶段 entry_conditions 已满足
  - 或阶段明确进入 WAITING_USER、BLOCKED 或 FAIL，并记录责任方
failure_return:
  - 按 orchestrator/STATE_MACHINE.md 的责任映射回退
  - 新 run_id 重跑受影响阶段，不继承旧 PASS
writable_paths:
  - reports/WORKFLOW_STATE.json
  - reports/DECISION_LEDGER.yaml
  - reports/USER_DECISIONS.md
  - reports/MVP_DECISION.md
  - reports/INVALIDATION_LOG.csv
  - reports/locks/
read_only_paths:
  - 专业 agent 的 canonical 代码、结果、图表、正文和模板资产
invalidates:
  - 根据依赖图使旧门禁和下游资产变为 obsolete 或 INVALIDATED
user_gate: true
```

## 唯一事实源

- 阶段顺序和 owner 只来自 `shared/PHASE_REGISTRY.json`。
- 全局状态只来自项目 `reports/WORKFLOW_STATE.json`。
- 开工、G1、G2、交付和最终终审确认只来自 `reports/DECISION_LEDGER.yaml`。
- `USER_DECISIONS.md`、`MVP_DECISION.md` 和 `TECHNICAL_DECISIONS.md` 是视图或技术提案，不得反向改变门禁。
- 题面、代码、结果、模板、正文和 PDF 的 canonical 路径必须在状态中登记并带 SHA-256。

## 严格流程

```text
01-cumcm-doctor
→ 02-cumcm-brainstorm
→ 03-cumcm-project-start
→ 04-cumcm-modeling
→ G1-model-confirmation
→ 05-cumcm-coding-visual
→ 06-cumcm-result-mvp
→ G2-result-confirmation
→ 07-cumcm-drawio（按需）
→ 08-cumcm-template
→ 09-cumcm-writing
→ 10-cumcm-latex
→ 11-cumcm-verify
→ 12-cumcm-docx（按需）
→ 13-cumcm-paper-review
```

不得跳过阶段、自动跨过 G1/G2，或因为下游 skill 自带旧编排文字而递归调用下游。可选阶段必须写入 `SKIPPED` 记录和原因，不能从状态中消失。

## 每次调度协议

1. 读取状态、注册表、当前阶段 packet 和所有 `HELD` 锁。
2. 校验 `workflow_id`、`current_phase`、`run_id`、阶段 status、门禁状态和 canonical 哈希。
3. 若状态不存在，先运行 `scripts/init_workflow_state.py`；不得手写半份状态。
4. 若当前阶段不满足 entry_conditions，写入阻塞原因并停止，不调用 agent。
5. 明确目标 agent 的 read-only 与 writable 范围。写 canonical 文件前必须取得 owner 锁。
6. 调度时为该轮生成或沿用 `run_id`，把输入哈希写进 phase_history。
7. 合并输出前检查输出路径属于该 agent owner，检查哈希和报告状态，再更新状态。
8. 释放锁并登记 output_sha256；锁冲突、输入哈希漂移或 owner 不一致时停止合并。

推荐命令接口：

```text
python scripts/init_workflow_state.py --project-root <project> --project-id <id>
python scripts/validate_workflow_state.py --state <project>/reports/WORKFLOW_STATE.json --registry <project>/shared/PHASE_REGISTRY.json
python scripts/manage_write_lock.py acquire --project-root <project> --path <canonical> --owner-agent <agent> --run-id <run> --reason <reason>
python scripts/manage_write_lock.py release --project-root <project> --path <canonical> --owner-agent <agent> --run-id <run> --reason <reason> --lock-id <lock>
python scripts/update_gate.py --state <project>/reports/WORKFLOW_STATE.json --gate g1 --status confirmed --decision-id <id> --packet-sha256 <sha> --user-text "..."
```

这些脚本只负责确定性状态操作，不替代总控的业务判断；任何用户确认都必须由总控依据用户原文调用 `update_gate.py`。

## G1/G2 硬暂停

到达 `G1-model-confirmation` 或 `G2-result-confirmation` 时：

- 只输出确认包和需要用户判断的明确问题；
- 将 `stage_status` 设为 `WAITING_USER`，将对应 gate 设为 `PENDING`；
- 停止当前轮次，不调用任何下游 agent；
- 不把“继续”“可以”“好的”等泛化回应当作确认；
- 只有用户原文明确覆盖范围、关键选择、数字/异常/限制并允许继续时，才写入决策台账；
- 确认后的 packet SHA-256 必须与状态一致，否则门禁立即失效。

题意、模型、约束、代码、数据口径、核心数字或验证证据变化时，必须先登记失效，再重新运行受影响阶段和门禁。

## 并行边界

事实链默认串行。只有注册表明确允许且不写同一 canonical 文件的审查任务才可以并行：

- G2 确认后，`07-cumcm-drawio` 和 `08-cumcm-template` 可并行；
- `11-cumcm-verify` 内部的代码审计和 PDF 视觉审计可并行；
- 建模、代码、结果 MVP、正文和 PDF 编译不得并行写同一事实源。

并行 agent 只提交报告或候选补丁，总控统一合并。

## 失败回退

| 失败类型 | 回退阶段 |
|---|---|
| 环境、依赖、编译工具 | `01-cumcm-doctor` |
| 需求范围和执行方案 | `02-cumcm-brainstorm` |
| 路径、版本、题目范围 | `03-cumcm-project-start` |
| 题意、变量、模型、约束 | `04-cumcm-modeling` |
| 代码、数据、运行、结果 | `05-cumcm-coding-visual` |
| 结果合理性、证据、异常 | `06-cumcm-result-mvp` |
| 技术图 | `07-cumcm-drawio` |
| 模板和版式基线 | `08-cumcm-template` |
| 正文、蓝图、引用 | `09-cumcm-writing` |
| XeLaTeX、交叉引用、页面 | `10-cumcm-latex` |
| 综合证据、提交包、复现 | `11-cumcm-verify` |
| Word 协作回流 | `12-cumcm-docx` |
| 最终论文审阅 | `13-cumcm-paper-review` |

修复后必须创建新 run 或明确的重跑记录，不能直接把旧 `FAIL` 改成 `PASS`。

## 完成条件

只有 `11-cumcm-verify` 为 `PASS`，按合同完成可选 DOCX，且 `13-cumcm-paper-review` 已完成最终只读审阅，才可以将 `delivery_status` 设为 `FULL_PASS`。本地 skill 项目自身在发布前还必须通过结构、状态、锁、门禁和迁移资产回归测试。
