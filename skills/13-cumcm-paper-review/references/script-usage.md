# 可复用脚本说明

`scripts/review_case_tool.py` 是本 skill 的通用执行层。它不替代审稿判断，只负责复制文件、抽取文本、渲染证据、生成模板、写回可见标注和验证输出。

## 运行方式

推荐在仓库根目录创建虚拟环境并安装依赖：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

之后用虚拟环境 Python 运行脚本：

```powershell
.\.venv\Scripts\python.exe -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py --help
```

macOS / Linux 可使用 `python3 -m venv .venv`，再用 `./.venv/bin/python -X utf8 ...`。

如果当前环境的 `python` 已正确指向可用解释器，也可以直接用 `python -X utf8 ...`。在 Windows 上若遇到 Microsoft Store Python alias 或中文编码问题，优先改用虚拟环境解释器。Codex 桌面环境有时会提供捆绑 Python，也可用于本地执行，但开源文档和脚本不依赖任何固定的本机绝对路径。

## Case 目录

所有试审和正式审稿使用：

```text
math-modeling-review-cases/<case-id>/
├── problem/
├── paper-original/
├── reviewed/
└── work/
```

## 常用命令

新用户不需要一次性运行全部命令。通常按这条主线走：

1. `init-case`：把材料放入本次 case。
2. `extract`：确认正文能读取。
3. `build-figure-inventory`：先拿到图表清单。
4. `match-exemplars`：有本地样例时匹配；没有样例时可以跳过。
5. `search-references`：正式审稿需要权威外部资料；不能联网时先用 `--dry-run` 生成检索词。
6. `make-figure-review-template` / `make-issues-template`：生成审稿草稿。
7. `write-docx-review` 或 `write-pdf-review`：写回同格式副本。
8. `verify-pdf` 或渲染检查：确认输出可见、无明显遮挡。
9. `build-reference-report`：生成参考来源和需确认项报告。

执行这些步骤时，建议在阶段切换前用一句话告诉用户当前目的，例如“我正在生成图表清单，先防止漏审图片和关键结果表。”

创建 case 并复制输入：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py init-case --case-dir math-modeling-review-cases\CASE_ID --problem PROBLEM_FILE --problem FORMAT_FILE --paper PAPER_FILE
```

抽取文本和粗略 profile：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py extract --case-dir math-modeling-review-cases\CASE_ID
```

渲染 PDF 并生成图表清单：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py render-pdf --case-dir math-modeling-review-cases\CASE_ID
```

检查 DOCX 内嵌图片：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py inspect-docx-media --case-dir math-modeling-review-cases\CASE_ID
```

生成结构化图表清单：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py build-figure-inventory --case-dir math-modeling-review-cases\CASE_ID
```

默认输出：

- `work/figure_inventory.json`
- `work/figure_inventory.md`

PDF 清单记录页码、图题/表题、内嵌图片 bbox 和待审状态；DOCX 清单记录段落位置、图题/表题、内嵌媒体文件名和尺寸。该清单只用于防漏审，正式图审仍需继续填写 `figure_review.json` 的证据链。

从优秀论文学习图表类型：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py build-figure-patterns --manifest math-modeling-intake\_catalog\manifest.json
```

检索权威外部资料并生成参考报告：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py search-references --case-dir math-modeling-review-cases\CASE_ID --labels "优化,图表密集,模型检验不足" --methods "线性规划,敏感性分析" --topic "生产调度优化"
```

该命令走 `agent-reach` 的 search 路由：优先调用 `mcporter + Exa MCP`，输出：

- `work/external_references.json`
- `work/external_reference_report.md`
- `work/external-reference-cards/*.card.md`

若当前终端找不到 `mcporter`，先把 npm 全局命令目录加入 PATH，或用 `--mcporter` 传入本机 `mcporter` 可执行文件路径。若 `mcporter` 尚未配置 Exa，先运行 `mcporter config add exa https://mcp.exa.ai/mcp`。本机生成的 `config/mcporter.json` 属于本地工具配置，不应随 skill 一起提交。

如果只想检查检索词，不联网：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py search-references --case-dir math-modeling-review-cases\CASE_ID --labels "预测,时间序列" --dry-run
```

匹配本地优秀论文样例：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py match-exemplars --case-dir math-modeling-review-cases\CASE_ID --labels "优化,图表密集,多问题结构" --methods "线性规划,敏感性分析" --data-tags "时间序列" --figure-tags "趋势图,结果表" --keywords "生产调度,成本,约束" --topic "生产调度优化"
```

默认输出：

- `work/exemplar_match.json`
- `work/exemplar_match_report.md`

该命令读取 `references/exemplars/index.md`，按题型、方法、数据、图表、写法、关键词和风险标签给样例排序，默认保留 8 篇候选样例和 5 篇核心样例，并输出选择理由。若存在 `math-modeling-review-cases/_learning/exemplar_feedback_log.jsonl`，会读取权威点评反馈作为轻量校准提示；反馈只影响解释和小幅排序，不会把单条点评写死为固定评分标准。正式审稿仍必须继续执行 `search-references`。

生成参考来源报告：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py build-reference-report --case-dir math-modeling-review-cases\CASE_ID
```

默认输出：

- `work/reference_report.md`
- `work/reference_report.json`

该命令汇总 `exemplar_match.json`、`external_references.json`、`issues.json`、`figure_issues.json` 和 `figure_review.json`，列出本地读了哪些样例、外部找了哪些资料、每条资料支撑什么类型的建议，以及哪些判断仍需用户提供原始数据、生成方法、脚本或中间结果。若某条资料的用途只能自动初判，报告会标明需要在具体批注中进一步确认。

运行回归测试：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py run-regression-tests
```

默认输出：

- `math-modeling-review-cases/_regression/<timestamp>/regression_manifest.json`
- 每个测试 case 的 `paper-original/`、`work/`、`reviewed/`

该命令现场生成最小 DOCX、PDF 和图审草稿，覆盖 A229/B203/C008 抽象出的 PDF 标注、DOCX 高亮、图审 JSON 和参考来源报告功能。测试输出在 `.gitignore` 排除目录内，不随开源仓库提交。详见 `references/regression-tests.md`。

生成权威点评反馈模板：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py make-feedback-template --case-dir math-modeling-review-cases\CASE_ID
```

把权威点评视频、文档或教师评语整理后的草稿转成学习记录：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py build-feedback --case-dir math-modeling-review-cases\CASE_ID --draft math-modeling-review-cases\CASE_ID\work\exemplar_feedback_draft.md
```

默认会同时写入：

- `work/exemplar_feedback.json`
- `math-modeling-review-cases/_learning/exemplar_feedback_log.jsonl`

这些反馈记录只作为后续样例匹配权重校准信号，不直接把单个点评写成固定评分标准。

生成结构化图审草稿：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py make-figure-review-template --format pdf --case-dir math-modeling-review-cases\CASE_ID
```

将图审记录转为 `figure_review.json` 和 `figure_issues.json`：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py build-figure-issues --format pdf --case-dir math-modeling-review-cases\CASE_ID --draft math-modeling-review-cases\CASE_ID\work\pdf_figure_review_draft.md
```

生成普通审稿意见草稿：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py make-issues-template --format pdf --case-dir math-modeling-review-cases\CASE_ID
```

将草稿转为 `issues.json`：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py build-issues --format pdf --case-dir math-modeling-review-cases\CASE_ID --draft math-modeling-review-cases\CASE_ID\work\pdf_issues_draft.md
```

写回 DOCX：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py write-docx-review --case-dir math-modeling-review-cases\CASE_ID --issues math-modeling-review-cases\CASE_ID\work\issues.json
```

写回 PDF：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py write-pdf-review --case-dir math-modeling-review-cases\CASE_ID --issues math-modeling-review-cases\CASE_ID\work\issues.json
```

验证 PDF：

```powershell
python -X utf8 .agents\skills\13-cumcm-paper-review\scripts\review_case_tool.py verify-pdf --case-dir math-modeling-review-cases\CASE_ID --pdf math-modeling-review-cases\CASE_ID\reviewed\PAPER_reviewed.pdf
```

默认同时输出：

- `work/<paper>_verification.json`
- `work/render_acceptance.json`
- `work/<paper>_key_pages_contact_sheet.jpg`

`render_acceptance.json` 会记录关键页是否非空、彩色定位标记像素是否达到阈值、追加提示页是否可读。若 `render_acceptance_ok` 为 false，不应直接交付，应先检查标注是否被遮挡、透明度是否失效或提示页是否未追加。

## 草稿格式

优先使用 Markdown 草稿再转换为 JSON，避免手写 JSON 的逗号、引号和数组错误。

图审草稿示例：

```markdown
---
id: fig-001
page: 4
search: 图 2 会员消费总金额占比
bbox:
title: 图 2 会员消费总金额占比
visual_type: 数据分布图
context_position: 结果分析小节，正文用该图解释会员消费结构
body_claim: 正文声称低消费会员占多数
visual_observation: 饼图类别较多，小比例标签拥挤
evidence_judgment: 部分支持
data_traceability: 分组阈值和统计脚本未在正文说明
needs_confirmation: 会员消费明细统计脚本、各类别人数和金额汇总表
content_advice: 改为横向条形图或帕累托图，补充人数、金额区间和累计占比
style_advice: 增大字号，减少扇区标签，保证黑白打印可辨
color: blue
---
```

DOCX 普通意见草稿示例：

```markdown
---
target: 原文中用于定位的一段短句
type: 建议
message: |
  问题/建议/需确认：一句话指出问题。
  原因：说明为什么影响评审或表达。
  改法：给出可执行修改方式。
---
```

PDF 普通意见草稿示例：

```markdown
---
page: 4
target: 图 2 会员消费总金额占比
type: 图表建议
message: |
  建议改为横向条形图，并补充分组阈值和样本数。
search:
bbox: 174.6, 438.1, 419.4, 610.3
color: blue
---
```

PDF 的 `bbox` 坐标格式为 `[x0, top, x1, bottom]`，对应 `pdfplumber` 页面坐标。PDF 记录必须有 `page`，且 `search` 或 `bbox` 至少填一个。

## 边界

- 脚本不替代审稿判断。
- 图表数据无法核验时必须标为“需确认”。
- PDF 标注默认使用描边框和编号，再追加提示页。
- DOCX 标注默认使用黄色原文高亮和蓝色可见提示段。
