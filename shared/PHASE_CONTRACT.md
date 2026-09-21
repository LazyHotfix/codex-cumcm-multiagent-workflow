# 阶段合同

每个本地 skill 的 SKILL.md 必须显式声明以下字段，不能只散落在叙述中：

```yaml
phase_id: 00-example
display_name: example
owner_agent: example-agent
entry_conditions: []
inputs: []
actions: []
outputs: []
exit_conditions: []
failure_return: []
writable_paths: []
read_only_paths: []
invalidates: []
user_gate: false
```

## 状态分层

- stage_status 只表示当前阶段生命周期：NOT_STARTED、RUNNING、WAITING_USER、BLOCKED、PASS、FAIL。
- phase_result 表示该阶段的业务结果，例如 candidate_pending、generated、READY_FOR_LATEX、COMPILED、REVISE。
- asset.status 表示资产生命周期：planned、generated、needs_confirmation、embedded、verified、obsolete、blocked。
- g1.status/g2.status 表示门禁状态，只有总控可从 PENDING 变为 CONFIRMED。
- delivery_status 表示全局交付状态，不得当作阶段 PASS。

## 硬规则

1. 未满足 entry_conditions 不得调用；未满足 exit_conditions 不得进入下一阶段。
2. G1/G2 到达后必须停止当前轮次，专业 agent 只输出确认包；用户确认由 orchestrator 写入唯一事实源 reports/DECISION_LEDGER.yaml。
3. 专业 agent 不得自行调用下游阶段，不得自行写用户确认或全局状态门禁。
4. 修改 canonical 文件前必须取得 owner 写锁；输出必须包含 run_id、输入哈希、输出哈希和状态。
5. 任何模型、数据、结果、模板、公式或事实数字变化，都必须在 reports/INVALIDATION_LOG.csv 登记失效传播并重跑受影响门禁。
6. PASS 只表示当前阶段通过，不代表最终论文通过。
