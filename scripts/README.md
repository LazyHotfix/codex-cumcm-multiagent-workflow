# Local Scripts

这里保存不依赖第三方包的确定性检查脚本。脚本从项目根目录运行时可直接使用：

```text
python scripts/check_locked_text.py <path> --required "锁定句" --forbidden "旧句"
python scripts/check_numeric_consistency.py <path>
python scripts/check_crossrefs.py <paper-or-project>
python scripts/audit_code_closure.py <code-dir> --entry run_all.py
python scripts/audit_submission_package.py <submission-dir> --required main.pdf
python scripts/validate_skill_layout.py --root <local-skills-project>
python scripts/propagate_invalidation.py --state <project>/reports/WORKFLOW_STATE.json --source-asset result:run-1 --affected-asset paper:main --reason "核心结果变化" --rerun-phase 09-cumcm-writing --invalidate-gate g2
```

统一退出码：

- `0`：检查通过；
- `1`：发现审计问题；
- `2`：参数、输入路径或运行错误，不能可靠完成检查。

默认输出人读摘要和逐条问题。添加 `--json` 输出机器可读 JSON；添加
`--json-output PATH` 可在保留摘要的同时写入 JSON 文件。所有脚本都支持
`--help`，不依赖 Conda、第三方 Python 包或联网服务。
## Workflow controls

这些脚本只使用 Python 标准库，不需要安装第三方包：

- `init_workflow_state.py`：初始化 `reports/WORKFLOW_STATE.json`、`reports/DECISION_LEDGER.yaml` 和写锁目录。
- `validate_workflow_state.py`：校验状态文件与 `shared/PHASE_REGISTRY.json` 的阶段、门禁和交付字段。
- `update_gate.py`：由 orchestrator 记录明确的 G1/G2 用户确认；专业 agent 不得直接调用它代替用户确认。
- `manage_write_lock.py`：为 canonical 文件取得和释放 owner 写锁。
- `validate_skill_layout.py`：不依赖 PyYAML 检查 14 个本地 skill 的目录、frontmatter、阶段合同字段和 agent 配置。
- `propagate_invalidation.py`：登记事实源变更，标记受影响资产失效并按显式参数使 G1/G2 失效。

统一退出码：0=通过，1=发现问题或冲突，2=命令/路径/输入错误。

官方 skill 结构校验（需要 PyYAML）可用以下命令运行。请把 `<python-with-pyyaml>` 和 `<quick_validate.py>` 替换为本机路径：

```powershell
$env:PYTHONUTF8 = "1"
<python-with-pyyaml> <quick_validate.py> <skill-dir>
```

`tests/run_local_smoke_tests.ps1` 不假设固定 Python 安装位置；如需让它执行官方校验，可设置 `QUICK_VALIDATE` 环境变量并把带 PyYAML 的 Python 放入 PATH。
