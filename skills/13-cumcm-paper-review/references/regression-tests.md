# 回归测试说明

## 目标

用可重复生成的最小测试材料保护审稿脚本的关键能力，避免以后修改脚本时破坏：

- PDF 可见描边标注和追加提示页。
- PDF 关键页渲染验收，包括彩色定位标记、非空页面和追加提示页可见性。
- DOCX 原文高亮和可见提示段。
- PDF/DOCX 图表清单 `figure_inventory.json`。
- 图审草稿到 `figure_review.json` / `figure_issues.json` 的转换。
- `reference_report.md` 对本地样例、外部资料和需确认项的汇总。

## 命令

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py run-regression-tests
```

默认输出到：

```text
math-modeling-review-cases/_regression/<timestamp>/
```

该目录已被 `.gitignore` 排除，不随开源仓库提交。

## 真实试审案例映射

这些测试由早期试审案例抽象而来，但不依赖私有原文：

| 原试审案例 | 抽象测试 | 保护能力 |
|---|---|---|
| A229 | `A229-pdf-markup` | PDF 中原文定位、WPS 可见描边标注、追加提示页、applied JSON |
| B203 | `B203-docx-highlight` | DOCX 黄色原文高亮、蓝色可见提示段、review notes |
| C008 | `C008-figure-json` | 图审证据链、`needs_confirmation`、`figure_review.json`、`figure_issues.json` |
| 新增抽象 | `figure-inventory` | PDF/DOCX 图题、表题和内嵌媒体清单 |

## 通过条件

- `B203-docx-highlight`：生成 reviewed DOCX；`*_docx_review_applied.json` 中 1 条 applied、0 条 missing；DOCX XML 中存在高亮和“审阅提示”。
- `A229-pdf-markup`：生成 reviewed PDF；页数至少为原文页 + 提示页；applied JSON 中无 missing，且有 applied 项。
- `A229-pdf-markup`：`render_acceptance.json` 中彩色定位标记、关键页非空和追加提示页可见性验收通过。
- `figure-inventory`：PDF 和 DOCX fixture 均生成 `figure_inventory.json`，且能识别最小样例中的 `图 1` 图题。
- `C008-figure-json`：生成 `figure_review.json` 和 `figure_issues.json`；`needs_confirmation` 转换为“需确认”批注，并要求用户提供材料。
- `reference-report`：生成 `reference_report.md`，包含本地样例、外部资料和仍需用户确认的数据项。

## 使用边界

- 回归测试只验证脚本结构能力，不替代真实论文审阅质量检查。
- 测试 fixture 是最小样例，不包含用户论文内容、题目内容或优秀论文全文。
- 若修改 PDF/DOCX 写回、图审 JSON、参考报告逻辑，提交前必须运行该命令。
