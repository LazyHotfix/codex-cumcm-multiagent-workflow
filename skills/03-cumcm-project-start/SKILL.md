---
name: 03-cumcm-project-start
description: "恢复高教杯项目现场，审计版本、路径、题目范围、用户决策和交付物合同。"
---

# 高教杯项目现场恢复与范围登记

## 阶段合同（机器接口）

- phase_id: 03-cumcm-project-start；display_name: 项目现场恢复；owner_agent: project-start-agent。
- entry_conditions: 02 范围确认已由总控记录；项目根目录可读。
- inputs: 题面、附件、旧版本、状态报告、执行范围 packet。
- outputs: reports/PROBLEM_SCOPE.csv、VERSION_AUDIT.csv、ARTIFACT_INVENTORY.csv、PROJECT_START_PACKET.json。
- exit_conditions: 唯一 canonical 路径、问题范围、版本标签和缺失项已登记。
- failure_return: 路径/版本冲突返回 03；题意问题返回 04；不调用下游。
- writable_paths: reports/PROBLEM_SCOPE.csv、reports/VERSION_AUDIT.csv、reports/ARTIFACT_INVENTORY.csv、reports/PROJECT_START_PACKET.json、plan.md、todo.md。
- read_only_paths: 原始题面、附件、旧代码、旧论文、模板原件。
- invalidates: 项目根目录、题目范围或版本事实变化使 04 及下游全部失效。
- user_gate: 开工确认由 orchestrator 管理。
## 本地多智能体合同
- owner_agent：project-start-agent；
- 只负责现场恢复、版本审计、范围登记和项目合同；
- 不调用下游 skill，不跳过用户开工确认；
- 必须读写 reports/WORKFLOW_STATE.json 和决策台账；
- 退出状态：ready_for_analysis 或 BLOCKED。

本 skill 只负责恢复项目现场、登记版本和范围、确定 canonical 路径并输出项目启动包。它不编排、不调用后续专业 skill；所有阶段推进、用户门禁和全局状态由 00-cumcm-orchestrator 管理。

## 固定边界

- 本入口只编排全国大学生数学建模竞赛（CUMCM）流程，不混入华数杯、MCM/ICM 或其他比赛模板和评分规则。
- 国赛主写作固定使用用户自制 `zh/cumcm-structured-latex` 模板族及其 `cumcmthesis.cls`；参考工程入口为用户确认的 `main.tex`。除非用户提供新模板，不再询问 Typst/LaTeX。
- 开工审计必须读取模板工程的 `TEMPLATE_VERSION.json`，记录模板 ID、`cumcmthesis.cls`/`main.tex` 哈希和实际路径；哈希不匹配时停止写作入口并报告。
- 主流模型目录优先读取 `skills/04-cumcm-modeling/references/mainstream-model-catalog\CATALOG_VERSION.json` 及同目录文件；桌面目录仅为用户维护备份。目录版本或哈希不匹配时停止模型选型并报告。
- `09-cumcm-writing` 是国赛写作主入口；`10-cumcm-latex` 只提供通用 LaTeX 基础支持。
- `06-cumcm-result-mvp` 只在第一次正式论文写作前运行：承接 `05-cumcm-coding-visual` 的结果，生成最小逐问论文和 `result_ai_review/`，必须通过 AI 评审并取得用户 G2 确认后，才能进入 `07-cumcm-drawio` 和 `09-cumcm-writing`。
- `05-cumcm-coding-visual` 可在当前项目 Conda/Python 环境中直接安装缺失的项目依赖；安装命令、版本和结果必须记录到环境说明、日志和 `run_manifest.json`。系统级工具和管理员权限安装仍由 `doctor` 或单独授权处理。
- 不覆盖题面、原始附件、模板原件或已有版本；修复项目必须在独立版本目录工作。

## 启动模式

先判定并记录以下模式之一：

- `new_project`：从题面和附件开始。
- `repair_project`：已有论文、代码、结果或 PDF；先审计证据和版本口径，再决定补算、重写或仅修复版式。
- `resume_project`：前序阶段已有明确产物和状态，用户要求从指定阶段继续；必须先验证该阶段产物仍与真实文件和最近运行日志一致。

无论模式如何，启动时都必须完成三方现场核对：状态文件（`AIREADE.md`、`README.md`、`plan.md`、`todo.md`） vs 目录真实文件 vs 最近运行日志/文件修改时间。写作前必须完成“题目问题—模型—结果资产—论文位置”映射。至少统计：顶层问题数；每问模型、验证方法和锁定口径；结果文件数量/类型；每问表格、图表、参数、预测、敏感性资产；当前论文每问的标题、公式、表格、图表和定量结论数量；缺失证据、历史口径冲突和不可复现风险。

## 首轮需求确认

只询问会改变交付的事项：正式题面与附件、老师模板/评分细则、做全部问题还是指定问题、身份字段、是否允许联网检索。执行模式默认模式 A；若用户明确选择模式 B，整个项目保持模式 B，不中途切换。不要把可由文件发现的信息再次询问。

## 统一交付物合同与状态机

启动审计与版本隔离：先确定唯一的当前项目根目录、论文目录、代码目录、结果目录、图表目录、参考文献目录、题面目录、模板目录和输出 PDF 路径；所有下游 skill 必须使用这组路径，不得各自猜测。创建或更新 `reports/PROBLEM_SCOPE.csv`、`reports/VERSION_AUDIT.csv`、`reports/ARTIFACT_INVENTORY.csv` 和 `reports/USER_DECISIONS.md（由 orchestrator 从 DECISION_LEDGER.yaml 投影）`。目录名含 `_v1`、`final` 或文件名为 `main.pdf` 不能自动证明其为当前版本。若当前代码、机器可读结果与旧报告/PDF 冲突，代码和机器可读结果优先，旧资产保留并标记 `obsolete`；差异写入 `reports/OLD_VERSION_DIFF.md`，受影响结果退回重新验证。

所有阶段围绕同一份交付物合同工作。文件可以在早期为空壳或处于 `planned`，但不能靠口头约定替代；阶段交接时必须更新状态、来源和责任阶段。

必须交付：

```text
README.md  AIREADE.md  plan.md  todo.md
paper/  code/  results/  figures/
mvp/  result_ai_review/
references/references.bib
references/REFERENCE_INDEX.csv
reports/ANALYSIS_MODELING_REPORT.md
reports/RESULTS_REPORT.md
reports/TECHNICAL_DECISIONS.md
reports/RESULTS_INDEX.csv
reports/VERIFY_REPORT.md
reports/PROBLEM_SCOPE.csv
reports/VERSION_AUDIT.csv
reports/ARTIFACT_INVENTORY.csv
reports/USER_DECISIONS.md（由 orchestrator 从 DECISION_LEDGER.yaml 投影）
```

生成 PDF 后必须有 `reports/LAYOUT_AUDIT.csv`；有 Python 依赖时必须有 `code/requirements.txt` 或等价环境说明；所有正式项目必须有 `code/run_manifest.json`。缓存、临时输出、旧版本结果和未登记的孤儿资产不得进入最终交付目录。

所有核心结果（主要表、数据图、技术图、检验和敏感性证据）统一使用：

```text
planned → generated → embedded → verified
             ↘ blocked
```

`04-cumcm-modeling` 创建 `planned`，`05-cumcm-coding-visual`/`07-cumcm-drawio` 生成 `generated`，`09-cumcm-writing` 更新 `embedded`，`11-cumcm-verify` 更新 `verified`。结果还可以标记 `needs_confirmation` 或 `obsolete`。`generated` 只表示资产已生成，不表示本题合理性已通过；3.5 的 G2 是进入技术图和正式写作的必要条件。模型、数据口径、代码或论文数字变化时，按资产依赖范围使受影响结果退回并重新验收，不能沿用旧状态。

## 必须维护的文件

根目录必须有：

```text
README.md       # 面向用户
AIREADE.md      # 面向后续 AI 的短状态记忆
plan.md         # 总体计划和阶段边界
todo.md         # 当前待办与门禁状态
reports/
  ANALYSIS_MODELING_REPORT.md
  RESULTS_REPORT.md
  DECISIONS.md
  VERIFY_REPORT.md
  RESULTS_INDEX.csv
  LAYOUT_AUDIT.csv       # 生成 PDF 后必须存在
  PROBLEM_SCOPE.csv
  VERSION_AUDIT.csv
  ARTIFACT_INVENTORY.csv
  USER_DECISIONS.md
```

`AIREADE.md` 合并当前阶段、已完成项、锁定模型、关键假设、警告、下一步、路径、最近命令和等待决策。默认不生成 `CHECKPOINT.md`、`NEXT_PROMPT.md`、`SOLUTION_NOTEBOOK.md` 或重复矩阵；只有跨会话硬中断且无法用 AIREADE 恢复时才临时生成。

## 计划与阶段

`plan.md` 固定记录：CUMCM 范围、模式、模板路径、交付目标、目录结构、风险和阶段接口。`todo.md` 使用可勾选门禁：

```text
开工审计 → 题面/数据审计 → 每问证据包 → G1 模型确认 → 代码与结果
→ 3.5 MVP/AI 结果评审 → G2 结果确认 → 数据图/技术图
→ CUMCM 结构化写作 → 完整代码附录 → 结果覆盖验收 → 页面级验收 → 交付
```

阶段调用顺序：

| 阶段 | Skill | 硬产物 |
|---|---|---|
| 分析与接口 | `04-cumcm-modeling` | 最终建模报告、每问证据包、候选评分与实现接口 |
| 编程与数据图 | `05-cumcm-coding-visual` | 真实代码、结果表、PDF/PNG 图、源数据、结果索引 |
| 结果 MVP 与 AI 评审 | `06-cumcm-result-mvp` | `mvp/`、`result_ai_review/`、G2 结果确认 |
| 非数据图 | `07-cumcm-drawio` | 按需生成的 `.drawio`、PDF 和记录 |
| 国赛写作 | `09-cumcm-writing` | `zh/cumcm-structured-latex` LaTeX 工程、论文、完整代码附录 |
| 验收 | `11-cumcm-verify` | 失败闭环验收报告、页面审计和 PASS/FAIL |

## 模式 A 的候选模型处理

每问生成 2--3 个真实可行候选方案，按题意适配性、数据适配性、适用前提、验证性、解释性、复现性和计算稳定性评分并记录在 `reports/TECHNICAL_DECISIONS.md`。必须向用户展示候选、排序、适合与不适合原因、透明基线和验证计划，并暂停等待确认；确认后才写入锁定模型。失败尝试不得删除，必须记录原因和替代口径。普通参数和排版细节仍不需要反复请求确认。

## 交付前入口检查

进入写作前确认：建模报告为锁定后的最终版本；每问证据闭环矩阵均有代码任务和结果资产；`RESULTS_INDEX.csv` 已建立并包含所有 `planned` 结果；`06-cumcm-result-mvp` 已生成 MVP 和 AI 评审；MVP 与 AI 评审总体 PASS；用户 G2 确认已记录；旧口径已标废弃；模板工程可复制；参考文献库和引用索引已建立；代码附录文件集合可从最终交付目录确定。缺任一项，先回到责任阶段，不得直接写正式论文。

最终交付前确认：所有核心结果状态为 `verified`；`REFERENCE_INDEX.csv` 与正文引用双向一致；`run_manifest.json` 中的正式命令可执行；`LAYOUT_AUDIT.csv` 和 `VERIFY_REPORT.md` 已完成。
