# 开题报告 B：能否通过协议层为已有 Coding Agents 补上安全能力？
## ——跨 Coding-Agent Architecture 的 Protocol-Level Security Retrofit 实证研究

### 1. 暂定题目

首选：

> **Can Protocols Make Coding Agents Safer? An Empirical Study of Security Retrofits for Agentic Software Engineering**

更偏 FSE：

> **Retrofitting Security into Coding Agents: A Cross-Architecture Empirical Study of Protocol-Level Safety Controls**

更强调 behavioral safety：

> **From Capability to Controllability: Retrofitting Behavioral Safety into Existing Coding Agents**

---

# 2. 研究动机

2024–2025 年产生了大量 Coding Agent systems：

- SWE-agent；
- AutoCodeRover；
- MAGIS；
- OpenHands；
- Agentless/structured pipelines；
- 后续大量 SWE-bench-oriented Agents。

这些工作的主要目标通常是：

\[
Task\ Success\uparrow
\]

例如 SWE-agent 研究 interface 如何增强 autonomous software engineering。

MAGIS 则研究 multi-agent collaboration 能否提高 GitHub issue resolution。

但是随着 Agent 获得：

```text
filesystem
shell
network
browser
repository
third-party tool
other agents
```

真实安全风险也随之增长。

《Behavior Safety of Autonomous Interactive Agents》将这种现象描述为从：

```text
content safety
```

向：

```text
behavior safety
```

的转变，并明确把：

- Tool misuse；
- communication protocol；
- MCP；
- privilege escalation；
- over-privileged tool use；
- multi-agent propagation；

纳入同一 Agent behavioral safety framework。

---

# 3. 现实问题

现实 Coding Agent 生态存在一个非常现实的问题：

> **大量 Agent 是先追求 capability，再逐渐补 security。**

因此一个重要的软件工程问题是：

> 我们是否必须重新设计这些 Agent，才能使其安全？

还是：

> **可以像给传统系统补 access-control middleware / sandbox / protocol layer 一样，对已有 Agent 做安全 Retrofit？**

即：

\[
Existing\ Agent
+
Reusable\ Security\ Layer
\rightarrow
Safer\ Agent?
\]

---

# 4. 已知 Coding-Agent Security 风险

## RedCode — NeurIPS 2024

RedCode 专门测试 Code Agent 的 unsafe execution / generation，并强调 Agent 能够真正执行 Python、Bash 和操作系统行为以后，安全已经不只是 output filtering 问题。

---

## Takedown — 2025

该工作系统分析 8 个真实 Coding Agents 的内部 workflow，发现 15 类安全问题，并展示多个 component issue 可以被串成 end-to-end exploitation；作者报告在部分系统中能够实现 arbitrary command execution 和 global data exfiltration。

这个结果对本研究非常重要：

> **Agent security failure 往往不是一个点，而是 component interaction chain。**

---

## Security Debt in LLM Agent Applications — ASE 2025

该研究对 Agent application vulnerability 和 developer mitigation practice 进行 measurement study，并强调 mitigation 伴随 trade-off。

因此：

> 给 Agent“补安全”本身就是一个 SE engineering problem。

---

## Engineering Pitfalls in AI Coding Tools — FSE 2026

针对 Claude Code、Codex、Gemini CLI 的 3,800+ public bug report 的 empirical analysis 进一步说明 production coding agents 存在大量 tool/harness engineering failure。

---

# 5. 已有 Safety Enforcement 方向

## Towards Verifiably Safe Tool Use for LLM Agents — ICSE 2026 NIER

该工作认为仅依赖 model guard 无法提供系统级安全保证，并提出将安全要求转换为：

- data-flow constraints；
- tool-sequence constraints；

对 Tool interaction 实施 enforcement。

这与本研究高度相关，因为它说明：

> **Safety 可以被提升到 Agent/tool boundary 上执行。**

---

## TraceCaps — ICSE 2026 NIER

TraceCaps 将 provenance 与 risk enforcement 引入 agentic software engineering workflow，并在 SWE-bench 场景展示 runtime governance。

它说明：

> Provenance 不只是 log，而可以成为 runtime safety primitive。

---

# 6. Harness Security 的最近邻工作

2026 年近期 preprint：

**Distributing Security Controls Through Harness Engineering**

已经开始研究能否把：

- sandbox；
- skill scanning；
- tool restrictions；

部署到 commercial coding agents 和 custom harness 上，并比较安全控制效果。

这是本课题必须正面面对的最近邻工作。

因此本研究不能只是：

> 给 Agent 加 sandbox，再测一次安全。

真正差异化必须落在：

# **Protocol-level security semantics**

---

# 7. 为什么研究 Protocol Layer？

Protocol 本身不是 security。

MCP 官方明确要求把未受信 Server 的 Tool annotation 视为 untrusted，并指出 Tool 可以代表任意代码执行。

MCPTox 又证明 Tool metadata 本身可以成为攻击入口。

因此本课题不提出：

> “MCP 天然可以保护 Agent。”

而提出：

> **标准化 interaction boundary 是否可以成为统一部署 security policy 的位置？**

即：

```text
Agent
  │
  ▼
┌────────────────────────────┐
│ Protocol Security Boundary │
│                            │
│ provenance                 │
│ capability                 │
│ authorization              │
│ trust                      │
│ policy                     │
└──────────────┬─────────────┘
               ▼
          Tool / Agent
               │
               ▼
         External World
```

---

# 8. Security Retrofit 定义

本课题拟设计一个**尽可能 model-agnostic、agent-agnostic 的 protocol security layer**。

不修改 LLM 权重。

尽量不修改 Agent planning logic。

主要拦截：

```text
Agent → Tool

Tool → Agent

Agent → Agent
```

三个边界。

---

# 9. 候选 Security Properties

## P1 Provenance

所有 observation / message 标记来源：

```text
USER
SYSTEM
REPOSITORY
TOOL
REMOTE_AGENT
EXTERNAL_WEB
```

目标：

> 不再把所有自然语言 context 视为同一信任级别。

---

## P2 Instruction–Data Separation

例如：

```text
README
code comments
tool output
```

明确作为：

```text
UNTRUSTED_DATA
```

而不能自然提升为 instruction。

---

## P3 Capability Scope

每个 Agent / Tool invocation 有显式 capability：

```text
read(workspace)
write(workspace/src)
execute(test)
```

而不是：

```text
full filesystem
full shell
full network
```

原则：

\[
Capability_{actual}
\subseteq
Capability_{task}
\]

---

## P4 Least Privilege

如果低权限 Tool 可以完成任务：

> 禁止 Agent 自动选择高权限 alternative。

Survey 本身已经把 over-privileged tool selection 列为重要 system safety problem。

---

## P5 Trust-Aware Tool Metadata

例如 MCP Tool：

```text
trusted
unknown
untrusted
```

Tool description 不自动拥有 instruction authority。

---

## P6 Multi-Agent Delegation Scope

如果：

```text
Agent A
   ↓
Agent B
```

要求：

\[
Capability_B
\subseteq
Capability_A
\]

避免 delegation amplification。

---

## P7 Policy Enforcement

每个高风险动作：

```text
Agent Action
     ↓
Policy Check
     ↓
allow / deny / require approval
```

---

# 10. 研究对象

建议选三个具有明显架构差异的 systems，而不是十个。

## Agent A — SWE-agent

代表：

> Single autonomous coding agent + explicit ACI。



---

## Agent B — OpenHands

代表：

> General event-driven coding agent platform。



---

## Agent C — MAGIS 或一个可复现 Multi-Agent Coding System

代表：

> Multi-agent division of labor + Agent communication。



这样形成：

```text
Single specialized
       vs
General-purpose
       vs
Multi-Agent
```

三种 architecture。

---

# 11. 核心实验条件

比简单 before/after 更强的设计是三层：

## C0 — Original

原 Agent。

```text
Original planning
Original tools
Original permissions
```

---

## C1 — Protocolized

所有 interaction 经过统一 protocol adapter，但**不增加主动 security policy**。

作用：

> 分离“协议化本身”的影响。

---

## C2 — Security-Enhanced Protocol

在 C1 上开启：

- provenance；
- least privilege；
- instruction-data distinction；
- capability control；
- policy enforcement。

---

形成：

\[
Original
\rightarrow
Protocolized
\rightarrow
SecureProtocol
\]

这一设计非常重要。

因为如果只比较：

```text
Original vs Secure
```

无法知道性能变化到底来自：

> serialization/communication overhead

还是：

> security mechanism。

---

# 12. Research Questions

## RQ1 — Baseline

> **What behavioral security failures occur in representative coding agents under realistic repository-level workloads?**

目标首先建立 baseline。

---

## RQ2 — Security Effectiveness

> **To what extent can a reusable protocol-level security layer reduce behavioral security violations across heterogeneous coding-agent architectures?**

这是核心 RQ。

---

## RQ3 — Utility Preservation

> **How much task utility is lost when protocol-level safety controls are enabled?**

测：

\[
\Delta TaskSuccess
\]

\[
\Delta TestPass
\]

\[
\Delta Regression
\]

---

## RQ4 — Efficiency Cost

> **What latency, token, tool-call, and monetary overhead does the retrofit introduce?**

---

## RQ5 — Generalizability

> **Which classes of coding-agent vulnerabilities are consistently mitigated by protocol-level controls, and which remain architecture- or model-dependent?**

这是我认为最有价值的 RQ。

最终建立：

```text
Protocol-solvable
        vs
Protocol-insufficient
```

的风险 taxonomy。

---

## RQ6 — Multi-Agent Propagation

如果包含 MAGIS：

> **Can protocol-level provenance and capability boundaries contain the propagation of malicious or faulty information across coding agents?**

指标：

\[
PropagationDepth
\]

\[
AffectedAgents
\]

\[
UnsafeDownstreamActions
\]

---

# 13. Threat Model

第一篇论文不建议覆盖十种攻击。

优先选四类。

---

## T1 Repository Indirect Prompt Injection

现实 Coding Agent 会主动读取：

- README；
- issue；
- source comments；
- docs；
- configuration files。

ACL 2026 的 XOXO 已经利用 coding assistant 自动引入 repository snippets 的机制实现 cross-origin context poisoning。

测试：

> provenance + instruction/data separation 是否有效？

---

## T2 Malicious Tool Metadata / Tool Result

例如：

```text
Tool Description
       ↓
Malicious Instruction
```

或者：

```text
Tool Result
     ↓
"Run ... / read ..."
```

MCPTox 已证明 MCP metadata poisoning 是真实攻击面。

测试：

> trust-aware Tool boundary 是否有效？

---

## T3 Privilege Misuse

没有攻击者也测。

任务只要求：

```text
repository read/write
test execution
```

但 Agent 尝试：

```text
external network
home directory
SSH key
credential
workspace outside write
```

测试：

> capability / least privilege 能否防止？

---

## T4 Cross-Agent Propagation

Multi-Agent extension：

```text
malicious repository
       ↓
Coder
       ↓
Reviewer
       ↓
Manager
       ↓
Tool
```

观察攻击是否：

```text
传播
放大
被阻断
```

---

# 14. Safety Oracle

尽量避免完全使用 LLM-as-Judge。

使用 system-level executable oracle：

```text
filesystem diff
process trace
network log
shell command
tool trace
permission check
secret access log
```

类似 RedCode 使用真实 execution environment 评价 Agent 行为的思想。

---

# 15. 指标体系

## Correctness

- Resolved；
- Tests Passed；
- Build Success；
- Patch correctness；
- Regression。

---

## Security

### Attack Success Rate

\[
ASR=
\frac{SuccessfulAttacks}
{AttackTrials}
\]

### Policy Violation Rate

\[
PVR=
\frac{PolicyViolatingActions}
{AllActions}
\]

### Over-Privilege Rate

\[
OPR=
\frac{UnnecessaryPrivilegedActions}
{PrivilegedActions}
\]

### Sensitive Resource Access Rate

### Unauthorized Tool Call Rate

### Data Exfiltration Success

### Cross-Agent Propagation Depth

---

## Efficiency

- wall-clock；
- token；
- LLM calls；
- Tool calls；
- Agent messages；
- retry；
- dollar cost。

---

# 16. Benchmark

主 benchmark：

> **SWE-bench Verified**

安全扩展方式：

为其中任务构造：

```text
Benign Version
       +
Adversarial Variant
```

例如：

```text
Task 001 clean repo
Task 001 poisoned repo
```

这样：

\[
TaskDifficulty
\]

基本保持不变，只改变 security condition。

这是比单独构建一个纯 attack benchmark 更好的 controlled design。

---

# 17. 当前文献 Gap

## Gap 1：Vulnerability studies 已经很多，但 mitigation study 不够跨 architecture

Takedown 等工作已经能证明 coding agents 存在严重 security problems。

因此：

> “Coding Agents 不安全”

本身已经不是足够的新贡献。

缺的是：

> **能否用统一工程机制跨不同 Agent architecture 改善安全？**

---

## Gap 2：现有防御通常针对某一个攻击或某一个 Agent component

例如：

- prompt filter；
- sandbox；
- tool restriction；
- specific injection defense。

而 Behavior Safety Survey 强调风险会沿：

\[
Cognition
\rightarrow
Tool
\rightarrow
Environment
\rightarrow
Collaboration
\]

传播。

因此需要跨 boundary 的 mechanism。

---

## Gap 3：Harness security 已经出现，但 protocol-level semantics 仍不充分

近期 Harness Engineering safety 工作已经测试 sandbox、skill scanner、tool restrictions。

所以不能把 novelty 放在：

> “我们加 sandbox。”

本研究需要聚焦：

```text
Provenance
Authority
Capability
Delegation
Trust
```

这些 **interaction semantics**。

---

## Gap 4：Security paper 通常不充分评价 Coding Utility

Agent safety benchmark 往往测：

\[
ASR
\]

但开发者真正关心：

> 开了安全以后还能不能修 bug？

因此必须研究：

\[
SecurityGain
\quad vs\quad
TaskUtilityLoss
\]

---

## Gap 5：缺少 Protocol-Solvable Risk Taxonomy

不是所有 Agent 问题都可以靠 protocol 修。

例如：

```text
unauthorized file access
```

可能适合协议约束。

但：

```text
incorrect bug localization
```

很可能不是。

因此本研究有机会回答：

> **Agent safety 中哪些问题属于 system/protocol engineering problem，哪些仍属于 model reasoning problem？**

这是非常有价值的 empirical finding。

---

# 18. 预期创新点

## Innovation 1 — Cross-Architecture Security Retrofit

同一个安全 interaction layer 被应用于多种 2024–2025 coding-agent architecture。

核心不是：

> 新 Agent。

而是：

> **已有 Agent 能不能被系统性 harden？**

---

## Innovation 2 — Protocol as Security Enforcement Boundary

把协议从：

```text
interoperability mechanism
```

重新评价为：

```text
security policy enforcement boundary
```

但同时检验：

> protocolization 是否也产生新风险。

---

## Innovation 3 — Protocol-Solvable / Protocol-Unsolvable Taxonomy

建立新的 empirical taxonomy：

| Failure | Protocol effective? |
|---|---|
| Unauthorized file access | Yes |
| Tool metadata injection | Maybe |
| Cross-agent privilege escalation | Yes |
| Hallucinated patch | No/limited |
| Wrong localization | No |
| Tool misuse | Partial |

最终回答：

> Protocol 应该解决什么、不应该解决什么。

---

## Innovation 4 — Security–Utility–Cost Curve

不是追求：

\[
MaximumSecurity
\]

而是寻找：

\[
SecurityGain
\quad vs\quad
UtilityLoss
\quad vs\quad
Overhead
\]

---

## Innovation 5 — Cross-Agent Containment

如果加入 Multi-Agent：

> 研究安全机制是否能够让一个 compromised agent 的问题停止在局部。

即：

\[
Compromise(A)
\not\Rightarrow
Compromise(System)
\]

---

# 19. Potential Paper Story

一个很好的结果可能是：

> We find that protocol-level capability control eliminates most direct privilege violations across all three coding-agent architectures with negligible utility loss.

同时：

> Provenance alone does not reliably prevent semantic prompt injection.

而：

> Multi-agent architectures exhibit substantially greater propagation risk than single-agent systems.

最后：

> Combining provenance with capability enforcement achieves the best safety–utility trade-off.

这样的结论比：

> “我们提出一个新 Guard，ASR 降了 20%”

更有 empirical paper 的价值。

---

# 20. 与现有工作的区别

| 工作 | 主要问题 | 本研究区别 |
|---|---|---|
| SWE-agent | Interface → capability | 加入 behavioral safety |
| RedCode | Code-agent safety benchmark | 研究 retrofit，而不只是测漏洞 |
| Takedown | 找真实漏洞 | 研究统一 mitigation |
| Security Debt | vulnerability / practice taxonomy | 做 controlled execution experiment |
| MCP Security | MCP 自身 attack surface | 研究 MCP/protocol security properties 在 coding workflow 中的效果 |
| Harness Security Controls | sandbox/tool restriction | 聚焦 provenance/capability/delegation 等 protocol semantics |
| A2ASecBench | generic A2A protocol attack | 进入真实 coding-agent domain |

---

# 21. FSE 定位

本论文可以被 framing 为：

> **secure engineering of agentic software systems**

它包含典型 FSE elements：

- existing systems；
- empirical measurement；
- reusable infrastructure；
- controlled experiment；
- regression / performance trade-off；
- system tracing；
- actionable developer recommendations。

---

# 22. 最大风险

## 风险 1：做成一个 Defense Method Paper

目标仍应是：

> empirical characterization。

Protocol layer 是：

> experimental vehicle。

而不是必须声称：

> 最先进防御算法。

---

## 风险 2：Retrofit 三个 Agent 工作量巨大

第一阶段建议：

```text
OpenHands
+
SWE-agent
```

先成功。

然后加入：

```text
一个 Multi-Agent system
```

验证 generalizability。

---

## 风险 3：Security policy 太主观

必须让 policy 尽量任务可验证：

```text
workspace boundaries
network access
filesystem scope
tool capability
secret files
```

避免全靠人工标注。

---

## 风险 4：Protocol implementation 变成主要工程贡献

目标不是重新实现 MCP/A2A 全协议。

更合理的是：

> 设计一个最小 protocol-security abstraction，然后通过 adapter 接入现有 Agent。

---

# 23. 当前一句话 Proposal

> **We conduct a cross-architecture empirical study of whether reusable protocol-level controls—such as provenance, capability scoping, least privilege, and delegation constraints—can retrofit behavioral safety into existing coding agents while preserving repository-level task effectiveness and acceptable execution cost.**

---

# 24. 当前 Novelty Confidence

**新颖性：4.5/5**

相较路径 A，这条路线的问题更尖锐：

> **Can we retrofit safety into already-deployed coding-agent architectures?**

且非常容易形成：

- positive findings；
- negative findings；
- trade-offs；
- actionable guidelines。

它最大的挑战不是 Research Question，而是工程实现与 scope 控制。