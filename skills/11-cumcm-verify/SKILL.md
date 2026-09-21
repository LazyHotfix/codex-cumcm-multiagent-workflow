---
name: 11-cumcm-verify
description: "验收高教杯题意、证据、代码、结果、论文、PDF、版本和最终提交包。"
---

# 高教杯验证与失败闭环验收

## 阶段合同（机器接口）

- phase_id: 11-cumcm-verify；display_name: 证据链与提交验收；owner_agent: verify-agent。
- entry_conditions: 10 PDF 和日志存在；核心结果、引用、代码和模板索引可读。
- inputs: 题面、G1/G2、模型、代码、结果、论文、PDF、模板、引用和提交包。
- outputs: reports/VERIFY_REPORT.md、SUBMISSION_MANIFEST.csv、修复单和复现日志。
- exit_conditions: 所有 critical/high 关闭，代码核心结果可重现，PDF 页面、证据链、引用和提交包通过；phase_result=PASS。
- failure_return: 只输出责任回退和修复单，不直接改其他 owner 的 canonical 内容。
- writable_paths: reports/VERIFY_REPORT.md、reports/SUBMISSION_MANIFEST.csv、reports/REPAIR_QUEUE.csv。
- read_only_paths: code/、results/、paper/、figures/、模板、台账和题面。
- invalidates: 任何事实源变化使本阶段 PASS 失效并要求重新验收。
- user_gate: true（交付确认由 orchestrator 管理；不是 G1/G2）。
## 本地多智能体合同
- owner_agent：verify-agent；
- 负责最终证据、版本、代码、PDF 和提交包验收；
- 编译成功不等于 PASS；
- FAIL 必须指定责任回退阶段并重新验收；
- 退出状态：PASS、FAIL 或 BLOCKED。

本 skill 是国赛最后质量门禁。它不重新设计模型，但必须发现问题并把任务退回正确阶段；可直接修复的小范围排版或路径错误可以修复后重跑。只有所有硬门禁通过，才在 `reports/VERIFY_REPORT.md` 写 `PASS`。

## 输入

根据实际工程读取：论文入口、章节、`PAPER_BLUEPRINT.md`、模板类文件、模板工程的 `TEMPLATE_VERSION.json`、`reports/ANALYSIS_MODELING_REPORT.md`、`reports/RESULTS_REPORT.md`、`reports/DECISIONS.md`、`reports/RESULTS_INDEX.csv`、`reports/LAYOUT_AUDIT.csv`、`references/references.bib`、`references/REFERENCE_INDEX.csv`、`results/`、`figures/`、最终 `code/`、`code/run_manifest.json`、README、AIREADE、题面和附件。若项目已有明确的其他路径，以实际路径为准，但必须在验收报告记录实际路径。

若项目存在，还必须读取 `reports/PROBLEM_SCOPE.csv`、`reports/DATA_STRUCTURE_AUDIT.csv`、`reports/INDEX_SCOPE_MAP.csv`、`reports/CONSTRAINT_COVERAGE.csv`、`reports/MODEL_CODE_MAPPING.csv`、`reports/OLD_VERSION_DIFF.md`、`code/environment_setup.log`、`mvp/` 和 `result_ai_review/`。这些文件用于核对题意范围、维度、约束来源、模型—代码映射、版本冲突、环境安装和 G2 结果审查；文件缺失时按其是否为当前项目必需资产判定 FAIL 或 WARN，不能用论文叙述替代机器记录。

## 门禁一：证据包与结果覆盖

正式论文验收前必须确认 `06-cumcm-result-mvp` 已完成：`mvp/` 和 `result_ai_review/` 文件存在，`AI_REVIEW_SUMMARY.md` 为 `PASS`，每个小问的实现/合理性/证据三层状态均为 `PASS`，且 `reports/MVP_DECISION.md` 有用户 G2 确认。缺任一项为 `FAIL`，不能以正式论文已经生成代替结果确认。

逐问题检查 `ANALYSIS_MODELING_REPORT.md` 中的证据闭环矩阵是否都有对应资产。读取 `RESULTS_INDEX.csv`，对每个核心结果验证：

```text
原始数据 → 代码入口 → 结果文件 → 表/图源数据 → 论文位置
→ 正文引用 → 现象解释 → 问题小结
```

以下任一情况为 `FAIL`：

- 核心结果没有 `result_id` 或来源；
- 核心结果状态不是 `embedded`/`verified`；
- 结果有论文位置但正文没有引用和解释；
- 某问缺少主要结果表、主要结果图或等价证据；
- 结果目录存在大量未解释的核心孤儿资产；
- 论文使用的数字无法回到当前版本结果；
- 旧口径、新口径或不同版本结果混用。

对每个 `problem_id` 另外核对题意输出、模型、关键假设、验证方法、主要表/图或等价证据、正文定量结论和问题小结是否全部存在。任一问题缺少闭环项，均为 `FAIL`，不能用其他问题的结果补足。

此外，验收必须读取 `result_ai_review/AI_REVIEW_ISSUES.csv` 和 `EVIDENCE_TRACE.csv`，确认没有未关闭的 `critical`/`high` 问题，且每个核心结论都能从题面要求追溯到锁定模型、代码入口、结果文件、验证文件和正文位置。若结果仅“按模型算出”但没有本题边界、约束、守恒、基线、单调性或扰动证据，不能判定结果合理；应退回 `06-cumcm-result-mvp`、`05-cumcm-coding-visual` 或 `04-cumcm-modeling`。

## 门禁二：国赛结构与写作质量

检查问题数量与题面一致；每问都有“问题 X 的建模与求解”和总起段。A–E 是强制论证功能而不是固定标题：读取 `PAPER_BLUEPRINT.md` 中的 `function_tags`，确认 A（具体分析）、B（模型准备）、C（算法选择）、D（模型建立/求解/结果/验证）、E（问题小结）均有正文语义覆盖。标题可按题型自适应，不因未出现“问题分析”等固定字符串而判错；但不能用标题灵活掩盖功能缺失。检查摘要是否为“背景框架段 + 每问独立段 + 创新段”。检查：

- 公式后的符号和单位解释；
- 图表前引入句和图表后解释；
- 模型选择比较及理由；
- 缺失、异常、极端值和敏感性口径；
- 结论是否直接回答题意而非只罗列方法。

每问只有几段文字、一个公式和一张图，或没有主要结果表时，判定 `FAIL`，不能只给 `WARN`。

正文页数、公式数量和图表数量只作为密度提示，不得脱离题型、证据需求和实际排版机械判定 PASS/FAIL。若采用自适应小节标题，必须以 `PAPER_BLUEPRINT.md` 的 `function_tags` 和正文语义核对 A–E 覆盖；不能只通过搜索固定标题字符串判定结构完整。

## 门禁三：图表与页面

检查每张图的真实文件、caption、编号、正文引用、数据来源和解释。生成 `LAYOUT_AUDIT.csv`，表头至少为：

```csv
page,object_id,object_type,source_file,caption,body_reference,content_ratio,standalone_page,duplicate_title,readable,overflow,whitespace,action,status
```

必须使用可用工具将 PDF 栅格化并逐页检查；不能用少量抽查代替整体页面审计。硬失败包括：裁切、越界、重叠、乱码、图表不可读、无理由单图占页、正文异常大块空白、重复大标题、宽表截断、参考文献或附录分页错误。

页面统计必须分开记录摘要、正文、参考文献和附录页数；正文密度是质量提示，不以固定页数、公式数量或图表数量机械判定通过。工具不可用时，必须在 `VERIFY_REPORT.md` 记录原计划、失败原因、替代工具、覆盖范围和未完成检查，不能假装已完成。

## 门禁四：模板、引用和摘要

- CUMCM 必须使用用户确认的 `zh/cumcm-structured-latex` / `cumcmthesis.cls`；
- `TEMPLATE_VERSION.json` 中登记的模板 ID 与类文件、入口文件哈希必须和实际工程一致；不一致为 FAIL，不能沿用旧版验收；
- XeLaTeX 至少连续编译两遍，无致命错误、未定义引用、缺图或明显 `Overfull \\hbox`；
- 参考文献从独立新页开始，正文必须有真实上标引用，不能只在文末列文献；
- 引用命令以模板实际定义和渲染结果为准；若模板规定 `\upcite{}`/`\supercite{}`，正文应使用对应上标命令，不能仅凭字符串搜索机械判错；
- `REFERENCE_INDEX.csv` 中所有 `used` 文献都能在正文定位，正文每个引用都能回到 `references.bib` 和来源记录；未定义引用、孤立文献、缺少方法依据的关键模型均为 `FAIL`；
- 附录在参考文献后再次独立分页；
- 摘要问题段不能合并或拆分，数字必须来自结果文件；
- 正文不得泄露内部 skill 名称、报告路径、临时目录、TODO 或占位符。

检查 `RESULTS_INDEX.csv` 的状态流转：写作前核心结果为 `generated`，写作后为 `embedded`，只有本验收完成来源、数字、正文和页面核对后才能改为 `verified`。发现正文、代码、数据或口径变化时，按资产依赖范围使旧的 `embedded`/`verified` 退回并重新验收；纯错别字不要求重新运行模型，但仍需重新检查受影响页面和引用。替换图片、表格样式或章节结构时，至少重新检查对应结果对象、正文位置、交叉引用和页面。

引用验收通过后，将 `REFERENCE_INDEX.csv` 中实际出现在正文且来源核对无误的条目标记为 `verified`；未使用条目标记为 `not_used`，不得以“参考过”代替正文引用。

## 门禁五：完整代码附录与复现

验证：

```text
附录文件集合 = 最终交付代码文件集合
附录代码内容 = 最终交付代码内容
结构图节点 = 实际代码/输出节点
运行命令 = 真实可执行命令
```

附录缺少结构图、文件清单、作用/输入/输出/命令、真实 `lstinputlisting` 或 `run_all.py` 时为 `FAIL`。在干净临时目录按 `code/run_manifest.json` 运行总入口，至少复现数据审计、核心结果和图表；环境文件、输入文件哈希、命令、依赖安装日志或输出目录缺失时为 `FAIL`。检查 `environment_setup.log` 是否记录自动安装的项目依赖、解释器路径、环境名、版本和返回码；环境修复后必须重新运行受影响结果。失败必须退回 `05-cumcm-coding-visual` 或环境处理，不能用“附件另有代码”代替。

## 门禁六：下游审查兼容

确保 `README.md` 能快速定位 PDF、LaTeX、代码、结果、报告、题面和复现命令；`13-cumcm-paper-review` 可以仅凭交付包和索引复核：题目对应关系、数据处理、公式、图表证据链、引用、视觉质量、代码一致性和限制。审查所需的内部状态不能泄露到论文正文。

## 失败闭环

`VERIFY_REPORT.md` 必须写明每项 PASS/FAIL/WARN、证据、责任阶段和下一步。失败分类：

| 失败类型 | 退回阶段 |
|---|---|
| 题意、变量、模型或验证缺口 | `04-cumcm-modeling` |
| 结果、表格、图表、日志或索引缺口 | `05-cumcm-coding-visual` |
| 技术图依赖、节点或导出缺口 | `07-cumcm-drawio` |
| 章节、正文解释、摘要或附录缺口 | `09-cumcm-writing` |
| 环境、编译或工具缺口 | `doctor`/对应阶段 |

修复后必须重新运行受影响门禁；不能把旧版 PASS 沿用到新版本。`PASS` 只在所有硬错误关闭、结果覆盖完整、代码可复现、LaTeX 编译通过且页面级检查完成后产生。
