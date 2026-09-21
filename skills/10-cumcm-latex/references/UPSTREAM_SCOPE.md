# 上游资产边界

`10-cumcm-latex` 是本地 CUMCM 编译阶段适配层，不复制旧 `5writing` skill 的全部英文模板和运行时资产。

- 中文 CUMCM 模板唯一来源：`skills/08-cumcm-template/templates/zh/cumcm-structured-latex/`。
- 编译阶段只消费项目 `paper/` 中已锁定的 canonical LaTeX 工程。
- 如需 XeLaTeX、字体或 PDF 渲染工具，由 `01-cumcm-doctor` 检查环境；本 skill 不安装系统工具。
