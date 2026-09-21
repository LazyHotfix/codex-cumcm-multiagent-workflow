# CUMCM Orchestrator

主控编排层负责：

- 读取 WORKFLOW_STATE；
- 检查当前阶段进入条件；
- 分派专业 agent；
- 管理 G1 和 G2；
- 管理文件 owner 和写锁；
- 汇总 agent 输出；
- 处理失败回退；
- 使受影响的下游资产失效。

主控不直接替代专业 skill，也不允许专业 agent 自行递归调用下游阶段。

