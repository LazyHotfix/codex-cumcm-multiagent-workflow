# 文件所有权和写锁

同一 canonical 文件同一时刻只能有一个 owner。专业 agent 不得修改其他 agent 的 canonical 文件，也不得绕过总控写用户门禁。

## Canonical owner

- `reports/WORKFLOW_STATE.json`：`orchestrator`
- `reports/DECISION_LEDGER.yaml`：`orchestrator`，唯一用户确认事实源
- `reports/USER_DECISIONS.md`：`orchestrator` 生成的人读视图，不是事实源
- `reports/MVP_DECISION.md`：`orchestrator` 生成的人读 G2 视图，不是事实源
- `reports/TECHNICAL_DECISIONS.md`：各阶段提交、`orchestrator` 合并，不能记录用户门禁
- `paper/PAPER_BLUEPRINT.md` 和正文 section：`writing-agent`
- `paper/main.pdf`、编译日志和页面渲染：`latex-agent`
- `code/`、`results/`、数据图和结果表：`coding-agent`
- `figures/technical/`：`figure-agent`
- `skills/08-cumcm-template/templates/` 与 `template_lock.json`：`template-agent`
- `reports/VERIFY_REPORT.md` 和提交包清单：`verify-agent`
- DOCX 协作副本及渲染物：`docx-agent`
- 最终审阅报告：`paper-review-agent`，默认只读

## 用户决策事实源

所有 G1、G2、开工确认和交付确认都只写入 `reports/DECISION_LEDGER.yaml`。其他 Markdown 文件只能由总控根据台账生成，不能被专业 agent 直接当作确认依据。
技术阶段可在 `reports/TECHNICAL_DECISIONS.md` 提交技术决策，但必须引用 `decision_id`，不能改变门禁状态。

## 写锁协议

修改前：
1. 读取目标文件当前 SHA-256。
2. 检查 `reports/locks/` 是否已有 `HELD` 锁。
3. 创建 `lock_id`，登记 owner、reason、run_id 和 input_sha256。
4. 修改后计算 output_sha256，更新 WORKFLOW_STATE 中的资产哈希并释放锁。
5. 如果哈希与 input_sha256 不一致或出现两个 owner，停止合并，交给 orchestrator。

锁文件格式见 `shared/WRITE_LOCK.schema.json`。锁只保护 canonical 写入，不代表内容已经通过阶段验收。
