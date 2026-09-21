# 上游资产边界

`12-cumcm-docx` 是对 bundled `documents:documents` 能力的 CUMCM 协作层适配，不复制插件运行时。

- DOCX 生成、渲染和页面检查使用当前环境中可用的 documents skill。
- 本地阶段只管理协作副本、回流事实源和渲染验收记录。
- Word 不得成为模型、结果、公式或最终 PDF 的事实源。
