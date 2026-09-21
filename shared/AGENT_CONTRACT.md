# CUMCM 专业智能体合同

每个专业 skill 都必须把本合同当作最低接口。具体阶段可以增加约束，但不得放宽以下规则。

## 必填元数据

阶段说明必须能回答：

- `phase_id`、`owner_agent`、`run_id`；
- `entry_conditions`：调用前必须满足什么；
- `inputs`：读取哪些事实源；
- `outputs`：生成哪些机器可读和人读交付物；
- `exit_conditions`：什么情况下才算阶段完成；
- `failure_return`：失败退回哪个阶段以及触发什么失效；
- `writable_paths` 与 `read_only_paths`；
- `invalidates`：本阶段改变什么时必须让哪些下游状态失效。

## 通用运行规则

1. 开始前读取 `reports/WORKFLOW_STATE.json`、当前 `run_id` 和待处理决策。
2. 只读取合同允许的输入，只写入自己的 owner 路径；不得覆盖原始题面、原始附件、旧版本或其他 agent 的 canonical 文件。
3. 修改 canonical 文件前读取现有 SHA-256、登记写锁，修改后登记新 SHA-256 和受影响资产。
4. 所有输出必须带 `run_id`、来源路径、生成时间、阶段和状态；核心数字必须能回到结果文件或题面。
5. 专业 agent 不得自行推进下游 skill，不得代替用户确认 G1/G2，不得把“继续”“可以”“好的”当作门禁确认。
6. 失败时写明 `status`、`severity`、`owner`、`evidence`、`return_phase` 和建议修复，不得只输出自然语言抱怨。
7. 结果生成、正文嵌入和最终验收是不同状态：`generated` 不等于 `embedded`，`embedded` 不等于 `verified`。
8. 任何模型、数据口径、约束、代码核心结果、模板类文件或锁定正文的变化，都必须按依赖传播使旧门禁和受影响资产失效。

## 退出状态

允许的通用状态为：`PASS`、`REVISE`、`BLOCKED`、`WAITING_USER`、`generated`、`embedded`、`verified`、`SKIPPED`。阶段若使用专有状态，必须在输出报告中给出到上述状态的映射。
