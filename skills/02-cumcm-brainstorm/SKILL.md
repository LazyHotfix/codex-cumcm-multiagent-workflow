---
name: 02-cumcm-brainstorm
description: "在高教杯建模前确认题目范围、交付形式、时间预算、权限边界和执行方案，并等待用户明确批准。"
---

# 02 高教杯任务范围与执行方案

## 阶段合同

```yaml
phase_id: 02-cumcm-brainstorm
display_name: 国赛任务范围确认
owner_agent: brainstorm-agent
entry_conditions:
  - 01-cumcm-doctor 已输出环境报告
  - 环境报告没有未解释的硬阻塞，或用户已明确接受替代方案
inputs:
  - reports/ENVIRONMENT_REPORT.md
  - 用户提供的项目目录、题面、附件和已有交付物
actions:
  - 确认题目范围、是否完成全部顶层问题、截止时间和运行预算
  - 确认模板、允许的安装/联网权限、作者信息和交付格式
  - 给出可执行的阶段顺序和风险清单
outputs:
  - reports/BRAINSTORM_PACKET.json
  - reports/EXECUTION_SCOPE.md
exit_conditions:
  - 已列出必需信息、默认值、阻塞项和用户需要确认的执行边界
failure_return:
  - 信息不足：WAITING_USER；范围冲突：返回 02 修订
writable_paths:
  - reports/BRAINSTORM_PACKET.json
  - reports/EXECUTION_SCOPE.md
read_only_paths:
  - 题面、附件、模板、旧代码、旧论文和环境报告
invalidates:
  - 范围、模板或交付形式变化使 project-start 及下游计划失效
user_gate: true
```

## 规则

1. 只问会改变工作范围或交付的事项；能从文件确定的信息不要重复询问。
2. 默认使用中文、完成全部顶层问题、优先 LaTeX/PDF、按需生成 DOCX；默认模板和作者信息必须写入 packet，不能藏在对话上下文中。
3. 这个用户门是执行范围批准，不是 G1 模型确认。用户没有明确批准前，orchestrator 不能进入 03-cumcm-project-start。
4. 不选择模型、不读取主流模型目录作结论、不写代码、不编译论文，也不修改任何项目 canonical 事实源。
5. “确认范围”的有效回复必须说明范围、截止时间/运行预算和交付目标；“继续”“可以”“好的”不能单独解除门禁。
6. 专业 agent 只输出 packet；由 orchestrator 将用户原文写入 reports/DECISION_LEDGER.yaml，并投影到人读报告。

## 交接

只有 scope_confirmation 已由 orchestrator 记录为 CONFIRMED，才允许调用 03-cumcm-project-start。
