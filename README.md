# 高教杯数学建模 Skills Local

这是面向中国高校“高教杯”数学建模竞赛场景的本地多智能体 Skills 重构项目。项目内部保留 `CUMCM` 作为历史兼容和机器工作流标识，用户可见名称统一使用中文高教杯名称。

当前状态：本地 14 个 skill、总控协议、状态/门禁/写锁脚本和迁移资产已完成第一轮可验收版本，并已推送到 GitHub 私有仓库。项目仍未覆盖现有 Codex 全局 skills。

## 命名约定

Codex 官方校验器要求 frontmatter 的 `name` 使用英文小写、数字和连字符，因此：

- 文件夹名和 `name` 是稳定的机器调用标识；
- `agents/openai.yaml`、标题、README 和界面说明使用中文高教杯名称；
- 详细对应表见 [docs/SKILL_NAMING.md](docs/SKILL_NAMING.md)。

例如：

```text
机器调用：$04-cumcm-modeling
中文名称：高教杯建模设计
```

## 设计目标

- 使用高教杯专用的英文机器编号和中文用户名称；
- 将长流程拆成总控与专业 agent；
- 使用统一状态、决策台账、版本、哈希和交付物协议；
- 保留 G1 建模确认和 G2 结果确认；
- 让题面、模型、代码、结果、图表、论文、PDF 和提交材料可追溯；
- 新系统通过结构和回归验证后，再考虑同步到全局 skills；
- 最后再创建 Git 仓库和发布。

## 运行边界

1. 本地项目是新系统实验区。
2. 当前 Codex 全局 skills 目录（通常为 `$CODEX_HOME/skills`）是运行系统，本阶段不修改。
3. 专业 agent 默认只输出报告或候选补丁，由 orchestrator 统一合并。
4. 同一个 canonical 文件同一时刻只能有一个 owner 锁。
5. G1、G2、11-cumcm-verify 和最终 13-cumcm-paper-review 是硬门禁。
6. Word 是协作副本，不能替代 LaTeX、代码或结果事实源。

## 新流程

```text
01-cumcm-doctor
→ 02-cumcm-brainstorm
→ 03-cumcm-project-start
→ 04-cumcm-modeling
→ G1-model-confirmation
→ 05-cumcm-coding-visual
→ 06-cumcm-result-mvp
→ G2-result-confirmation
→ 07-cumcm-drawio（按需）
→ 08-cumcm-template
→ 09-cumcm-writing
→ 10-cumcm-latex
→ 11-cumcm-verify
→ 12-cumcm-docx（按需）
→ 13-cumcm-paper-review
```

`00-cumcm-orchestrator` 是控制平面，不作为普通阶段执行。

## 已完成能力

- 14 个本地 skill 的 frontmatter、阶段合同和 agent 配置；
- 阶段注册表、状态 Schema、决策台账、失效传播和写锁协议；
- G1/G2 硬暂停与确认记录；
- 主流模型目录、中文模板、结构化写作蓝图和论文审阅资产归档；
- 本地 skill 结构校验、状态校验、门禁更新、锁管理、提交包审计和确定性回归入口。

## 验证

在本地项目根目录执行：

```powershell
.\\tests\\run_local_smoke_tests.ps1
```

Python 控制脚本不依赖第三方包；官方 quick_validate 需要可用的 Python/YAML 环境。

## Quick Start

首次使用建议按下面顺序操作：

```powershell
cd "<项目根目录>"
.\tests\run_local_smoke_tests.ps1
```

冒烟测试只检查本地 skill 结构、阶段协议和确定性控制脚本，不代表真实题目已经完成求解或论文验收。真实项目应另建项目目录，先运行 `01-cumcm-doctor`，再由 `00-cumcm-orchestrator` 按阶段推进；不要把真实题目、个人数据或运行报告直接提交到本仓库。

当前仓库保持私有，许可证和真实高教杯 forward-test 尚未完成前，不建议公开为 Public。

## 目录

- `skills/`：14 个编号 skill；
- `orchestrator/`：总控状态机和 G1/G2 协议；
- `shared/`：状态、阶段、决策和写锁 Schema；
- `scripts/`：确定性状态与交付审计脚本；
- `tests/`：fixtures 和本地冒烟测试；
- `docs/`：迁移、命名、测试和验收记录。

公开到 GitHub 前请先阅读 [GitHub 发布前清单](docs/PUBLIC_RELEASE_CHECKLIST.md)。许可证和 `archive/` 资产公开权限需要由项目维护者单独确认。


