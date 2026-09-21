# 优秀论文样例

用户可将国赛优秀论文样例放入项目的 `math-modeling-intake/优秀论文/`。样例入库后，运行 `math-modeling-intake/_tools/build_catalog.py` 生成 `math-modeling-intake/_catalog/sample-index.md` 和卡片，并同步更新本目录的 `index.md`。若只需要同步索引，运行 `../scripts/sync_exemplar_index.py`。后续审稿优先读取本目录的 `index.md`，再按标签定位样例卡片。

建议结构：

```text
math-modeling-intake/
├── 优秀论文/
└── _catalog/
    ├── sample-index.md
    └── cards/
        └── 2024/
            └── 2024-001.md

.agents/skills/13-cumcm-paper-review/references/exemplars/
├── README.md
├── index.md
└── external/
    └── EXT-2024-ARXIV-01.card.md
```

使用样例时遵守：

- 只参考结构、表达方式、图表组织和摘要写法。
- 不复制样例中的具体内容、数据、图表或结论。
- 样例与默认国赛标准冲突时，以用户指定标准和当次题目要求为准。
- 如果样例很多，先筛选 5-8 篇候选，再精读 3-5 篇核心样例或卡片；如果样例不足，使用全部可用候选并说明局限。
- 正式审稿不只依赖本地样例；无论本地匹配度如何，都必须联网检索权威外部资料并记录选择理由。

## 推荐样例卡片

每篇样例在 `math-modeling-intake/_catalog/cards/<year>/` 下生成一个卡片文件，只保存低 token 信息：

```markdown
# 样例编号：CUMCM-2024-A-01

- 文件：cumcm-2024/paper-a.docx
- 赛题/方向：
- 题型标签：
- 方法标签：
- 数据标签：
- 图表标签：
- 结构标签：
- 亮点标签：
- 适合参考：
- 不适合参考：
- 简短总结：
- 关键词：
```

## 索引原则

`index.md` 只写样例卡片摘要和标签，不粘贴长段原文。审稿时先读索引，只有匹配后才读取具体样例或卡片。

## 外部参考

正式审稿必须在 `external/` 下放置或更新网络检索得到的外部参考卡片。外部参考可以来自数模论文、学术论文、综述、方法论文、教材级资料或官方文档，但只保存来源信息、检索日期、可信度、标签、摘要级总结、关键词、可借鉴写法和用于支撑的审稿判断，不保存论文正文。
