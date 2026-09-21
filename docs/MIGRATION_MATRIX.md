# 旧 Skills 到新 Skills 的迁移矩阵

旧名称只保留在“来源”列作为追溯信息，不再作为本地 skill 主名称。

| 新编号 | 新名称 | 来源 | 本地状态 | 资产边界 |
|---|---|---|---|---|
| 00 | cumcm-orchestrator | 新建 | 已完成首版迁移 | 总控协议、状态、门禁、锁和失效传播 |
| 01 | cumcm-doctor | doctor | 已完成本地重构 | 保留环境预检职责，不自动安装系统工具 |
| 02 | cumcm-brainstorm | brainstorming | 已完成迁移 | 已归档规范提示和视觉 companion 脚本 |
| 03 | cumcm-project-start | 1start-mathmodel | 已完成本地重构 | 现场恢复、版本审计、范围和台账 |
| 04 | cumcm-modeling | 2analysis-modeling | 已完成迁移 | 已归档主流模型目录；本地规则优先 |
| G1 | model-confirmation | 新建门禁 | 已完成协议 | 由 orchestrator 唯一写入确认 |
| 05 | cumcm-coding-visual | 3coding-visual | 已完成本地重构 | 代码、结果、数据图和结果索引 owner |
| 06 | cumcm-result-mvp | 3-5-result-mvp | 已完成本地重构 | MVP、result_ai_review 和 G2 包 |
| G2 | result-confirmation | 新建门禁 | 已完成协议 | 由 orchestrator 唯一写入确认 |
| 07 | cumcm-drawio | 4drawio | 已完成本地重构 | 只生成非数据型技术图 |
| 08 | cumcm-template | cumcm-official-template | 已完成迁移 | 已归档中文 CUMCM LaTeX 模板和版本清单 |
| 09 | cumcm-writing | 5writing-structured | 已完成迁移 | 已归档结构化章节蓝图；消费 G2 后结果 |
| 10 | cumcm-latex | 5writing | 已完成适配层 | 不复制旧英文模板；只负责编译和页面验收 |
| 11 | cumcm-verify | 6verity | 已完成迁移 | 已归档 writing_check.sh 和提交包审计规则 |
| 12 | cumcm-docx | documents:documents | 已完成适配层 | 使用 bundled documents runtime，不重复 vendoring |
| 13 | cumcm-paper-review | math-modeling-paper-review | 已完成迁移 | 已归档国赛审阅参考资料和 review_case_tool.py |

## 迁移原则

- 全局旧 skill 只读，不覆盖、不重命名、不移动；
- 旧 skill 的通用能力经过 CUMCM 阶段合同重写后进入本地编号目录；
- 大型外部运行时只登记接口边界，不复制到本地项目；
- 每个本地 skill 的 `SKILL.md`、`agents/openai.yaml`、`references/` 和 `scripts/` 都必须存在。

