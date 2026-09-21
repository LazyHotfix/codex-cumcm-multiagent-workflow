# 本地测试计划

## 已实现入口

在项目根目录执行：

```powershell
.\tests\run_local_smoke_tests.ps1
```

该测试不修改全局 skills，不初始化 Git，检查 14 个 skill 的目录、frontmatter、阶段合同、UTF-8 agent 配置、阶段注册表、状态示例和控制脚本。

## 阶段顺序测试

验证：

```text
doctor → brainstorm → project-start → modeling → G1
→ coding → result-mvp → G2 → drawio/template
→ writing → latex → verify → docx → paper-review
```

禁止跳过事实链阶段；可选阶段必须写入 SKIPPED 记录。

## 用户门禁测试

- brainstorming 未批准：不能进入 project-start；
- 未确认开工：不能进入 modeling；
- G1 未确认：不能进入 coding；
- G2 未确认：不能进入 drawio、template 和 writing；
- 泛化的“继续”“可以”“好的”不能确认门禁；
- 决策台账中的 packet hash 必须与状态一致。

## 版本测试

- 旧 PDF 不能被视为当前 PDF；
- 源文件变化后旧 PDF 状态失效；
- 结果变化后重新触发 3.5 和 G2；
- Word 实质修改后回流对应事实源；
- 失效传播必须写入 `reports/INVALIDATION_LOG.csv`。

## 写作测试

- 用户锁定文本必须逐字出现；
- 旧文本必须消失；
- 公式锁定时 token 不变；
- 图表重复时给出替换建议；
- 引用和表号必须可追溯；
- 结论必须绑定结果文件、代码入口和适用范围。

## 交付测试

- 提交包不能包含内部状态、临时文件和个人绝对路径；
- README 面向评委；
- 结果 Excel 不能是空模板；
- canonical PDF 和提交 PDF 哈希一致；
- 11 verify PASS 后才能进入可选 DOCX 和最终论文审阅。

