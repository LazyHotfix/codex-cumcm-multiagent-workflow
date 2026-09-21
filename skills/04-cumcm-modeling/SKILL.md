---
name: 04-cumcm-modeling
description: "审计高教杯题面与数据，生成候选模型、证据包、验证计划和代码接口。"
---

# 高教杯赛题分析与证据包设计

## 阶段合同（机器接口）

- phase_id: 04-cumcm-modeling；display_name: 题面与建模设计；owner_agent: modeling-agent。
- entry_conditions: 03 项目审计 PASS；题面、附件和本地模型目录可读。
- inputs: 题面、附件、数据结构审计、主流模型目录、范围和模板约束。
- outputs: ANALYSIS_MODELING_REPORT.md、逐问证据包、G1_CONFIRMATION_PACKET.json、代码接口和验证计划。
- exit_conditions: 候选前两/前三名、基线、适用条件和验证计划齐全；phase_result=candidate_pending。
- failure_return: 题意/数据不可解释返回 03；目录校验失败保持 BLOCKED；不自行锁定模型。
- writable_paths: reports/ANALYSIS_MODELING_REPORT.md、reports/DATA_STRUCTURE_AUDIT.csv、reports/G1_CONFIRMATION_PACKET.json、reports/CONSTRAINT_COVERAGE.csv、reports/MODEL_CODE_MAPPING.csv。
- read_only_paths: 原始题面、附件和本地 mainstream-model-catalog。
- invalidates: 模型、公式、假设或约束变化使 G1、05、06、G2、07、08、09、10、11、13 失效。
- user_gate: true（只生成 G1 包；由 orchestrator 记录确认）。
## 本地多智能体合同
- owner_agent：modeling-agent；
- 只负责题面、附件、数据、候选模型和验证计划；
- 未通过 G1 不得实现代码或写正式论文；
- 输出必须绑定 problem_id、model_decision_id 和 run_id；
- 退出状态：candidate_pending 或 BLOCKED。

本阶段不写论文正文，不直接生成最终 PDF；负责把题面和附件转化为可以被代码、图表、结构化写作和验收共同消费的建模接口。模型选型采用“候选—解释—用户确认—锁定”流程：AI 必须先生成前两名或前三名真实候选并解释适配性，暂停等待用户确认；未经确认不得进入代码实现或论文写作。不得使用全局人工优先表替代当前题目的数据和题意判断。

## 输入审计

读取题面、全部附件、`plan.md`、已有版本、模板说明和本 skill 内置的主流模型目录。目录实际位置为：

```text
references/mainstream-model-catalog/
```

先读取并校验：

```text
references/mainstream-model-catalog/CATALOG_VERSION.json
```

当前内置目录版本以本 skill 的 `references/mainstream-model-catalog/CATALOG_VERSION.json` 为准。按其中 SHA-256 校验目录文件；哈希不匹配时停止选型并报告阻塞。用户维护的外部备份不作为运行时来源。区分顶层问题与子问，记录文件哈希/版本、表单规模、字段、单位、主键、重复、缺失、异常、极端值、结构性缺失和不可识别变量。不得把缺失值一律填零或把极端值一律删除；关键处理要有替代口径或敏感性计划。

## 数据结构与题意维度审计

不能只判断文件能否读取，必须在建模前理解字段的现实含义、时间/空间/阶段/对象粒度、总量与均值/上下限的区别以及多表主外键关系。创建或更新：

```text
reports/DATA_STRUCTURE_AUDIT.csv
reports/PROBLEM_SCOPE.csv
reports/INDEX_SCOPE_MAP.csv
```

至少登记：

```csv
source_file,sheet_name,field_name,field_description,data_type,unit,time_scope,space_scope,season_scope,object_scope,primary_key,foreign_key,missing_count,duplicate_count,outlier_count,aggregation_allowed,aggregation_warning,processing_action
```

对题面每个“每日、每月、每季、当期、分地区、分地块、分设备、分阶段”等词，建立维度映射：题目原句 → 时间/空间/阶段/对象维度 → 决策变量索引 → 参数索引 → 约束索引 → 输出索引。默认不得删除题面明确维度；只有证明目标函数、约束、参数和输出在聚合前后等价，且可行域不变时，才允许聚合，并在 `proof_or_reason` 中记录证明或理由。

变量和参数索引必须对齐。若变量保留地块、季次或地区下标，价格、成本、产量、需求等参数不得无说明地平均到更粗粒度；`mean()`、`sum()`、`groupby()` 等聚合操作必须在建模报告和代码接口中说明保留/删除了哪些维度。

## 约束来源与模型边界

创建或更新 `reports/CONSTRAINT_COVERAGE.csv`，每条约束至少记录：

```csv
constraint_id,question_text,source_type,real_meaning,model_formula,code_location,index_scope,hard_or_soft, numeric_basis,validation_method,formally_adopted,status
```

`source_type` 必须区分：题面明确、附件直接给出、数据结构推断、用户确认、优秀论文假设、团队自定义、模拟设定。优秀论文中的额外约束不得自动变成本题硬约束。

对“不宜过小、不能太分散、基本满足、合理安排、尽量降低风险”等模糊表述，生成弱/中/强化多个候选口径，说明各自来源、影响和是否正式采用。只有题意歧义或不同口径会显著改变结果时，才建立条件式 M0（严格题面）、M1（题面解释）和 M2（强化诊断）并比较可行性、目标值、缺口和方案结构；M2 不能冒充题面唯一答案。

建模报告必须包含模型边界：未采用的方法及原因、未加入的约束、模拟参数、相关矩阵/系数来源、求解状态含义以及结论不能外推的范围。

## 目标函数与候选模型审计

先明确目标是利润、销售量、需求满足、风险调整收益还是资源利用，逐项核对收入/成本/折扣/单位换算、局部参数、缺货/弃耕是否改变题意。候选模型比较必须使用相同数据、目标、约束、参数、口径和输出要求；否则只能说明口径差异，不能宣称算法优劣。

在交给代码阶段前创建或更新：

```text
reports/MODEL_CANDIDATES.csv
reports/MODEL_CODE_MAPPING.csv
reports/COUNTERFACTUAL_PLAN.csv
```

`COUNTERFACTUAL_PLAN.csv` 按风险选择约束消融、基线、参数扰动或反事实试验，至少写明变更项、预期输出、验证方法和论文用途。不是每道题都强制所有消融；但优化、风险、评价和预测题应至少有一个透明基线和一个能检验关键假设的对照。

## 参考文献与理论依据

## 内置主流模型目录使用

按以下顺序读取目录资源：

1. `CATALOG_VERSION.json`：确认版本、状态、哈希和自适应选型模式；
2. `PROBLEM_TO_METHOD_MATRIX.csv`：按题型和场景取得候选方法；
3. `MAINSTREAM_MODEL_CATALOG.csv`：读取适用条件、对象类型、成熟度、最低验证和常见误用；
4. `MODEL_NAME_NORMALIZATION.csv`：统一模型名称和别名；
5. `MODEL_SELECTION_RULES.md`、`MODEL_CATALOG_SCHEMA.md`：解释筛选和记录规范；
6. `MODEL_CATALOG_DATA_QUALITY.md`、`CATALOG_CLEANING_REPORT.md`：处理复核标记和已知清洗边界。

不得把目录中的 `priority_level=S/A` 当作无条件适用证明；不得把 `needs_human_review=true` 的记录直接作为最终主模型；不得使用目录外方法绕过候选比较和用户确认。全局人工模型优先表不作为自动选型输入。

对每个需要外部依据的模型、统计检验、评价指标、算法或数据处理方法，记录至少一条可追溯来源。创建或更新：

```text
references/references.bib
references/REFERENCE_INDEX.csv
```

`REFERENCE_INDEX.csv` 至少包含：

```csv
reference_key,title,authors_or_organization,year,source_url_or_doi,problem_id,method_or_claim,paper_section,citation_status,notes
```

`citation_status` 使用 `planned`、`used`、`verified`、`not_used`。来源、用途和正文目标位置必须先登记，后由写作阶段引用。

## 最终报告

在 `reports/ANALYSIS_MODELING_REPORT.md` 创建一份锁定后的最终报告，不保留路线选择前的重复副本。推荐结构：

```text
# 建模报告
## 1. 题面与问题拆解
## 2. 数据审计与预处理
## 3. 总体建模框架和问题依赖
## 4. 问题一证据包与模型
## 5. 问题二证据包与模型
...按实际问题数...
## 末章：统一验证、敏感性与代码接口
```

## 每问证据包

每个顶层问题必须显式定义：

1. 题意、输入、输出、与前问依赖；
2. 数据处理、变量和符号；
3. 至少 2 个、至多 3 个真实候选方案及评分理由；
4. 用户确认前记录候选排序和适配性解释；确认后记录锁定模型及确认依据；
5. 数学公式、目标函数、约束或统计假设；
6. 算法/求解步骤、停止条件、复杂度或可行性；
7. 主要结果表字段和来源；
8. 主要结果图类型、横纵轴、单位和用途；
9. 有效性、误差、稳健性或敏感性证据；
10. 预期解释句和直接回答题意的问题小结。

每问必须另外注明：题意维度映射、约束来源、目标函数现实含义、不能聚合的维度、参数局部性检查、至少一个透明基线和反事实/敏感性计划（若不适用，写等价证据和原因）。

每问还必须给出一行“逐问证据闭环矩阵”：

```text
problem_id | 题意输出 | 锁定模型 | 关键假设 | 验证方法 | 核心 result_id
| 主要表/图 | 论文目标位置 | 预期正文结论 | 小结回答 | 当前状态
```

不适用的表、图或检验必须写明等价证据和原因，不能留空。`当前状态` 初始为 `planned`，不得在没有代码资产时写成 `generated`。

标准闭环：

```text
问题分析 → 数据处理/变量 → 模型比较 → 模型建立 → 算法求解
→ 主要结果表 → 主要结果图 → 检验/稳健性 → 解释 → 小结
```

不要机械要求所有问题使用同一种图或同一种检验。如果某项不适用，必须在证据包中给出等价证据和原因，不能留空。

## 候选模型评分与确认门

候选评分至少包含：题意适配性 30%、数据结构与样本适配性 25%、适用前提满足度 15%、验证可行性 15%、解释性 10%、复现性与计算稳定性 5%。主流等级只能作为候选成熟度参考，不得替代题意和数据适配性；不得为了追求“创新”给复杂方法额外加分。评分只是比较证据，不代替实际试算。

每问必须遵守以下状态机：

```text
candidate_pending → user_confirmed → locked
         ↘ blocked
```

在 `candidate_pending` 状态，生成前两名或前三名候选、适用条件、风险、透明基线、验证计划和未选理由，输出 G1_CONFIRMATION_PACKET 并停止。用户确认由 orchestrator 写入唯一 `reports/DECISION_LEDGER.yaml`；本 skill 不接收、不记录、不代替用户确认。确认后由总控重新调度本 skill 完成锁定包，才允许交给 `05-cumcm-coding-visual`。

不得把 `MAINSTREAM_MODEL_CATALOG.csv` 中 `needs_human_review=true` 的记录直接作为最终主模型；目录外方法必须说明主流方法不足并取得用户确认。不得自动读取或执行全局人工模型优先表。

## 代码接口表

报告末尾必须给出可执行接口：

| 问题 | 输入文件/字段 | 代码入口 | 输出结果文件 | 表/图源数据 | 校验方法 | 论文目标位置 |
|---|---|---|---|---|---|---|

每个结果对象都要有稳定的 `result_id`，供 `05-cumcm-coding-visual` 写入 `RESULTS_INDEX.csv`。结果对象不能只存在于长篇 Markdown 叙述中；同一 `result_id` 不得因改写正文或重新运行而随意更换。模型路线也必须有稳定的 `model_decision_id`，用于关联候选、用户确认、代码入口和论文位置。

## 分析阶段交接清单

交给 `05-cumcm-coding-visual` 前，必须锁定问题数、每问输出、用户确认后的模型和公式、关键假设、验证方法、核心 `result_id`、`model_decision_id`、结果来源、论文目标位置、需要引用的 `reference_key`、摘要/结论候选数字、数据结构审计、维度映射、约束来源和代码映射。每问没有用户确认记录，不得通过交接门禁。

## 进入代码阶段的门禁

只有在以下条件满足后才进入 `05-cumcm-coding-visual`：问题数已锁定；目录版本校验通过；数据结构和题意维度审计完成；每问证据闭环矩阵完整；至少两名候选已比较并由用户确认锁定；变量/参数索引已对齐；所有正式约束都有来源；公式和约束可直接实现；每个主要表/图/检验都有来源和验收方法；基线和反事实计划已明确或说明等价证据；需要引用的方法已有 `reference_key`；历史口径冲突已处理。
