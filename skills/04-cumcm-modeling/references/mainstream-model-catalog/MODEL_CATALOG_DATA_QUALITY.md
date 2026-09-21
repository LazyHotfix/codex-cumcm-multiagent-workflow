# 主流模型目录数据质量报告

## 当前资产

- `MAINSTREAM_MODEL_CATALOG.md`：可读场景目录。
- `MAINSTREAM_MODEL_CATALOG.csv`：319 条机器记录（清洗后）。
- `PROBLEM_TO_METHOD_MATRIX.csv`：86 个场景映射。
- `METHOD_TO_PROBLEM_INDEX.csv`：方法反向索引。
- `MODEL_NAME_NORMALIZATION.csv`：名称规范化记录。
- `MODEL_SELECTION_RULES.md`：选择规则。
- `MODEL_CATALOG_REVIEW_QUESTIONS.md`：争议项。
- `CATALOG_VERSION.json`：正式版本、文件哈希和清洗状态。

当前 `MAINSTREAM_MODEL_CATALOG.csv` 共 319 条记录、18 个题型族、86 个场景；对象类型分布为 `algorithm=222`、`model=71`、`test=9`、`metric=12`、`preprocessing=3`、`simulation=2`。其中 92 条记录被标记为需要人工复核，25 条记录要求方法确认后才能使用。

## 已发现问题

1. 已修复 `灰色预测GM(1,1)`、`(s,S)策略`、`(r,Q)策略` 的逗号拆裂，并同步正向矩阵、反向索引和名称规范表。
2. 部分记录的 `method_name_en` 仍为 `English name to be confirmed`，不能直接用于论文或反向检索；这些记录保留 `needs_human_review=true`，不擅自编造英文名。
3. 同一方法在多个场景重复出现是合理的，但需要以规范化名称和 `aliases` 去重，不能把场景重复误当成不同方法。
4. 一些记录的 `object_type` 仍需人工复核，例如检验、评价模型、求解器和算法的边界。
5. 自动生成的 `needs_human_review` 不能代替人工确认；尤其是 B/C 级方法和组合方法。

典型错位记录 `MMC-073/074` 和 `MMC-182--185` 已合并清洗；原拆裂片段不再作为独立模型记录。清洗映射和版本哈希见 `CATALOG_VERSION.json`。

## 当前使用限制

在目录版本锁定后：

- AI 应先校验 `CATALOG_VERSION.json`，再读取 CSV 和矩阵；
- 不应直接把 `needs_human_review=true` 的记录作为最终主模型；
- 不应把 S/A 等级当作无条件适用；
- 不应引入目录外创新方法作为主模型。

## 推荐修复顺序

1. 修复含逗号/括号的名称记录；
2. 补齐可确认的标准英文名，未知名称保留复核标记；
3. 去重别名并校验反向索引；
4. 生成 `CATALOG_VERSION.json` 并记录所有机器文件哈希；
5. 在建模阶段由 AI 输出候选模型，等待用户确认后锁定当前题目模型。
