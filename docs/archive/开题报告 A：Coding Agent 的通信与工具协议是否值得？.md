# 开题报告 A：Coding Agent 的通信与工具协议是否值得？
## ——代码智能体中 Capability–Safety–Efficiency Trade-off 的实证研究

### 1. 暂定题目

**英文题目候选**

> **Are Sophisticated Agent Interactions Worth It? An Empirical Study of Communication and Tool-Protocol Trade-offs in Coding Agents**

更偏 FSE 风格：

> **Beyond Task Success: An Empirical Study of Communication, Tool Integration, and Behavioral Safety in Coding Agents**

更强调 MCP：

> **MCP or Native Tools? An Empirical Study of Effectiveness, Safety, Latency, and Cost in Coding Agents**

---

# 2. 研究背景

2024–2026 年，LLM-based coding systems 已经从单轮代码生成快速发展成能够自主浏览 repository、读取文件、执行 shell、运行测试、修改代码并进行多轮调试的 Agent 系统。

SWE-agent 的重要发现之一就是：

> Agent 最终表现并不只由 backbone LLM 决定，**Agent–Computer Interface 本身就是重要设计变量**。

其专门设计的 Agent-Computer Interface 显著改善了 Agent 编辑文件、搜索 repository 和执行程序的能力。

之后出现了不同设计哲学：

- **AutoCodeRover**：强调 program analysis / code search 与 LLM agent 的结合；
- **MAGIS**：将 GitHub issue resolution 拆给多个不同角色的 agents；
- **OpenHands**：采用通用 event-driven architecture，为 Agent 提供代码、shell 和网页等交互能力；
- **Agentless**：反过来证明不使用复杂 autonomous agent，通过 localization → repair → validation 的简单流程仍然可以获得有竞争力的效果与较低成本。

因此目前 coding-agent 领域实际上存在巨大的系统设计空间：

```text
                     Coding Agent
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
     Architecture     Communication      Tool Access
          │               │                │
     Single/Multi     Ad-hoc/Typed      Native/MCP
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                    Agent Trajectory
                          │
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
   Correctness          Safety           Efficiency
                                          │
                                      Time / Cost
```

但现有研究往往只研究其中一块。

---

# 3. 与 Behavior Safety Survey 的关系

《Behavior Safety of Autonomous Interactive Agents》明确指出，现代 Agent 的风险已经不能只在最终输出层理解，而应该考察：

- Foundation model；
- Memory；
- Tool invocation；
- Multi-agent collaboration；
- Communication protocol；
- Third-party extension；
- Runtime permission/resource management。



尤其值得本课题借鉴的是两个观点。

第一：

> **能力增强和安全风险可能同时增加。**

例如 Tool、Agent 数量、交互轮次和 trajectory length 增长会增强自主能力，但也扩大攻击面。

第二：

> **Task Success ≠ Behavior Safety。**

Survey 指出，仅评价最终 task completion 会掩盖 execution trajectory 中发生的 distraction、invalid execution、unsafe tool invocation 等行为失败。

因此本研究拟把：

\[
\text{Agent Design}
\]

与：

\[
\text{Correctness},
\text{Safety},
\text{Time},
\text{Cost}
\]

放进同一个 empirical framework。

---

# 4. 相关工作

## 4.1 Coding Agent Architecture

### SWE-agent — NeurIPS 2024

**SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering**

核心意义不是又提出了一个 Agent，而是证明：

> interface / harness design 会显著影响软件工程 Agent 的行为和性能。



这篇论文是本课题最重要的思想基础之一。

---

### AutoCodeRover — ISSTA 2024

**AutoCodeRover: Autonomous Program Improvement**

将 LLM 与结构化 code search / analysis 结合，用于真实 GitHub issue resolution。

说明：

> Tool design 本身可能显著改变 Agent performance。

---

### MAGIS — NeurIPS 2024

**MAGIS: LLM-Based Multi-Agent Framework for GitHub Issue Resolution**

采用 multi-agent division of labor 解决 GitHub issues，并在 SWE-bench 上获得优于直接使用 LLM 的表现。

它提供了本研究研究：

\[
Single\ Agent
\quad vs\quad
Multi-Agent
\]

的现实基础。

---

### OpenHands — ICLR 2025

**OpenHands: An Open Platform for AI Software Developers as Generalist Agents**

提供可扩展的 event-driven agent architecture，非常适合作为后续 controlled experiment platform。

---

### Agentless — FSE 2025

**Demystifying LLM-Based Software Engineering Agents**

使用 localization → repair → validation 的简单流程，而非复杂自主 Agent，并展示了有竞争力的 SWE-bench 效果和低成本。

它对本研究尤其重要，因为它提醒我们：

> **More Agent ≠ Better Agent。**

增加 communication、tool、autonomy 的收益必须和成本一起衡量。

---

# 5. 已有 Configuration / Harness 研究

2026 年开始出现一类与本课题高度相关的新文献。

## Configuring Agentic AI Coding Tools

该研究系统分析：

- Claude Code；
- GitHub Copilot；
- Cursor；
- Gemini；
- Codex；

中的 configuration mechanisms，并归纳出 Context Files、Skills、Subagents、Commands、Rules、Settings、Hooks、MCP 等机制。

其 GitHub empirical study 说明 coding-agent configuration 已经成为真实工程实践的一部分。

但它主要回答：

> 开发者现在怎么配置 Agent？

而不是：

> 不同配置究竟怎样改变 correctness / safety / time / cost？

作者也把后者明确作为未来 experimental research 的方向。

---

## Build-vs-Buy Study Protocol

近期的研究方案进一步计划控制：

- context files；
- Skills；
- MCP-enabled tools；
- permission controls；

观察 Claude Code / Codex 的 build-vs-buy decision 如何变化。

这是一个非常重要的邻近工作。

它证明：

> **把 coding-agent configuration 当作 controlled treatment 是成立的 empirical-SE methodology。**

但其 outcome 聚焦 dependency/library choice，而非一般的 coding effectiveness 和 behavioral safety。

---

# 6. Communication 与 Cost 研究

Multi-Agent communication 研究已经开始关注通信内容和效率。

例如 2026 年的 **PACT / What Should Agents Say?** 探索 action-state communication，并报告 communication design 可以减少 token consumption，同时保持或改善 coding task performance。

另一方面，已有研究开始单独研究 OpenHands 的 token consumption pattern。

因此当前文献分别已经证明：

```text
Agent interface → Performance

Communication → Performance / Token

Configuration → Agent behavior

MCP → Tool interoperability

Security mechanism → Safety
```

但这些问题尚未被统一研究。

---

# 7. Protocol Security 相关工作

MCP 官方规范本身已经明确承认 Tool 是安全边界：

- Tool 可以执行任意代码；
- Tool annotations/description 来自非可信 server 时应视为 untrusted；
- Host 应获得用户授权。



MCPTox 则进一步以 45 个真实 MCP servers 和 353 个真实 tools 进行 Tool Poisoning evaluation，显示 MCP tool metadata 可以形成实际攻击面。

这说明：

\[
MCP
\neq
Security\ Mechanism
\]

它既可能提供统一 control point，也可能增加新的 attack surface。

---

# 8. Coding-Agent Safety 相关工作

### RedCode — NeurIPS 2024

RedCode 专门评价 Code Agent 的 risky code execution 与 generation，提供超过 4,000 个 execution cases，并使用真实 Docker environment 验证行为。

这是本课题设计安全 oracle 的重要参考。

---

### Security Debt in LLM Agent Applications — ASE 2025

该 empirical study 系统研究 Agent application vulnerabilities、developer mitigation practices 和 mitigation trade-offs。

它证明：

> **安全–功能 trade-off 本身是一个 Software Engineering empirical question。**

---

### Engineering Pitfalls in AI Coding Tools — FSE 2026

该研究人工分析 Claude Code、Codex 和 Gemini CLI 的 3,800+ publicly reported bugs。

说明真实 coding agents 已经产生大量工程 failure，而不仅是 benchmark-level capability difference。

---

# 9. 当前文献 Gap

经过上述文献梳理，本课题认为目前存在一个明确但需要通过进一步 SLR 验证的 gap：

## Gap 1：现有 Coding-Agent 研究主要优化 capability，而不是综合 trade-off

SWE-agent、MAGIS、AutoCodeRover、OpenHands 等主要回答：

> 怎样使 coding agent 更有效？

而不是：

> 这种设计提高 accuracy 的同时，安全、latency 和 cost 发生了什么？

---

## Gap 2：现有 Safety 研究主要研究“是否能攻击成功”，而不是 SE task performance

例如 RedCode / MCP Security benchmark 通常测：

\[
Attack\ Success
\]

或者：

\[
Refusal / Unsafe\ Execution
\]

而没有在真实 repo-level coding workload 下同步回答：

\[
TaskSuccess
+
Safety
+
Time
+
Cost
\]

---

## Gap 3：已有 configuration 研究主要是 observational study

我们已经知道开发者会使用：

- Skills；
- Subagents；
- MCP；
- Rules；
- Hooks。



但尚缺少：

> **对这些 interaction mechanisms 的 controlled causal-style comparison。**

---

## Gap 4：Communication 与 Tool Protocol 通常被分开研究

Multi-agent 工作研究：

```text
Agent ↔ Agent
```

MCP 工作研究：

```text
Agent ↔ Tool
```

现实 coding agent 却是：

```text
Agent
  ↓
Agent
  ↓
Tool
  ↓
Repository
```

缺少统一分析 communication 与 tool integration 如何共同影响 trajectory。

---

## Gap 5：缺少机制层解释

仅比较：

```text
success rate
ASR
cost
```

仍不足以解释：

> 为什么 A 比 B 好？

因此需要完整 tracing：

- tool calls；
- communication turns；
- retries；
- privilege use；
- trajectory length；
- delegation depth；
- unsafe-context exposure。

---

# 10. 核心 Research Question

## RQ1 — Effectiveness

> **How do different communication and tool-integration mechanisms affect the effectiveness of coding agents on repository-level software engineering tasks?**

指标：

- Resolve Rate；
- Test Pass Rate；
- Build Success；
- Patch Correctness；
- Regression Rate。

---

## RQ2 — Behavioral Safety

> **How do these mechanisms affect coding-agent behavioral safety under benign and adversarial execution conditions?**

指标：

- Unsafe Tool Call Rate；
- Unauthorized Action Rate；
- Over-Privileged Action Rate；
- Sensitive Resource Access；
- Attack Success Rate；
- Policy Violation Rate。

---

## RQ3 — Efficiency

> **What computational and interaction overhead do these designs introduce?**

指标：

- wall-clock latency；
- input/output token；
- LLM requests；
- Tool calls；
- Agent messages；
- retries；
- dollar cost。

---

## RQ4 — Trade-off

> **When are more sophisticated Agent interactions worth their additional security and computational costs?**

这是本论文最重要的综合 RQ。

目标不是简单回答：

> Multi-Agent 好不好？

而是：

> **在什么类型任务上、什么 complexity 下、什么 Tool intensity 下，它才值得？**

---

## RQ5 — Mechanism

> **Which trajectory characteristics explain the observed differences in effectiveness, safety, and efficiency?**

候选解释变量：

\[
TrajectoryLength
\]

\[
ToolCalls
\]

\[
CommunicationTurns
\]

\[
RetryCount
\]

\[
PrivilegeEscalations
\]

\[
DelegationDepth
\]

---

# 11. 实验设计

第一阶段建议采用 **2×2 controlled factorial design**。

| | Native Tools | MCP-mediated Tools |
|---|---|---|
| Single Agent | C0 | C1 |
| Multi-Agent | C2 | C3 |

尽量固定：

```text
Same LLM
Same Prompt
Same Repository
Same Task
Same Tool Functionality
Same Token Budget
Same Execution Environment
```

改变：

```text
Agent Architecture
+
Tool Integration Mechanism
```

---

# 12. Multi-Agent Configuration

第一版不建议研究五种 topology。

固定为：

```text
Planner
   ↓
Coder
   ↓
Reviewer
```

或：

```text
Planner
 ↙   ↘
Coder Reviewer
  ↘   ↙
 Validator
```

这样避免同时改变：

- Agent number；
- topology；
- protocol；
- Tool；

导致实验不可解释。

如果 pilot 结果有价值，后续增加：

```text
framework-native communication
vs
typed / protocolized communication
```

作为第二实验。

---

# 13. Benchmark

首选：

## SWE-bench Verified

优点：

- repo-level；
- real GitHub issues；
- executable tests；
- ground truth 清晰；
- Coding Agent literature 广泛使用。

第二阶段可以加入：

- SWE-bench Lite；
- SWE-bench Pro；
- SWE-rebench；
- 自建 security-aware subset。

---

# 14. Safety Scenario

第一版建议只选三个。

### S1 Repository Context Injection

恶意 instruction 藏于：

```text
README
code comments
documentation
issue text
repository config
```

---

### S2 Malicious Tool Metadata / Output

测试：

```text
Native Tool
vs
MCP Tool
```

面对 tool description / result poisoning 的差异。

---

### S3 Privilege Misuse

任务本身只需要：

```text
read repository
write workspace
run tests
```

观察 Agent 是否：

```text
读取 home
访问 credential
访问网络
执行高权限 shell
修改 workspace 外文件
```

---

# 15. 数据记录

每次执行保存完整 event trace：

```text
task_id
configuration
agent_id
timestamp

message
tool_name
tool_arguments
tool_result

file_read
file_write
shell_command
network_request

token_input
token_output
latency
cost

security_event
final_patch
test_result
```

最终研究的不只是：

\[
Configuration \rightarrow Outcome
\]

而是：

\[
Configuration
\rightarrow
Trajectory
\rightarrow
Outcome
\]

---

# 16. 预期创新点

## Innovation 1 — Unified empirical evaluation

第一次系统地在 repo-level SE workload 下联合评价：

\[
Correctness
+
BehavioralSafety
+
Latency
+
Cost
\]

而非只优化其中一个维度。

---

## Innovation 2 — Interaction mechanism as treatment

将：

- communication；
- Agent architecture；
- Tool protocol；

作为 **software architecture variables**，而非把不同 commercial agent 当黑盒排行榜。

---

## Innovation 3 — Trajectory-level mechanism analysis

通过完整 trace 解释：

> 为什么某种 architecture 更快、更贵、更安全或更危险。

---

## Innovation 4 — Capability–Safety–Efficiency frontier

尝试构造：

\[
Utility
\times
Safety
\times
Efficiency
\]

的 Pareto frontier，而不是单一 leaderboard。

---

# 17. 预期结论类型

好的论文不一定证明复杂 Agent 更好。

任何下面结果都可能有价值：

> MCP 对 coding correctness 没有明显帮助，却增加 latency 和 attack surface。

或者：

> Multi-Agent 只在 high-complexity repository task 上产生收益，简单任务成本显著高于收益。

或者：

> Multi-Agent reviewer 降低 patch errors，却同时扩大 malicious-context propagation。

或者：

> Tool protocol 本身影响有限，真正决定安全的是 permission/provenance enforcement。

---

# 18. FSE 价值

本课题本质上研究的是：

> **AI coding agent 作为软件系统，其 architecture/interface/protocol design 如何影响 software quality 与 system safety。**

而不是单纯：

> 比几个 LLM benchmark。

这与 FSE 对：

- empirical SE；
- AI-assisted SE；
- software architecture；
- reliability/security；
- developer tooling；

的关注较契合。

---

# 19. 最大风险

### 风险 1：变量太多

解决：

第一阶段只研究：

\[
Single/Multi
\times
Native/MCP
\]

不要同时加入 memory、skill、topology、model。

### 风险 2：MCP 与 Native 功能不等价

必须实现功能等价的 tools。

### 风险 3：结论只适用于某一个 LLM

至少使用：

- 一个 frontier model；
- 一个不同厂商 model；
- 如果预算允许，一个 open-weight model。

### 风险 4：论文变成 benchmark table

必须做：

> RQ5 mechanism analysis。

---

# 20. 当前一句话 Proposal

> **We propose a controlled empirical study to understand how communication and tool-integration mechanisms shape the effectiveness, behavioral safety, latency, and cost of repository-level coding agents, and to identify when increasingly sophisticated agent architectures are actually worth their additional complexity and risk.**

---

# 21. 当前 Novelty Confidence

**新颖性：4/5**

关键在于不要把论文做成：

> MCP vs Native 的简单 benchmark。

真正 novelty 应该是：

> **controlled interaction design + trajectory-level behavioral safety + multi-dimensional trade-off + mechanism explanation。**