# 本地重构计划

## 阶段 0：本地架构初始化

状态：已完成第一轮

- [x] 创建本地项目目录
- [x] 确定新编号
- [x] 确定主控与专业智能体边界
- [x] 确定旧 skills 不覆盖原则
- [x] 创建状态协议
- [x] 创建 agent 合同
- [x] 创建迁移矩阵
- [x] 为每个 skill 建立本地目录和初始化骨架
- [x] 迁移第一个 skill 进行试验

## 阶段 1：主控协议

状态：已完成第一轮

- [x] 阶段进入/退出条件
- [x] G1/G2 暂停协议
- [x] 失败回退协议
- [x] 文件 owner 和写锁协议
- [x] run_id 和版本传播协议
- [x] 状态初始化、校验和失效传播脚本

## 阶段 2：核心能力

状态：已完成本地重构

- [x] 01-cumcm-doctor
- [x] 02-cumcm-brainstorm
- [x] 03-cumcm-project-start
- [x] 04-cumcm-modeling
- [x] 05-cumcm-coding-visual
- [x] 06-cumcm-result-mvp
- [x] 09-cumcm-writing
- [x] 11-cumcm-verify
- [x] 13-cumcm-paper-review

## 阶段 3：辅助能力

状态：已完成适配

- [x] 07-cumcm-drawio
- [x] 08-cumcm-template
- [x] 10-cumcm-latex
- [x] 12-cumcm-docx

## 阶段 4：验证

状态：结构和协议验证中

- [x] 手工 frontmatter 和目录结构检查
- [ ] 官方 quick_validate.py 检查（当前机器的 Python 命令不可用）
- [x] 阶段注册表和状态 Schema 检查
- [x] G1/G2 门禁脚本检查
- [x] 写锁脚本检查
- [x] 锁定文本、数值、交叉引用、代码闭合和提交包审计脚本存在
- [ ] 一个真实项目 forward-test

## 阶段 5：Git 发布

本阶段暂不执行。

