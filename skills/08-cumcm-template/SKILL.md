---
name: 08-cumcm-template
description: "锁定并验证高教杯论文模板、类文件、入口文件、版式参数和哈希。"
---

# 高教杯结构化 LaTeX 模板规范

## 阶段合同（机器接口）

- phase_id: 08-cumcm-template；display_name: 模板锁定；owner_agent: template-agent。
- entry_conditions: G2.status=CONFIRMED；项目模板来源和老师要求已确定。
- inputs: 本地 templates/zh/cumcm-structured-latex、模板版本、老师版式要求。
- outputs: template_lock.json、模板哈希清单、版式基线和 paper/ 模板副本。
- exit_conditions: cumcmthesis.cls、main.tex 和版本清单哈希锁定；phase_result=LOCKED。
- failure_return: 模板缺失/哈希冲突返回 08；编译错误返回 10。
- writable_paths: skills/08-cumcm-template/templates/、reports/TEMPLATE_LOCK.json、paper/模板副本。
- read_only_paths: 原始老师模板、模型、结果、代码和正文内容。
- invalidates: 类文件、模板版本或版式参数变化使 09、10、11、12、13 失效。
- user_gate: false；老师专用模板替换需要 orchestrator 记录 scope 决策。
## 本地多智能体合同
- owner_agent：template-agent；
- 锁定 template_path、模板版本和文件哈希；
- 不擅自替换用户确认模板；
- 模板哈希变化必须使写作和验收状态失效；
- 退出状态：LOCKED 或 BLOCKED。

本 skill 只服务全国大学生数学建模竞赛（CUMCM）。用户已确认主模板为自制：

```text
模板族：zh/cumcm-structured-latex
核心类文件：cumcmthesis.cls
工程入口：main.tex
参考工程：由项目目录或用户提供的模板工程复制到当前项目；发布包不携带个人绝对路径。
```

模板资产位于本 skill 的 `templates/zh/cumcm-structured-latex/`。项目中若存在更新的老师模板，老师模板优先；否则复制该模板工程到独立论文目录，保留 `cumcmthesis.cls` 原文件，不改写原始模板。

模板版本以模板工程中的 `TEMPLATE_VERSION.json` 为准。当前基准为 `CUMCM-STRUCTURED-2025-08-09-v2.8`，核心文件哈希、来源和锁定参数必须在复制到项目时写入项目的 `run_manifest.json` 或等价元数据。未经用户明确批准，不得修改 `cumcmthesis.cls`；修改类文件后必须生成新模板版本并重新编译、渲染和验收。

## 固定版式

- 中文 XeLaTeX；连续编译至少两遍；
- 摘要标题为“摘　要”，标签为“关键词：”；
- 摘要采用背景框架段、逐问段、创新段结构；
- 模型假设使用简洁阿拉伯数字编号；
- 图题在图下，表题在表上；优先矢量 PDF；
- 参考文献独立起页，正文使用真实右上角上标引用；
- 参考文献结束后 `\clearpage`，附录再次独立起页；
- 附录首页先放真实代码结构与运行关系图，再放清单和完整源码；
- 主要代码模块自然分页，避免标题孤立、代码裁切和异常空白。

## 已核对的基准参数

`cumcmthesis.cls` 当前基准实际包含：A4 单栏；`top=25mm,bottom=25mm,left=25mm,right=25mm`；正文 `\baselinestretch=1.38`；首行缩进 `2em`；正文主字体由类文件设置；一级标题居中加粗，二级标题常规加粗，三级标题常规加粗；中文一级编号为“ 一、 ”形式，二级为“1.1”，三级为“1.1.1”；图题在 `\caption` 位置置于图下，表题在 `\caption` 位置置于表上；摘要标题由 `main.tex` 覆盖为“摘　要”，关键词标签覆盖为“关键词：”。这些参数是验收基线，不在写作阶段凭空改写。

## 行文到模板的映射

`09-cumcm-writing` 的 A–E 论证功能必须映射为可读的 LaTeX 层级，但 A–E 是功能协议而不是固定标题协议。模板只约束 section/subsection/subsubsection 的层级、编号和版式；具体标题由题型、数据结构和模型链自适应生成，并在 `PAPER_BLUEPRINT.md` 以 `function_tags` 登记：

```text
\section{问题 X 的建模与求解}
  总起段（本问目标、输入输出和路线）
  \subsection{自适应标题}           % function_tags: A
  \subsection{自适应标题}           % function_tags: B 或 B,D
  \subsection{自适应标题}           % function_tags: C
  \subsection{自适应标题}           % function_tags: D
    \subsubsection{模型建立}
    \subsubsection{求解算法}
    \subsubsection{结果分析}
  \subsection{自适应结论标题}       % function_tags: E
```

允许根据题型在 D 内增加“稳健性检验”“敏感性分析”等三级标题，也允许一个小节承担多个功能或一个功能分散到多个小节，但不得跳过 A–E，也不得为了凑篇幅重复标题。标题文字应与 `PAPER_BLUEPRINT.md` 一致；模板只负责呈现层级，不负责替换已确认模型。验收按 `function_tags` 和正文语义检查，不按固定标题字符串机械判定。

## 实际问题数适配

`main.tex` 中的 `\\input{sections/4_problem1}` 至 `\\input{sections/7_problem4}` 只是四问基准工程，不代表每道题固定四问。复制模板后必须按题面实际顶层问题数更新输入清单：删除不存在问题的空文件和 `\\input`，保留实际问题的连续编号，不得用空白章节、占位文字或虚构问题填满四问。灵敏度分析、模型评价、参考文献和附录只在有对应证据时保留。

## 编译与页面门禁

正式论文必须使用 XeLaTeX，从独立论文目录连续编译至少两遍；编译前检查所有 `\\input`、图片、参考文献和代码路径存在，编译后检查未定义引用、缺图、致命错误和明显 `Overfull \\hbox`。必须渲染 PDF 页面进行视觉检查，确认摘要/关键词、标题层级、图表题注、公式、参考文献和附录分页正常；仅“编译成功”不能视为模板通过。

## 与工作流的关系

```text
03-cumcm-project-start → 04-cumcm-modeling → 05-cumcm-coding-visual → 07-cumcm-drawio
→ 本模板 + 09-cumcm-writing → 11-cumcm-verify
```

模板只负责版式和入口，不替代证据包、结果索引、模型选择、代码复现或验收门禁。国赛不得使用通用 `10-cumcm-latex` 模板先生成简略论文，也不得混入 Typst、华数杯、MCM/ICM 或其他比赛格式。
