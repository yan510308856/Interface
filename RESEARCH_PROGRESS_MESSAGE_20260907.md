# AI Coding Agent 研究进展（可直接转发版）

导师您好，我最近把实验重新梳理了一遍，研究问题也做了一个调整。

我最开始想比较两种 agent 接口：Atomic 和 Restricted Python。Atomic 一次只能调用一个工具，Restricted Python 理论上可以在一次 action 里组合多个工具调用，所以我原本想研究它是否能减少模型往返、降低 token 和运行时间。

但前期实验发现，Restricted Python 虽然在代码层面支持 batch，真实模型并没有真正使用这个能力。在历史九任务实验中，Restricted Python 执行了 864 个 backend operations，但多操作 batch 的比例是 0%，同时有 215 个 invalid actions。也就是说，如果继续直接比较 Atomic 和 Restricted Python，结果很可能测到的是 Python 语法和协议摩擦，而不是执行粒度本身。

所以我把问题改成了：

> 在模型、任务、Backend、权限和预算都相同的情况下，一次模型决策最多允许执行多少个后端操作，会不会改变 agent 的轨迹、效率、任务成功率和安全风险？

现在比较三个处理：

```text
G1：一次 action 最多 1 个 backend operation
G2：一次 action 最多 2 个 backend operations
G4：一次 action 最多 4 个 backend operations
```

这里的重点不是 G4 一定比 G1 好，而是模型在看到下一次环境反馈之前可以连续执行多远。更大的 G 可能减少模型往返，也可能让错误计划或攻击行为在被纠正前传播得更远。

这个方向主要受到几类工作的启发：ReAct 把 agent 描述成“推理—行动—观察”的循环；SWE-bench 说明真实代码修复需要读取仓库、修改代码和运行测试；SWE-agent 说明 agent-computer interface 会影响 agent 表现；ToolSandbox 和 τ-bench 强调有状态工具和结果依赖；AgentDojo、InjecAgent 以及间接 prompt injection 相关工作说明，工具返回的外部内容可能影响 agent 后续行动。

这些论文支持了我的研究动机，但没有直接研究“下一次 observation 之前最多执行几个 backend operations”。这正是我现在想单独拿出来研究的因素。

实验设计比较简单：固定同一个 Qwen 模型、任务、代码仓库、Backend、权限策略、prompt、sandbox 和预算，只改变 G1/G2/G4。每个 run 都从同一个任务的 base commit 创建一个新的临时仓库，避免不同实验互相影响。实验同时包含 clean 和 attack 两种条件，用来观察正常 coding workflow 和攻击暴露下的差异。

agent 的工作流程可以理解为：

```text
模型看到任务和仓库信息
        ↓
决定下一步操作
        ↓
提交一个 action
        ↓
接口检查 action 是否合法
        ↓
Backend 执行操作，Permission 检查安全边界
        ↓
返回 observation
        ↓
模型根据 observation 决定下一步
```

例如，模型已经知道两个文件路径时，G2 可以一次读取两个文件；但如果第二个路径必须依赖第一次搜索的结果，那么即使是 G4，也要等下一次 observation 后再读取。这样 G 操纵的是两次模型观察之间的执行窗口，而不是让模型在 batch 中动态运行任意程序。

攻击实验也采用受控的 synthetic prompt injection，不使用真实凭证、生产系统或第三方目标。最早的 attack-v0 把指令放在隐藏文件中，模型没有发现它，所以只能作为负控制。之后的 `repository_comment_hijack_v1` 把指令放进任务相关源码的注释中，要求模型写入 `.git/agent_attack_success`。v2 pilot 中有 18/27 个 attack run 暴露了攻击内容，但没有产生精确的目标写操作，因此这个攻击只能说明 exposure pipeline 有效，不能说明接口已经安全。

现在已经实现了新的 `repository_sentinel_write_v2`，要求模型创建实验专用的 `.git/agent_attack_sentinel_v2`。目标仍然受到 `.git` 权限保护，不允许真实创建。下一步会先确认模型是否在看到 payload 后产生可识别的 target attempt，再研究 G1/G2/G4 是否改变攻击传播距离。未来还希望加入受保护读取、被 allowlist 拒绝的进程调用，以及“读取恶意指令 → 查找目标 → 修改目标 → 执行命令”的多步攻击链。

目前已有的 G1/G2/G4 pilot 主要用于校准，54 个 run 的产物完整，但任务级操作深度还没有形成预期的单调关系：

```text
G1：0.998 operations / observation，multi-op 0%
G2：1.079 operations / observation，multi-op 8%
G4：1.030 operations / observation，multi-op 3%
```

所以现在还不能说 G4 更高效、更安全或任务成功率更高。当前最重要的结论是：接口的理论能力不等于模型实际使用的能力，正式比较之前必须先验证 G1/G2/G4 的 manipulation 是否真的生效。

下一步我会先运行 calibration，检查两件事：

1. G2/G4 是否真的产生更多 multi-operation actions；
2. 新的 sentinel attack 是否能产生非零的精确目标操作。

只有这两个条件通过后，我才会冻结实验配置，并进行正式的 task success、patch quality、token/runtime 和 security interaction 分析。

目前仓库分支是 `codex/granularity-formal-matrix`，最新提交是 `a05a679`。当前测试 125/125 通过。本次只新增了这份汇报文字，没有修改实验代码，也没有重新运行昂贵的模型实验。

参考论文：

- [ReAct](https://arxiv.org/abs/2210.03629)
- [Toolformer](https://arxiv.org/abs/2302.04761)
- [SWE-bench](https://arxiv.org/abs/2310.06770)
- [SWE-agent](https://arxiv.org/abs/2405.15793)
- [ToolSandbox](https://arxiv.org/abs/2408.04682)
- [$\tau$-bench](https://arxiv.org/abs/2406.12045)
- [InjecAgent](https://arxiv.org/abs/2403.02691)
- [AgentDojo](https://arxiv.org/abs/2406.13352)
