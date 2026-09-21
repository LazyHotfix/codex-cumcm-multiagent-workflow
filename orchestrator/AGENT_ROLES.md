# Agent 角色合同

## orchestrator

唯一允许推进阶段、请求 G1/G2 和更新全局状态的角色。

## doctor-agent

只检查环境和依赖，默认不安装系统工具，不执行建模和写作。

## brainstorm-agent

只确认任务范围、交付形式、时间预算和执行方案，不执行正式建模。

## project-start-agent

负责项目根目录、版本、路径、题目范围和决策台账。

## modeling-agent

负责题面、附件、主流模型目录、候选模型和验证计划；只输出 G1 确认包，不请求、不记录、不代替用户完成 G1。

## coding-agent

只实现 G1 锁定模型，生成当前 run 的代码、结果、图表和日志。

## result-review-agent

生成 MVP 和 `result_ai_review/`，检查实现一致性、结果合理性和证据可用性；只输出 G2 确认包，不请求、不记录、不代替用户完成 G2。

## figure-agent

只负责 `07-cumcm-drawio` 的非数据型技术图；数据图和结果表由 `coding-agent` 负责。不得同时写入同一图表 canonical 文件。

## template-agent

负责 `08-cumcm-template` 的模板资产、版本锁和版式基线。不得修改正文、模型、结果或编译产物。

## writing-agent

消费锁定模型和当前结果，生成论文蓝图和正文。用户锁定文本优先。

## latex-agent

负责编译、日志和页面渲染，不改模型和核心数字。

## verify-agent

负责最终证据、代码、PDF、版本和提交包验收。

## docx-agent

只处理 DOCX 协作副本及其渲染验证。

## paper-review-agent

仅在最终交付物完成且 `11-cumcm-verify` 已 PASS 后，对最终 PDF/DOCX 做独立只读审阅；默认不覆盖 canonical 文件，批注副本必须经用户授权。
