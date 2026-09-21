---
name: 10-cumcm-latex
description: "处理高教杯 LaTeX 双次编译、日志、交叉引用、版式修复和页面渲染。"
---

# 高教杯论文编译与页面验收

## 阶段合同（机器接口）

- phase_id: 10-cumcm-latex；display_name: XeLaTeX 编译与页面检查；owner_agent: latex-agent。
- entry_conditions: 09 phase_result=READY_FOR_LATEX；08 template_lock 可读。
- inputs: paper/ LaTeX 工程、模板锁、图表、参考文献和编译环境。
- outputs: paper/main.pdf、编译日志、交叉引用报告、页面 PNG 和 PDF_SHA256。
- exit_conditions: 至少双次 XeLaTeX 编译完成，日志无未解决引用/致命错误，页面渲染可读。
- failure_return: 语法/交叉引用返回 10；内容或图表事实返回 09/05；环境返回 01。
- writable_paths: paper/build/、paper/main.pdf、reports/LATEX_BUILD_REPORT.md、reports/LAYOUT_AUDIT.csv。
- read_only_paths: 模型、结果、正文事实源和模板原件。
- invalidates: PDF、字体、页面或交叉引用变化使 11 和 13 失效。
- user_gate: false。
## 本地多智能体合同
- owner_agent：latex-agent；
- 只处理 LaTeX 语法、编译、交叉引用和页面排版；
- 不修改模型、核心数字或结果口径；
- 至少双次编译并记录日志和 PDF 哈希；
- 退出状态：COMPILED 或 BLOCKED。

本 skill 提供 LaTeX/Typst 的通用语法、图片/表格插入、交叉引用、编译和基础排版帮助。它不是 CUMCM 的主写作入口。

## CUMCM 路由

当任务属于全国大学生数学建模竞赛（CUMCM/国赛）时，必须按以下顺序工作：

```text
08-cumcm-template
→ 09-cumcm-writing
→ 本 skill 的 LaTeX 编译与语法支持
→ 11-cumcm-verify
```

不得先用通用模板生成一篇简略论文，再靠后续提示词补表、补图或补附录。国赛固定优先使用用户自制 `zh/cumcm-structured-latex` 和 `cumcmthesis.cls`；不在启动阶段询问 Typst。

## 通用支持范围

- LaTeX/Typst 章节组织和交叉引用；
- 表格、图形、公式、参考文献和代码 listing 语法；
- XeLaTeX 双遍编译、日志检查和路径诊断；
- 在不改变模型和数字的前提下提供排版修复。

## 边界

本 skill 不负责决定 CUMCM 章节结构、证据包、结果覆盖、模型选择、完整代码附录策略或最终 PASS/FAIL。所有国赛内容和结构规则以 `09-cumcm-writing`、`08-cumcm-template` 和 `11-cumcm-verify` 为准。
