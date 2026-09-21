---
name: 05-cumcm-coding-visual
description: "实现已锁定的高教杯模型，生成可复现代码、结果文件、数据图和结果索引。"
---

# 高教杯编程实现与数据图表生成

## 阶段合同（机器接口）

- phase_id: 05-cumcm-coding-visual；display_name: 编程与结果资产；owner_agent: coding-agent。
- entry_conditions: G1.status=CONFIRMED 且 packet_sha256 与当前状态一致。
- inputs: 锁定建模报告、G1 决策、原始数据、math 环境和代码接口。
- outputs: code/、results/、figures/data/、RESULTS_INDEX.csv、MODEL_CODE_MAPPING.csv、run_manifest.json。
- exit_conditions: 每问总入口成功或明确失败；核心结果、验证、日志和哈希齐全；phase_result=generated。
- failure_return: 环境返回 01；模型/接口返回 04；数据/代码/结果返回 05。
- writable_paths: code/、results/、figures/data/、reports/RESULTS_INDEX.csv、reports/MODEL_CODE_MAPPING.csv、code/run_manifest.json。
- read_only_paths: G1 包、题面、附件和模板类文件。
- invalidates: 代码、核心结果、随机种子或环境变化使 06、G2、07、09、10、11、12、13 失效。
- user_gate: false。
## 本地多智能体合同
- owner_agent：coding-agent；
- 只能实现 G1 已锁定模型；
- 代码、结果和数据图必须绑定当前 run_id；
- 不得修改模型决策或写正式论文；
- 退出状态：generated、REVISE 或 BLOCKED。

本阶段承接 `04-cumcm-modeling` 的最终建模报告和逐问证据包。目标不是只跑出一个汇总数字，而是生成从原始数据到论文结论的完整可追溯资产。代码阶段不写论文正文，但必须明确每个表、图和数字的论文目标位置。

## 代码工程要求

创建真实的 `code/`、`results/`、`figures/` 和必要的表格源数据目录。必须提供：

- `run_all.py` 总入口；
- 每个顶层问题的独立入口；
- 数据审计/清洗模块；
- 统一随机种子、环境和日志；
- `requirements.txt` 或等价环境说明；
- `run_manifest.json`（输入文件哈希、运行命令、版本、随机种子和输出目录）；
- 结果与图表输出路径；
- 失败时可定位的错误信息。

## 环境缺失与自动修复

代码阶段允许直接修复当前项目的 Conda/Python 运行环境，不因普通项目依赖缺失反复中断用户。执行顺序为：

```text
检测当前解释器和 Conda 环境
→ 读取 requirements.txt、environment.yml 或等价环境说明
→ 运行最小导入/版本检查
→ 列出缺失包和触发它们的代码入口
→ 在当前项目环境中安装缺失依赖
→ 重新执行导入检查
→ 运行 run_all.py 或受影响的问题入口
→ 记录环境和安装结果
```

### 可直接安装的范围

- 当前激活的项目 Conda 环境中的 Conda 包；
- 当前项目解释器对应的 Python 包，使用 `python -m pip`；
- 项目明确声明的运行依赖和绘图库、数值库、求解器 Python 接口；
- 缺失依赖安装后应更新 `requirements.txt`、`environment.yml` 或等价锁定文件。

### 安装限制

- 只安装缺失或明确需要的包，不无理由升级全环境，不修改无关项目；
- 不把依赖安装到系统 Python；当前环境是 `base` 且项目没有明确使用 base 时，先报告并建立项目专用环境；
- 优先使用锁定文件中的版本；无法满足时记录实际版本和原因；
- Conda 包优先用 Conda 安装，Conda 不可用或无对应包时才使用当前解释器的 pip；
- 每条安装命令、时间、解释器路径、环境名、包版本和返回码写入 `code/environment_setup.log`，并同步到 `code/run_manifest.json`；
- 安装后必须重新运行导入检查和完整入口，不能以“安装命令成功”代替运行验证。

### 需要转交 doctor 或单独授权的情况

以下不属于普通项目级依赖，不能静默用 pip/Conda 代替：

```text
xelatex、Typst、DrawIO、pdftoppm、mutool、ImageMagick
系统驱动、编译器、管理员权限软件
无法在当前项目环境写入的系统路径
```

此类缺失转交 `doctor`；若安装命令需要管理员权限或额外网络/系统权限，先报告具体命令和影响，不绕过授权。

### 安装失败处理

网络失败、版本冲突、许可证/编译器缺失或包无法安装时，记录完整错误、已尝试命令和替代方案，将受影响结果标为 `blocked`，不得用未验证的假结果继续写论文。修复环境后必须重新运行受影响结果并更新 `run_manifest.json`。

最终交付代码目录只保留真实运行所需文件，不把缓存、临时 PNG、编译辅助文件或虚构脚本放入交付包。正式运行必须能够从 `run_manifest.json` 复现，不得只记录“运行过代码”。

## 逐问实现契约

按问题顺序实现并运行。每问必须完成：

1. 读取并审计输入数据；
2. 按锁定模型实现公式、目标、约束和算法；
3. 检查可行性、单位、边界和异常输入；
4. 输出主结果、候选比较、参数/系数、预测明细或方案明细；
5. 输出至少一张服务于结论的数据图；
6. 输出一种有效性、误差、稳健性或敏感性证据；
7. 保存表格源数据、作图数据、运行日志和机器可读结果；
8. 更新结果索引所需记录。

## 模型—代码映射与索引完整性

创建或更新 `reports/MODEL_CODE_MAPPING.csv`，逐项对应建模报告中的变量、参数、目标、约束、索引和输出：

```csv
problem_id,model_decision_id,model_element,report_symbol,code_symbol,input_field,index_scope,output_field,validation_script,status,notes
```

代码必须保留题面明确的时间、空间、季次、阶段和对象维度。对 `mean()`、`sum()`、`groupby()`、透视表或广播操作，记录被聚合维度、聚合理由、聚合前后目标/约束是否等价；未说明的高风险聚合标为 `blocked` 或 `needs_confirmation`，不能静默通过。参数索引必须与变量索引匹配，局部价格、成本、产量、需求和概率不得无说明地平均到更粗粒度。

## 独立结果验证

求解器退出码为 0 只表示程序完成，不能证明模型正确、结果合理或达到全局最优。每个优化结果必须由独立验证代码从输出文件回代检查：变量边界、容量、适配、轮作/阶段条件、需求上下限、产销/库存/流量守恒、目标值分项、土地利用率、闲置量和碎片化。预测、评价、分类和检验题使用与题型匹配的边界、基线、误差、稳定性和口径检查。

优化器若返回 `FEASIBLE`，必须同时记录 `best_bound`、目标值、求解时间和最优性差距；未证明最优时只能写“限时可行解/最优候选”，不能写“全局最优”。

## 基线、消融与真实敏感性

每个优化、风险、评价或预测问题至少保留一个透明基线；基线与主模型必须使用相同数据、目标、参数、约束和输出口径。按 `04-cumcm-modeling` 的 `COUNTERFACTUAL_PLAN.csv` 执行必要的约束消融、口径对照或参数扰动，输出机器可读的 `results/constraint_ablation.csv` 或等价文件，记录变更项、求解状态、目标值、可行性、关键结构指标和变化比例。敏感性分析必须真实重新求解，不能只修改论文文字。

结果明显偏高、偏低、异常稳定或出现大量碎片化/闲置时，暂停写作并拆解检查：维度聚合、局部参数、约束遗漏、需求上下限、重复收益、销售口径、求解状态和数据单位。问题未解释前，结果状态不得超过 `generated`。

每问完成后，按 `04-cumcm-modeling` 的闭环矩阵逐项回填实际输入、代码入口、结果文件、表/图源数据、验证资产和论文对象。若与锁定方案不一致，先在 `DECISIONS.md` 记录口径变化，再将受影响结果标为 `blocked`，不得静默替换。

不同题型的最低证据：预测要有时间顺序验证或合理误差评估；检验要报告效应量、区间和显著性；评价要说明标准化、权重和排名稳定性；优化要先证明可行解再优化目标，并报告约束和敏感性。

## 结果文件

`reports/RESULTS_REPORT.md` 是人类可读摘要，不能代替结构化结果。核心数字、结果表和图表源数据必须分别保存为 CSV/JSON/Parquet 等机器可读文件，并标明生成代码和版本。建议同步输出 `results/data_audit_summary.csv`、`results/parameter_mapping.csv`、`results/validation_summary.csv`；这些文件的具体内容按题型和实际证据启用。

## RESULTS_INDEX.csv

在 `reports/RESULTS_INDEX.csv` 创建或更新统一索引。表头至少为：

```csv
result_id,problem_id,evidence_type,source_data,code_entry,result_file,source_table_or_figure,figure_pdf,figure_png,paper_section,paper_object,body_explanation,summary_use,status,notes
```

每个核心结果至少一行，`status` 只能为 `planned`、`generated`、`embedded`、`verified`、`blocked`、`needs_confirmation` 或 `obsolete`。代码/绘图阶段只能推进到 `generated`；写作阶段推进到 `embedded`；验收阶段推进到 `verified`。`needs_confirmation` 表示结果已生成但必须经过 3.5/G2；`obsolete` 表示旧版本已被当前结果替代。核心结果没有 `paper_section`、`paper_object`、`body_explanation` 或 `summary_use` 时，不能在最终验收中通过。

每行必须能回答：服务哪个 `problem_id`、来自哪个输入版本、由哪个代码入口生成、由哪个源数据文件重建、用于证明什么结论、最终进入论文哪里。

## 图表契约

- 数据图必须由真实数据生成，并保存 PDF、PNG 和作图数据；
- 图内不放与 LaTeX caption 重复的大标题；
- 中文论文的标题、坐标轴、图例和单位中文化；
- 普通图优先紧凑画布和组合图，避免整页 PDF 边界造成嵌入后图形过小；
- 每张图必须在索引中写明论证问题、正文位置和图后解释；
- 图表不能只是“存在”，必须支撑一个可验证结论；
- 图表若不适用，记录等价表格或其他证据及理由；
- 非数据技术图交给 `07-cumcm-drawio`，本阶段不得重复绘制。

## 结果报告最低结构

```text
# 计算结果
## 运行环境和复现命令
## 原始数据审计与预处理
## 问题一结果
...按实际问题数...
## 统一约束/一致性/敏感性校验
## 结果文件与论文映射摘要
```

## 进入写作阶段的门禁

在 `06-cumcm-result-mvp` 启动前确认：每问代码已运行；主要结果文件非空；核心数字可回溯；主要图表和验证资产已生成；随机种子、输入哈希和运行命令已记录；`MODEL_CODE_MAPPING.csv` 和 `RESULTS_INDEX.csv` 完整；不存在未标记旧口径、未解释孤儿结果或失败结果；总入口可重复执行。进入 `06-cumcm-result-mvp` 的核心结果必须为 `generated`。在 `09-cumcm-writing` 启动前还必须满足 3.5 MVP/AI 评审和 G2 门禁。
