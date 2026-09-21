# 主流模型目录清洗报告

版本：`MMC-2026-08-28-CLEAN1`

## 已完成

- 清除 `MMC-074`、`MMC-183`、`MMC-185` 等由逗号拆裂产生的伪记录。
- 将 `灰色预测GM(1,1)` 恢复为单条模型记录，并补充可确认的英文名 `Grey Model GM(1,1)`。
- 将 `(s,S)策略`、`(r,Q)策略` 恢复为完整名称，并同步模型层级和英文名。
- 同步修复 `MAINSTREAM_MODEL_CATALOG.csv`、`PROBLEM_TO_METHOD_MATRIX.csv`、`METHOD_TO_PROBLEM_INDEX.csv` 和 `MODEL_NAME_NORMALIZATION.csv`。
- 对无法可靠确认的英文名保留 `English name to be confirmed` 和 `needs_human_review=true`，不编造名称。
- 统一机器选型模式为 `adaptive_candidates_then_user_confirmation`：AI 先根据题意和数据输出候选，用户确认后锁定当前题目模型。

## 校验结果

| 文件 | 数据行 | 字段数 | 字段一致性 |
|---|---:|---:|---|
| `MAINSTREAM_MODEL_CATALOG.csv` | 319 | 27 | PASS |
| `PROBLEM_TO_METHOD_MATRIX.csv` | 86 | 11 | PASS |
| `METHOD_TO_PROBLEM_INDEX.csv` | 272 | 10 | PASS |
| `MODEL_NAME_NORMALIZATION.csv` | 267 | 8 | PASS |

已知拆裂模式扫描结果：`none`。

各机器文件 SHA-256 及锁定状态见 `CATALOG_VERSION.json`。任何文件修改后，必须重新计算哈希并生成新目录版本，不得继续使用旧版本号。
