---
name: 12-cumcm-docx
description: "在高教杯验收通过后生成可编辑的 Word 协作副本，渲染检查布局，并把实质修改分类回流到正确事实源。"
---

# 12 高教杯 Word 协作副本

## 阶段合同

```yaml
phase_id: 12-cumcm-docx
display_name: 国赛 Word 协作
owner_agent: docx-agent
entry_conditions:
  - 11-cumcm-verify 已写入 VERIFY_REPORT.md 且为 PASS
  - 用户明确需要 DOCX，或交付合同要求 DOCX
inputs:
  - 已通过验收的 PDF 和 LaTeX 工程
  - paper/PAPER_BLUEPRINT.md、模板锁和最终结果索引
  - 队友修改后的 DOCX（回流任务时）
actions:
  - 从当前 PDF/LaTeX 生成协作副本，不把 PDF 转换结果当作新的事实源
  - 使用 render_docx.py 或等价工具渲染每页并检查分页、公式、图表和字体
  - 将队友修改分类为措辞、结构、数字/图表、模型/公式、代码结果、模板和引用
outputs:
  - deliverables/paper_collaboration.docx
  - reports/DOCX_RENDER_AUDIT.md
  - reports/DOCX_CHANGE_CLASSIFICATION.csv
  - reports/DOCX_RETURN_PACKET.md
exit_conditions:
  - DOCX 渲染通过，所有队友修改都有分类、证据和回流阶段
failure_return:
  - 布局失败：返回 12；数字/模型/引用实质变化：返回责任阶段并使 11/13 失效
writable_paths:
  - deliverables/paper_collaboration.docx
  - reports/DOCX_RENDER_AUDIT.md
  - reports/DOCX_CHANGE_CLASSIFICATION.csv
  - reports/DOCX_RETURN_PACKET.md
read_only_paths:
  - paper/、code/、results/、figures/、reports/VERIFY_REPORT.md
invalidates:
  - DOCX 中任何事实、数字、公式、图表、结构或模板变更使受影响的写作/编译/验收/终审状态失效
user_gate: false
```

## 协作规则

1. DOCX 只是协作副本，不是 canonical 论文源；不得凭感觉把 DOCX 修改回填到 LaTeX。
2. 只改措辞可交给 paper-review；改章节结构回到 writing；改数字、表格或图回到结果索引和 coding；改模型、公式或约束回到 modeling 并重新 G1；改模板参数回到 template；改引用重新检查 verify。
3. 生成后必须渲染 DOCX 逐页检查，检查公式是否仍为可读对象、图表是否裁切、标题是否孤立、页眉页脚是否异常。
4. 任何无法判断的修改标为 NEEDS_USER_CONFIRMATION，不静默合并。
5. 本阶段不请求 G1/G2、不修改 WORKFLOW_STATE，不宣称最终交付通过；由 orchestrator 根据回流包推进。

## 交付顺序

LaTeX 工程 → PDF → 11 verify PASS → DOCX 协作副本 → 队友修改 → 变化分类 → 回流责任阶段 → 重新验收。
*** End Patch
