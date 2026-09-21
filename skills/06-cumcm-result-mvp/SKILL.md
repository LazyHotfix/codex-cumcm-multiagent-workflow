---
name: 06-cumcm-result-mvp
description: "生成逐问高教杯结果 MVP，审查实现一致性、题目合理性和证据可用性。"
---

# 高教杯 3.5 结果 MVP 与 AI 评审门

## 阶段合同（机器接口）

- phase_id: 06-cumcm-result-mvp；display_name: 结果 MVP 体检；owner_agent: result-review-agent。
- entry_conditions: 05 结果资产为 generated，代码日志和 RESULTS_INDEX.csv 齐全。
- inputs: 真实代码、结果、图表、G1 锁定模型、题面和验证计划。
- outputs: mvp/、result_ai_review/、G2_CONFIRMATION_PACKET.json、MVP_REVIEW.csv、EVIDENCE_TRACE.csv。
- exit_conditions: 三层检查完成；critical/high 已关闭或明确退回；phase_result=READY_FOR_G2。
- failure_return: 模型返回 04；代码/数据返回 05；环境返回 01；不自行请求 G2。
- writable_paths: mvp/、result_ai_review/、reports/G2_CONFIRMATION_PACKET.json、reports/MVP_REVIEW.csv、reports/EVIDENCE_TRACE.csv。
- read_only_paths: code/、results/、figures/data/、G1 包和题面。
- invalidates: MVP 发现的合理性、证据或实现问题使 05 或 04 退回；结果变化使 G2 及下游失效。
- user_gate: true（只产 G2 包；由 orchestrator 记录确认）。
## 本地多智能体合同
- owner_agent：result-review-agent；
- result_ai_review 是本阶段输出，不是独立 skill；
- 必须审查实现一致性、题目合理性和证据可用性；
- 所有纳入问题通过后才生成 G2_CONFIRMATION_PACKET，用户门禁由 orchestrator 单独管理；
- 退出状态：PASS、REVISE 或 BLOCKED。

本 skill 只在第一次正式论文写作前运行。它不是正式论文写作器，也不是最终验收器，而是把代码结果压缩成一份最小可读论文，并做三层结果体检，防止 `05-cumcm-coding-visual` 输出不理想或有 bug 时继续黑盒进入 `07-cumcm-drawio` 和 `09-cumcm-writing`：

```text
第一层：实现一致性——是否按已确认模型正确实现
第二层：本题合理性——结果是否符合题意、边界、约束和方向逻辑
第三层：证据可用性——是否有验证、解释和可复现证据支持结论
```

## 阶段位置和硬门禁

```text
04-cumcm-modeling
→ 用户确认建模思路（G1）
→ 05-cumcm-coding-visual
→ 06-cumcm-result-mvp（本 skill）
→ AI 结果评审
→ 用户确认计算结果（G2）
→ 07-cumcm-drawio
→ 09-cumcm-writing
```

没有 G2，不得进入 `07-cumcm-drawio` 或 `09-cumcm-writing`。本 skill 只负责第一版正式论文前的结果体检；后续纯语言、版式和措辞修改不默认重复运行。若模型、数据口径、代码或核心数字发生变化，必须重新运行受影响结果，必要时重新运行本 skill。

## 输入

必须读取：

```text
reports/ANALYSIS_MODELING_REPORT.md
reports/RESULTS_REPORT.md
reports/TECHNICAL_DECISIONS.md
reports/RESULTS_INDEX.csv
code/run_manifest.json
code/environment_setup.log（如存在）
code/
results/
figures/
题面和附件
```

若存在，还必须读取 `reports/PROBLEM_SCOPE.csv`、`reports/DATA_STRUCTURE_AUDIT.csv`、`reports/INDEX_SCOPE_MAP.csv`、`reports/CONSTRAINT_COVERAGE.csv` 和 `reports/MODEL_CODE_MAPPING.csv`，用于检查本题维度、约束来源和模型—代码映射；缺少这些审计文件时记录为证据缺口，不得用 MVP 文字代替。

逐问核对：用户确认后的锁定模型、`model_decision_id`、代码入口、结果文件、验证计划、论文目标位置和摘要候选数字。不得把旧版本结果、未登记文件或论文中的数字当作当前事实源。

如果项目已有旧版 `mvp/`、`result_ai_review/`、结果报告或 G2 记录，必须执行“旧 MVP—当前建模报告—当前代码—当前机器可读结果”四方差异核对。当前代码和机器可读结果优先；旧 MVP 保留并标记为旧版本，差异写入 `result_ai_review/AI_REVIEW_ISSUES.csv` 或独立 `reports/OLD_VERSION_DIFF.md`，受影响小问重新生成 MVP，旧确认不得自动继承。

## 输出目录

按题面实际顶层问题数生成，不固定四问：

```text
mvp/
├── MVP_PAPER.md
├── problem_1.md
├── problem_2.md
└── …

reports/
├── MVP_REVIEW.csv
└── G2_CONFIRMATION_PACKET.json

result_ai_review/
├── AI_REVIEW_SUMMARY.md
├── problem_1_review.md
├── problem_2_review.md
├── …
├── AI_REVIEW_ISSUES.csv
└── EVIDENCE_TRACE.csv
```

已有文件不得静默覆盖；修复项目在独立版本目录输出。

## MVP 最小论文要求

`MVP_PAPER.md` 提供整体速览，`problem_X.md` 提供逐问检查稿。每个小问控制在约半页至一页，优先复用已生成的表和图，不重新制作华丽版式。每问必须包含：

```text
# 问题 X MVP 检查稿
## 1. 本问要解决什么
## 2. 已确认模型
## 3. 数据处理
## 4. 核心计算结果
## 5. 最小验证证据
## 6. 结果解释
## 7. 小问结论
## 8. 当前状态
```

内容约束：

- “本问要解决什么”写清题意、输入和输出；
- “已确认模型”只能使用 G1 后锁定的模型，写出核心变量、目标、约束或统计假设；
- “数据处理”只写真实执行过的清洗、变换、编码和指标构造；
- “核心计算结果”引用真实结果文件中的最小表格或明细，标明单位和口径；
- “最小验证证据”至少包含一种与题型匹配的误差、可行性、稳定性、基线、残差或敏感性证据；
- “结果解释”说明数量级、趋势、比较和异常，不能只写“结果较好”；
- “小问结论”直接回答题目，不引入结果文件中没有的新数字；
- 当前状态只能为 `PASS`、`REVISE` 或 `BLOCKED`。

MVP 不负责正式 LaTeX 排版、完整摘要、优秀论文语气、完整参考文献、技术路线图、代码附录或最终 PDF 验收，不得用空泛文字凑篇幅。

## AI 结果评审

在生成 MVP 后，必须生成 `result_ai_review/`。评审方法借鉴 `13-cumcm-paper-review` 的结构化证据链思想，但只做结果体检，不执行完整论文批注流程。

### 评审对象

对每个小问同时比较：

```text
题面要求
↔ 建模报告
↔ 实际代码入口
↔ 机器可读结果
↔ MVP 叙述
↔ 验证资产
```

### 必查项目

1. **题意覆盖**：输入、输出和全部子任务是否覆盖；
2. **模型一致性**：建模报告、锁定记录、代码和 MVP 中的模型、变量、目标和约束是否一致；
3. **结果完整性**：结果文件是否存在、非空、字段齐全且与 `RESULTS_INDEX.csv` 对得上；
4. **数值和单位**：数量级、百分比、概率、得分、成本、距离和单位是否混淆或明显错位；
5. **边界、守恒和约束**：变量范围、非负/整数条件、容量、资源、流量守恒、比例和、汇总—分项关系是否成立；
6. **题意方向和单调性**：在题目明确逻辑下，成本/资源/权重/阈值变化后的结果方向是否合理；不能只写“看起来合理”，必须给出题面边界或计算证据；
7. **基线和反事实检查**：主模型是否与透明基线比较；关键参数小幅扰动、简单方案或小规模精确解是否揭示明显不稳定或反常结果；
8. **验证证据**：预测检查时间顺序和误差，优化检查可行性/约束/目标值，评价检查标准化/权重/排序稳定性，分类检查混淆矩阵/F1/AUC 或等价指标，检验检查效应量/区间/显著性；
9. **结论支持**：结论是否由结果支持，是否过度推断、把相关写成因果、把预测概率写成现实概率或把相对评分写成绝对质量；
10. **图表可用性**：图表是否存在、与结果对应、坐标轴/单位/图例是否清楚并真正支撑结论；
11. **代码复现性**：入口、环境、依赖、日志、输入哈希和输出路径是否足以重跑；
12. **失败和异常**：是否存在空表、部分问题未运行、异常值、结果方向冲突、环境错误或未登记旧口径。

### 本题结果合理性审查要求

不得把“代码运行成功”或“结果与模型一致”当作本题合理性的证明。对每个小问至少形成一条有证据的合理性判断，使用以下顺序：

```text
题目要求的输出
→ 结果对应的字段/方案/预测
→ 题面给出的边界、约束或方向
→ 实际计算值与边界的比较
→ 基线、守恒、单调性或扰动检查
→ 合理/不合理/证据不足的判定
```

至少检查适用的项目：

- 优化：逐条约束回代、变量边界、资源/容量、目标值分项和可行基线；
- 预测：训练—测试时间隔离、非负/比例边界、基线误差、预测趋势、残差结构和预测区间；
- 评价：指标正负方向、标准化、权重归一、得分—排名一致性和权重扰动稳定性；
- 分类：类别定义、混淆矩阵总量、逐类指标、概率范围和少数类是否被忽略；
- 统计检验：样本量、检验前提、效应量—区间—显著性一致性；
- 机理/网络/排队/库存等：守恒关系、稳定条件、容量边界、参数量纲和理论/仿真对照。

无法从题面、数据或验证资产判断合理性时，必须标为 `needs_confirmation` 或 `BLOCKED`，不能凭常识替题目补充事实。

### 结果异常的专项复核

当结果相对透明基线、旧版本、优秀论文或题面直觉异常偏高/偏低时，不得直接归因于“模型更先进”或“算法更好”。必须拆解比较：时间/空间/阶段维度、参数局部性、约束集合、目标函数、需求上下限、销售/成本口径、求解状态和单位换算。异常未解释时，`reasonableness_status` 至少为 `REVISE`，不得请求 G2。

### 评审输出

`AI_REVIEW_SUMMARY.md` 必须给出总体判定、逐问判定、阻塞项、必须返工项和建议返工项。每个 `problem_X_review.md` 必须给出：

```text
题意覆盖
模型—代码—结果一致性
结果和单位检查
验证证据检查
图表检查
结论强度检查
复现性检查
问题清单
退回阶段
本问判定
```

`AI_REVIEW_ISSUES.csv` 表头固定为：

```csv
issue_id,problem_id,severity,category,evidence,description,impact,return_stage,recommended_action,status
```

严重程度：

```text
critical：必须停止后续流程
high：必须修复后才能进入正式写作
medium：建议修复，可在正式写作前处理
low：仅语言或展示优化，可留给写作阶段
```

### 三层状态

`MVP_REVIEW.csv` 和每个 `problem_X_review.md` 必须分别记录：

```text
implementation_status：PASS / REVISE / BLOCKED
reasonableness_status：PASS / REVISE / BLOCKED / NEEDS_CONFIRMATION
evidence_status：PASS / REVISE / BLOCKED
```

三者不能合并成一个“代码成功”状态。只有三层均为 `PASS`，该小问才可进入 G2 候选通过列表。

`EVIDENCE_TRACE.csv` 至少记录：

```csv
problem_id,claim_id,question_requirement,model_decision_id,code_entry,result_file,validation_file,mvp_location,review_location,trace_status,notes
```

每个核心结论必须能从题面追溯到代码、结果和 MVP 位置；无法追溯时标为 `blocked` 或 `needs_confirmation`，不得猜测。

## 判定规则和 G2

`MVP_REVIEW.csv` 表头至少为：

```csv
problem_id,model,result_files,key_result,validation,implementation_status,reasonableness_status,evidence_status,issues,status,next_action
```

本 skill 的总体结果只有在以下条件同时满足时才为 `PASS`：

```text
每个小问都有 MVP 文件
每个小问都有核心结果和最小验证证据
每个小问实现、合理性和证据三层状态均为 PASS
每个小问至少有一条带题面/边界/计算依据的合理性判断
异常高/低结果已完成差异拆解，或明确标为 REVISE/BLOCKED
没有 critical/high 问题
没有 BLOCKED 小问
AI_REVIEW_SUMMARY.md = PASS
MVP_REVIEW.csv 中所有小问 = PASS
```

如果结果不理想但代码能运行，也不能自动通过；必须标为 `REVISE`，说明是模型适配、数据处理、代码实现、题意合理性、验证不足还是结果解释问题。若无法判断结果是否符合题意，标为 `NEEDS_CONFIRMATION`/`BLOCKED`，不得用“数量级看起来正常”代替证据。

只有以下条件全部满足，才可生成 G2_CONFIRMATION_PACKET；本 skill 不请求、不接收、不记录用户 G2：

```text
MVP 总体 PASS
AI 评审总体 PASS
核心结果状态为 generated
没有未处理的 critical/high 问题
代码入口和环境记录可复现
```

G2_CONFIRMATION_PACKET 必须包括：

```text
确认时间
确认者
确认文本
通过的问题编号
需要返工的问题编号
允许进入 07-cumcm-drawio/09-cumcm-writing 的范围
```

orchestrator 收到用户明确确认后，才允许将 MVP 结果交给 `07-cumcm-drawio` 和 `09-cumcm-writing`，并生成人读视图 `reports/MVP_DECISION.md`。用户未确认、结果方向不合理或任何小问为 `REVISE/BLOCKED` 时，不得继续。

## 退回规则

|问题|退回阶段|
|---|---|
|模型不适合题意、变量/约束定义错误|`04-cumcm-modeling`|
|代码错误、结果为空、单位错、验证缺失、依赖或运行失败|`05-cumcm-coding-visual` 或 `doctor`|
|仅图表表达不清|`05-cumcm-coding-visual`|
|仅 MVP 文字组织问题|本 skill，或正式写作阶段|
|模型、数据、代码或核心数字改变|重新运行受影响结果，必要时重新执行本 skill|

失败时保留问题、证据、错误日志和已尝试修复，不删除失败记录，不用未验证结果继续写论文。

## 与其他 skill 的接口

- `05-cumcm-coding-visual`：提供真实代码、结果、图表、日志和 `RESULTS_INDEX.csv`；本 skill 不替代代码验证。
- `07-cumcm-drawio`：只有 G2 通过后才能读取 MVP 结果和最终代码结构生成技术图。
- `09-cumcm-writing`：只有 G2 通过后才能读取 MVP 和结果索引生成第一版正式论文；正式写作不得重新选择模型。
- `11-cumcm-verify`：最终仍需重新检查证据、引用、页面、复现和 PDF；MVP PASS 不等于最终 PASS。
- `13-cumcm-paper-review`：用于正式论文或 Word/PDF 完成稿审阅，不替代本阶段的快速结果体检。

## 不执行的事项

```text
不生成正式 LaTeX 论文
不修改模型和代码
不编造数字、图表、引用或结论
不以程序退出码为唯一正确性证明
不因某个小问失败而继续写完整论文
不把 MVP 的 PASS 写成最终论文 PASS
```
