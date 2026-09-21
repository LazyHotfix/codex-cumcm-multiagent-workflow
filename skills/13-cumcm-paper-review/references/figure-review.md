# 图审证据链与优秀论文图表类型

## 目标

图审必须先形成结构化证据链，再生成写回论文的批注。不要直接根据图题或作者解释下判断。

核心产物：

- `figure_inventory.json` / `figure_inventory.md`：审稿前自动生成的图表清单，用于防止漏审。
- `figure_review.json`：逐图/逐表证据链记录。
- `figure_issues.json`：由证据链生成的可写回批注。
- `figure-patterns.json` / `figure-patterns.md`：从优秀论文中抽取的图表类型模式库，用于提示检查重点。

## 从优秀论文学习图表类型

使用命令：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py build-figure-patterns --manifest math-modeling-intake\_catalog\manifest.json
```

默认输出：

```text
math-modeling-review-cases/_learned/figure-patterns.json
math-modeling-review-cases/_learned/figure-patterns.md
```

当前项目已从 `manifest.json` 中的 11 篇 `text-rich` 优秀论文抽取图/表标题，过滤正文引用后得到 242 条图表标题。分类结果只作为图审提示，不替代人工判断。

## 已归纳类型

### 流程图

常见标题：问题流程图、求解流程图、算法流程图、总体思路框架。

检查重点：

- 节点是否覆盖正文步骤。
- 箭头方向是否正确。
- 输入、输出、分支条件和终止条件是否清楚。
- 是否把大段正文硬塞进节点。

### 模型结构图

常见标题：系统示意图、工作原理图、几何关系示意图、模型框架图。

检查重点：

- 变量关系是否与公式一致。
- 模块输入输出是否完整。
- 并列关系和因果关系是否混淆。
- 图例和符号是否与正文一致。

### 数据分布图

常见标题：产量分布、类型占比、最优决策分布、排名图。

检查重点：

- 样本范围、分母口径和分组阈值是否说明。
- 是否适合用饼图；类别多或小比例拥挤时优先建议条形图/帕累托图。
- 是否标注样本数、单位和数据来源。

### 趋势图

常见标题：随时间变化、进化曲线、利润折线图、速度变化图。

检查重点：

- 时间轴、迭代轴或参数轴是否清楚。
- 是否需要误差带、基线或置信区间。
- 平滑、插值、归一化方法是否说明。

### 对比图

常见标题：不同条件下对比、成本与收入折线图、方案比较图。

检查重点：

- 比较口径是否一致。
- 坐标尺度是否统一。
- 是否只展示有利结果。
- 最优/基准方案是否标出。

### 敏感性分析图

常见标题：参数影响、扰动分析、变量波动、目标结果影响。

检查重点：

- 参数范围、步长和控制变量是否说明。
- 是否覆盖边界情形。
- 结论是否只在局部范围成立。

### 空间/几何图

常见标题：位置图、路径图、区域划分、螺旋线、坐标关系图。

检查重点：

- 坐标系、单位、比例尺和方向是否明确。
- 几何约束是否与公式一致。
- 路径或区域是否回应题目约束。

### 结果表

常见标题：结果表、决策方案表、指标值表、变量序列表、支撑文件目录。

检查重点：

- 列名、单位和有效数字是否完整。
- 最优值是否标识。
- 能否追溯到模型输出、脚本或附件。
- 长表是否应移至附录。

## 图审记录字段

每条图审记录至少包含：

```text
id:
page:
target/search/bbox:
title:
visual_type:
context_position:
body_claim:
visual_observation:
evidence_judgment:
data_traceability:
needs_confirmation:
content_advice:
style_advice:
```

`evidence_judgment` 只能使用：

- 支持
- 部分支持
- 不支持
- 无法判断

如果数据来源、计算口径、生成脚本或模型输出无法追溯，批注必须使用“需确认”，不能写“合理/正确”。

## 使用流程

1. 先运行 `build-figure-inventory`，为待审论文建立 `figure_inventory.json` 和 `figure_inventory.md`。
2. 渲染或提取待审论文图表，逐项核对清单是否遗漏关键图表。
3. 用 `make-figure-review-template` 生成草稿。
4. 逐图填写证据链。
5. 用 `build-figure-issues` 生成 `figure_review.json` 和 `figure_issues.json`。
6. 必要时把 `figure_issues.json` 与普通 `issues.json` 合并后写回 PDF/DOCX。

命令示例：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py build-figure-inventory --case-dir math-modeling-review-cases\CASE_ID
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py make-figure-review-template --format pdf --case-dir math-modeling-review-cases\CASE_ID
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py build-figure-issues --format pdf --case-dir math-modeling-review-cases\CASE_ID --draft math-modeling-review-cases\CASE_ID\work\pdf_figure_review_draft.md
```

## 边界

- 优秀论文图表模式只用于提示“这种图通常该查什么”，不说明待审论文图表一定正确。
- 图表标题抽取来自 PDF 文本层，可能仍有少量正文引用混入；正式审稿时必须回到页面渲染和上下文。
- 图片版优秀论文若只有 OCR 侧写，不能直接当作完整图表模式来源。
