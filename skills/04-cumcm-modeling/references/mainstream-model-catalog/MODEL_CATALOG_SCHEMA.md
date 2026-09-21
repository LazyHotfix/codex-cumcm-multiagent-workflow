# 主流模型目录规范

## 记录层级

每条记录必须区分：

1. `problem_family`：题型族，如评价、优化、预测。
2. `scenario`：具体问题场景，如整数规划、时间序列趋势预测。
3. `object_type`：`model`、`algorithm`、`solver`、`test`、`metric`、`preprocessing`、`simulation`。
4. `usage_role`：`primary`、`baseline`、`alternative`、`sensitivity`、`optional`。
5. `priority_level`：S/A/B/C。

## 选择优先级

```text
human_locked
→ S 级主流方法
→ A 级成熟方法
→ 数据和题意适配
→ 验证和复现
→ B/C 级（说明必要性，C 级人工确认）
```

热门等级不等于无条件适用；每次选型必须记录前提、最低证据、未选原因和是否需要确认。

## 组合方法

组合方法拆成可追溯组件：

- `熵权法 + TOPSIS`：赋权方法 + 排序模型；
- `AHP-熵权组合`：主观赋权 + 客观赋权 + 组合规则；
- `整数规划 + 分支定界法`：问题模型 + 求解器；
- `SMOTE + 随机森林`：预处理 + 分类模型。

## CSV 规则

- 含逗号、括号、分号、斜杠或引号的字段必须使用 RFC 4180 双引号包裹；
- `GM(1,1)`、`(s,S)`、`M/M/c/K`、`A*` 等名称不得拆成多行或多个字段；
- 每行字段数必须与表头一致；
- 标准英文名未知时保留中文名并标记 `needs_human_review=true`，不写虚假英文；
- 规范化名称与别名通过 `MODEL_NAME_NORMALIZATION.csv` 维护；
- 场景重复不等于方法重复，反向索引必须保留适用场景集合。
