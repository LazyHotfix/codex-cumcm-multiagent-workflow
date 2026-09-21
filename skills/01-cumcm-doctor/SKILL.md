---
name: 01-cumcm-doctor
description: "检查高教杯项目的 math Conda 环境、Python 依赖、XeLaTeX 和图形工具，记录可复现的环境报告。"
---

# 01 高教杯环境预检

## 阶段合同

```yaml
phase_id: 01-cumcm-doctor
display_name: 国赛环境预检
owner_agent: doctor-agent
entry_conditions:
  - 项目根目录已由总控确定
  - 当前没有未处理的写锁冲突
inputs:
  - 项目根目录与当前操作系统信息
  - 已有 requirements.txt、environment.yml、run_manifest.json（若存在）
actions:
  - 只读检查 Conda、math 环境、Python 包、XeLaTeX、PDF 栅格化和 DrawIO
  - 记录解释器路径、版本、命令、返回码和时间
outputs:
  - reports/ENVIRONMENT_REPORT.md
  - reports/environment_check.json
  - reports/environment_setup.log（仅记录已授权安装）
exit_conditions:
  - 必需工具状态、缺失项、替代方案和阻塞项均已记录
failure_return:
  - 环境不可用：保持 BLOCKED，修复后重跑本阶段
writable_paths:
  - reports/ENVIRONMENT_REPORT.md
  - reports/environment_check.json
  - reports/environment_setup.log
read_only_paths:
  - 题面、附件、代码、模板和已有结果
invalidates:
  - 环境或解释器变化使受影响的代码结果、复现和验收失效
user_gate: false
```

## 执行规则

1. 这是总控的第一阶段；不得调用 brainstorm、建模、代码或写作。
2. Python 优先检查 conda run -n math python ...。系统找不到 Conda 时记录为 BLOCKED，不自行创建 .conda、venv 或替代环境。
3. 检查项目实际需要的 numpy、pandas、scipy、matplotlib、scikit-learn、openpyxl 及题目使用的求解器和读取包；也检查 xelatex、PDF 渲染器和 DrawIO。
4. 缺少项目 Python 包时，只能在用户已经允许安装的前提下写入 math 环境；安装命令、版本、解释器路径、返回码和时间必须写入日志。系统工具、管理员权限和 Conda 本身缺失时不得假装安装完成。
5. 不能把普通 Python 能运行当作 math 环境通过；报告必须给出实际命令和 stdout/stderr 摘要。
6. 输出 PASS、REVISE 或 BLOCKED 的原因，但不修改 WORKFLOW_STATE 或 DECISION_LEDGER；由 orchestrator 合并阶段状态。

## 交接

只有 reports/ENVIRONMENT_REPORT.md 明确列出阻塞项已关闭，orchestrator 才能调度 02-cumcm-brainstorm。
