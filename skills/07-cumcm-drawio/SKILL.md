---
name: 07-cumcm-drawio
description: "生成有论证作用的高教杯技术路线图、求解流程图、模型图和代码结构图。"
---

# 高教杯非数据型技术图

## 阶段合同（机器接口）

- phase_id: 07-cumcm-drawio；display_name: 技术图生成；owner_agent: figure-agent。
- entry_conditions: G2.status=CONFIRMED；技术图确有论证作用。
- inputs: 锁定模型、真实代码结构、结果索引、G2 包和技术图需求。
- outputs: figures/technical/、技术图源文件、FIGURE_MANIFEST.csv。
- exit_conditions: 图源、导出文件、目标章节和解释用途登记完整；不需要时输出 SKIPPED 记录。
- failure_return: 图依赖/导出问题返回 07；模型/结果事实问题返回 04/05/06。
- writable_paths: figures/technical/、reports/FIGURE_MANIFEST.csv。
- read_only_paths: code/、results/、paper/正文、模板和 G2 台账。
- invalidates: 技术图源结构变化使写作、编译和验收中对应图资产失效。
- user_gate: false。
## 本地多智能体合同
- owner_agent：figure-agent；
- 只生成有论证作用的非数据型技术图；
- 不修改核心数字、模型和正文事实源；
- 跳过时必须记录 DRAWIO_SKIPPED；
- 退出状态：generated、SKIPPED 或 BLOCKED。

本阶段只负责有论证作用的非数据图：总体技术路线、数据处理流程、问题求解流程、模型结构和真实代码依赖图。折线图、柱状图、散点图、热力图、预测图、敏感性图等由 `05-cumcm-coding-visual` 生成。

## 输入与选择原则

读取 `ANALYSIS_MODELING_REPORT.md`、`RESULTS_REPORT.md`、`RESULTS_INDEX.csv`、代码目录、已有图表和 `06-cumcm-result-mvp` 的 `MVP_DECISION.md`/`AI_REVIEW_SUMMARY.md`。只有在 G2 结果确认通过、没有 critical/high 评审问题且用户已允许进入本阶段时才生成技术图；否则退回 `06-cumcm-result-mvp` 或对应责任阶段。不为凑数量生成装饰图。每张图必须在本阶段的 `FIGURE_MANIFEST.csv` 中登记独立 `result_id`、`problem_id`（总体图可用 `overall`）、目标章节和解释用途，并遵循 `planned → generated → embedded → verified` 状态流转；由 orchestrator/coding-agent 合并到项目结果索引。

## 技术路线图

通常生成一张总体路线图，节点应覆盖：原始数据/题面、数据审计、逐问模型、验证、结果资产、论文和验收。节点文字短、层次清楚、连线少且不交叉；不能把论文中不存在的模块画进去。

## 代码结构与运行关系图

当论文包含完整代码附录时，必须根据最终交付代码生成结构图。至少覆盖：

```text
原始附件 → run_all.py → 数据审计/公共工具 → 各问题入口
→ 验证与作图 → results/figures/paper 输出
```

图中每个代码节点和输出目录必须真实存在，名称与交付目录逐字一致；不能用旧版本结构图代替。保留 `.drawio` 源文件和可嵌入 PDF；DrawIO CLI 不可用时可使用等价矢量导出，并在验收报告中说明。

## 版式要求

- 文字语言与论文一致；
- 节点不写长段落；
- 纵向分层优先于超宽横向布局；
- 缩入 A4 后仍能识别节点和箭头；
- 图内不重复写论文 caption；
- PDF 画布边界紧贴内容，避免嵌入后缩小；
- 每张图生成后检查节点重叠、箭头穿越、裁切、字号和可读性。

## 记录

只有确实使用非数据型图且需要额外说明时，才生成 `reports/DRAWIO_REPORT.md`；否则将图清单、嵌入位置和导出限制写入本阶段的 `FIGURE_MANIFEST.csv` 和 `DRAWIO_REPORT.md`，避免重复 Markdown。技术图进入论文后，由写作阶段将对应索引状态更新为 `embedded`，再由 `11-cumcm-verify` 更新为 `verified`。
