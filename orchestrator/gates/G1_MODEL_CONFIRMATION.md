# G1 模型确认门

进入：04-cumcm-modeling 已输出候选模型、适用性、基线、验证计划和风险。

必须向用户展示：

- 每个纳入问题的候选模型；
- 选择理由和不适用原因；
- 关键假设和约束；
- 透明基线；
- 验证计划；
- 模型边界。

只有用户明确确认问题范围、主模型、主要假设、主要约束、基线并允许进入代码，才可将 model_status 设为 locked。

到达本门必须停止当前轮次，不得调用 05-cumcm-coding-visual。

用户确认原文写入 reports/DECISION_LEDGER.yaml 或 reports/USER_DECISIONS.md。

模型、题意、目标或关键约束变化时，旧 G1 立即失效。
