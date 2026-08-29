# FSE 2027：Coding Agent 接口 / 工具协议的 Security–Utility–Efficiency 研究路线

> **Research snapshot:** 2026-08-15  
> **目标 venue:** ACM FSE 2027（Research Papers）  
> **核心领域:** Autonomous Software Engineering / Coding Agents / Agent Security / Empirical Software Engineering  
> **重要说明:** 本文档做的是截至 2026-08-15 的 prior-art / novelty screen。它可以显著降低“撞题”风险，但**不能保证绝对首创**；Agent 方向变化极快，投稿前必须再次做 Google Scholar / DBLP / arXiv / OpenReview / ACM DL 的滚动检索。

---

## 0. Executive Summary：先说结论

最初的研究想法是：

> 比较不同 Agent 协议 / 技术 / 工具 / scaffold，在代码相关任务中的 **correctness、security、latency、cost**。

这个母题是对的，但**按原始表述已经不够新**。

原因是 2025–2026 已经出现了多条非常接近的工作：

- **SWE-Effi** 已经系统研究 coding-agent 的 correctness × token/time/resource effectiveness；
- **When Does Restricting a Coding Agent to `execute_code` Help?** 已经做了 `baseline / bash_only / code_only(MCP)` 的受控 tool-surface ablation；
- **The Devil Is in the Interface**（2026-08-11，COLM 2026）刚刚进一步做了 **6 种 capability-matched tool architectures × 3 actors × 11,700 trajectories**，研究 resolve rate、consistency、exploration、token/step efficiency；
- **The Scaffolding Matters More Than the Interface**（2026-08-09）已经直接比较 MCP vs CLI，并发现 scaffold 往往比 interface 本身更主导成本；
- **Permission Denied**（2026-08）已经研究企业安全策略 hardening 对 coding-agent success 和 cost 的影响；
- **SecureAgentBench** 已经同时评价 repository-level coding agent 的 functional correctness 与 generated-code security；
- **IssueTrojanBench / Adversarial Bug Reports / Execution-Grounded Security Testing** 已经系统研究恶意 issue、间接 prompt injection 与 coding-agent execution security；
- **Breaking the Protocol / AgentRFC / AgentThread** 已经深入 MCP / agent protocol 的安全与协议组合问题。

因此，不建议再做：

> “SWE-agent vs OpenHands vs Agentless，比较准确率、token、时间、价格。”

也不建议把题目简单改成：

> “MCP vs CLI 谁更好 / 谁更安全？”

这两类 gap 都已经被明显占据。

### 0.1 我目前最推荐的核心科研问题

> **How does tool architecture—and separately, privilege granularity—causally affect the security–utility–efficiency frontier of repository-level coding agents?**

中文：

> **在 repository-level 软件工程任务中，Agent 的工具接口架构（tool architecture）和权限粒度（privilege granularity）分别如何影响任务正确性、执行层安全性与资源效率？**

这比“比较几个 Agent”强的地方在于：

1. **研究的是可泛化的设计变量**，不是产品排行榜；
2. 可以做真正的 **controlled empirical study**；
3. 直接承接 SWE-agent 的 ACI 思想；
4. 衔接最新的 tool-architecture / efficiency 文献；
5. 又进入 coding-agent security 的 execution/authorization 层；
6. 可以回答一个目前仍非常重要的机制问题：

> **Structured ACI 的安全收益到底来自“interface representation”，还是来自“它顺便收窄了 authority”？**

这是一个比单纯测 ASR 更有科研价值的因果拆解。

### 0.2 推荐论文故事

```text
SWE-agent:
Better interface can improve coding-agent behavior.

2025–2026:
Tool/scaffold design also changes cost, consistency, exploration.

Agent-security literature:
Broad tool authority creates prompt-injection / authorization / execution risks.

BUT:

Interface representation
        ×
Privilege / authority
        ×
Repository task
        ↓
Utility + Execution Security + Efficiency

还缺乏统一、受控、paired 的实证分析。
```

最终问题不是：

> 哪个 Agent 最强？

而是：

> **When is extra agent capability/authority actually worth it, and why?**

---

# 1. 先把几个容易混淆的概念分清

| 概念 | 研究对象 | 例子 |
|---|---|---|
| Foundation Model | 底层模型 | GPT、Claude、Gemini、Qwen |
| Agent / Actor | 负责 reason–act–observe 的执行主体 | Codex CLI actor、Claude Code actor |
| Scaffold / Harness | 把模型、context、tools、loop 组织起来的运行框架 | OpenHands、SWE-agent harness |
| ACI / Tool Architecture | “能力以什么形式暴露给模型” | Bash、typed read/edit/search tools、Python CodeAct |
| Tool Surface | Agent 实际能调用的工具集合 | shell、read_file、edit_file、browser、network |
| Privilege / Authority | 每个工具到底允许做到什么 | repo-only、network off、allowlisted commands |
| Protocol | Agent 与工具 / Agent 与 Agent 的通信与交互规范 | MCP、A2A |
| Agent Architecture | 单 Agent / planner–coder / reviewer / multi-agent 等结构 | Planner–Coder–Reviewer |
| Security of Agent | Agent 本身是否会被劫持或越权 | prompt injection、tool misuse |
| Security of Output | Agent 写出的代码是否安全 | SQLi、XSS、memory safety bug |
| Agent for Security | Agent 是否能完成安全任务 | vulnerability finding / repair / pentesting |

## 1.1 特别注意：MCP 和 A2A 不应简单当成“同一层协议二选一”

- **MCP** 主要解决 Agent / model 与 tools/resources 的标准化连接；
- **A2A** 主要解决 Agent-to-Agent 的发现、任务生命周期和通信。

因此：

> “MCP vs A2A 哪个在 coding task 上更好？”

如果没有明确比较对象，很容易成为 apples-to-oranges。

2026 年已经出现 [A Comparative Study of MCP and A2A for Inter-Agent Coordination](https://arxiv.org/abs/2607.23884)，作者自己也强调这是狭义 coordination 场景的经验报告，而不是“哪个协议普遍更好”。

---

# 2. 科研链条：从 SWE-bench 到 ACI，再到 Efficiency 和 Security

## 2.1 Stage 0：真实软件工程 benchmark

### SWE-bench — ICLR 2024
**Paper:** [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770)

```text
Real GitHub Issue
      +
Repository snapshot
      ↓
Model / Agent
      ↓
Patch
      ↓
Executable tests
      ↓
Resolved / Not Resolved
```

它把研究从 function-level code generation 推进到 repository-level software engineering。

留下的问题包括：

- 找到正确文件；
- 理解 issue；
- 修改多文件；
- 调工具；
- 跑测试；
- 根据错误恢复。

---

# 3. Stage 1：SWE-agent 把“接口本身”变成科研变量

## SWE-agent — NeurIPS 2024
**Paper:** [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)

### 核心创新

提出 **Agent-Computer Interface (ACI)**：

> Agent 是一种新的 computer user，应为它设计适合 LLM 的计算机接口，而不是默认人类 GUI / 裸 shell 就是最优接口。

典型能力：

- repository navigation；
- file search；
- file view；
- code editing；
- test execution；
- concise feedback；
- lint / syntax guardrails。

### 关键思想

\[
Agent\ Capability \neq Model\ Capability
\]

而更接近：

\[
Agent\ Capability = Model + Interface + Environment + Feedback
\]

SWE-agent 把下面这个问题正式变成独立研究变量：

> **Holding the model fixed, how does the way we expose computer capabilities affect agent behavior?**

---

# 4. Stage 2：不同团队开始问“Agent 到底需要多复杂？”

## 4.1 AutoCodeRover — ISSTA 2024
**Paper:** [AutoCodeRover: Autonomous Program Improvement](https://arxiv.org/abs/2404.05427)

使用 software-specific structure：

- AST；
- class / method structure；
- iterative code search；
- fault localization。

\[
Generic\ ACI \rightarrow Program\text{-}aware\ Agent
\]

启示：真实代码不是普通文本；SE-specific structure 可能比通用 agent 工具更重要。

## 4.2 Agentless — FSE 2025
**Paper:** [Agentless: Demystifying LLM-based Software Engineering Agents](https://arxiv.org/abs/2407.01489)

用固定的：

```text
Localization
    ↓
Repair
    ↓
Patch Validation
```

挑战复杂 autonomous agent loop。

\[
More\ Agentic \neq Always\ Better
\]

因此真正应该研究的是 **when / under what conditions**，而非 average leaderboard。

## 4.3 SpecRover — ICSE 2025
**Paper:** [SpecRover: Code Intent Extraction via LLMs](https://arxiv.org/abs/2408.02232)

```text
Program Structure
      +
Specification / Intent Inference
      +
Reviewer
```

把关注点从“tests pass”推进到“patch 是否符合程序意图”。

---

# 5. Stage 3：Observation / Search / Multi-Agent / Platform 分叉

## 5.1 RepoGraph — ICLR 2025
[RepoGraph](https://openreview.net/forum?id=dw9VUsSHGB)

```text
Raw Files
   ↓
Repository-level Code Graph
   ↓
Agent Observation
```

对应：**Better Observation Interface**。

## 5.2 SWE-Search — ICLR 2025
[SWE-Search](https://arxiv.org/abs/2410.20285)

```text
multiple candidate trajectories
          ↓
MCTS / Value Agent
          ↓
select/refine
```

把研究推进到 inference-time search，同时自然带来 compute/token/time 成本问题。

## 5.3 MAGIS — NeurIPS 2024
[MAGIS](https://arxiv.org/abs/2403.17927)

把职责拆为 Manager、Repository Custodian、Developer、QA Engineer。

\[
Single\ Agent \rightarrow Specialized\ Multi\text{-}Agent
\]

**不建议当前第一篇同时把 tool architecture + multi-agent + protocol 全部做。**

## 5.4 OpenHands — ICLR 2025
[OpenHands](https://arxiv.org/abs/2407.16741)

提供 terminal、editing、browser、sandbox、runtime、evaluation、multi-agent 等通用软件 agent 基础设施。

但不要把“OpenHands vs SWE-agent”本身当核心科研变量，因为系统之间同时改变太多因素。

---

# 6. Stage 4：从 Scaffold Engineering 进入 Agent Training

## SWE-Gym — ICML 2025
[SWE-Gym](https://arxiv.org/abs/2412.21139)

从：

```text
pretrained model + prompt/scaffold
```

走向：

```text
SWE trajectories + agent training + verifier training
```

## SWE-smith
[SWE-smith](https://arxiv.org/abs/2504.21798)

继续扩展 software-agent training data。对于当前 empirical study 不是主线，但需要知道这一支的发展。

---

# 7. Stage 5：Efficiency 成为独立研究问题

## 7.1 SWE-Effi
[SWE-Effi](https://arxiv.org/abs/2509.09853)

把 SWE-agent 评价从单一 resolve rate 扩展到：

- token；
- time；
- resource effectiveness。

重要现象：

- scaffold × base model interaction；
- token snowball；
- expensive failures；
- token budget 与 time budget 下可能有不同排序。

因此以下 claim 已不新：

> “第一次同时比较 coding agents 的 correctness、token、cost、time。”

## 7.2 How Do AI Agents Spend Your Money? — 2026
[Paper](https://arxiv.org/abs/2604.22750)

研究 SWE-bench Verified 上多模型 token consumption，说明：

- agentic coding token 使用很高；
- 同一 task cost 具有高随机性；
- 更多 token 不等于更高 accuracy；
- model token efficiency 差异明显。

实验最好同时记录 input/output/cache/reasoning tokens、provider-billed dollars 与 wall-clock。

---

# 8. Stage 6：2026 年 Tool Surface / Tool Architecture 被真正受控研究

## 8.1 When Does Restricting a Coding Agent to `execute_code` Help?
[Paper](https://arxiv.org/abs/2607.10569)

非常接近原始选题：

```text
baseline
vs
bash_only
vs
code_only (single execute_code MCP tool)
```

并控制 model、harness、prompt，横跨 synthetic tasks、SWE-bench Mini、Claude Code、Codex CLI。

### 已占据的 gap
> 不同 tool surface 是否影响 coding-agent cost / pass rate？

### 未解决
- adversarial security；
- execution-layer unsafe behavior；
- privilege granularity；
- paired clean / attacked tasks；
- structured ACI 是否改变 attack surface。

## 8.2 The Scaffolding Matters More Than the Interface — 2026-08
[Paper](https://arxiv.org/abs/2608.08654)

比较 MCP vs CLI，跨 7 agent scaffoldings、5 models、一个固定 software task。

重要警告：

> interface 的 effect 不能与 scaffold/model/prompt/tool semantics 混在一起。

因此不能拿：

```text
Codex + CLI
vs
OpenHands + MCP
```

就归因于 protocol/interface。

## 8.3 The Devil Is in the Interface — COLM 2026
[Paper](https://arxiv.org/abs/2608.11386)

> **当前最高优先级必读。**

2026-08-11 上传，COLM 2026 accepted。

设计 6 种 capability-matched tool architectures，包含：

- BashOnly；
- Atomic；
- NLSearch；
- Python / CodeAct-style；
- cognitive-scaffolding variants。

规模：

- 3 actors；
- 11,700 trajectories；
- repository-level issue fixing。

评价：

- resolve rate；
- consistency；
- exploration；
- efficiency。

重要结果：

- capability 相近时总体 resolve rate 接近；
- tool architecture 仍改变 consistency、exploration、efficiency；
- Python/CodeAct 风格显著减少 steps/tokens；
- structured atomic tools 的效率效应具有 actor/model dependency。

### 这篇已经大幅吃掉：
> Tool architecture → correctness / time / token / behavior

### 但留下：
\[
Tool\ Architecture \rightarrow Security\ Behavior?
\]

## 8.4 Harness-IF — 2026-08
[Harness-IF](https://arxiv.org/abs/2608.11727)

关注 coding agent 在不同 **instruction surfaces** 上的 instruction following，例如 system、project files、user、tool、skill。

这对 security experiment 很关键：

> 攻击指令位于 issue、AGENTS.md、tool output、skill description 中时，不能默认它们是同一种 attack carrier。

---

# 9. Security 主线 A：General Tool-Using Agent Security

## 9.1 AgentDojo — NeurIPS 2024 Datasets & Benchmarks
[AgentDojo](https://arxiv.org/abs/2406.13352)

- realistic tool-use tasks；
- untrusted data；
- prompt injection；
- **utility + security joint evaluation**。

因此“security + utility jointly”本身已不是 novelty。

## 9.2 Progent
[Progent](https://arxiv.org/abs/2504.11703)

核心：

> **Least privilege for agent tools**

通过 policy 限制 agent 只能执行任务需要的 tool calls。

\[
More\ Authority \Rightarrow Larger\ Attack\ Surface
\]

但它不是 repository-level coding ACI 的 causal study。

---

# 10. Security 主线 B：MCP / Protocol Security

## 10.1 MCP Safety Audit
[MCP Safety Audit](https://arxiv.org/abs/2504.03767)

研究 malicious MCP server/tool、code execution、credential theft 等攻击面。

## 10.2 MCPSecBench
[MCPSecBench](https://arxiv.org/abs/2508.13220)

提供 MCP security taxonomy + benchmark/playground。单纯“做 MCP 安全 benchmark”已不新。

## 10.3 MCP-SafetyBench
[MCP-SafetyBench](https://arxiv.org/abs/2512.15163)

覆盖真实 MCP servers、多步、多 server interactions，包含 repository-management domain。

## 10.4 Breaking the Protocol — 2026
[Breaking the Protocol](https://arxiv.org/abs/2601.17549)

做：

```text
MCP integration
vs
equivalent non-MCP integration
```

控制 tool semantics、prompt、attack payload 等，并测 ASR、protocol vulnerabilities、defense、latency。

因此：

> “MCP vs non-MCP，在 security / latency 上做受控比较。”

已明显被占据。

## 10.5 AgentRFC
[AgentRFC](https://arxiv.org/abs/2603.23801)

贡献：

- 6-layer Agent Protocol Stack；
- 11 security principles；
- TLA+ invariants；
- AgentConform；
- SDK replay；
- Composition Safety。

属于 formal protocol security，而不是 repository-level empirical SWE。

## 10.6 AgentThread
[Formal Security Analysis of Agent Protocol Composition](https://arxiv.org/abs/2606.28690)

推进 cross-protocol composition safety：

\[
Safe(A) \land Safe(B) \not\Rightarrow Safe(A \circ B)
\]

适合作为未来 protocol-composition 第二路线。

---

# 11. Security 主线 C：Coding Agent Security

## 11.1 SecureAgentBench — 2025
[SecureAgentBench](https://arxiv.org/abs/2509.22097)

105 repository-level tasks，同时检查：

- functionality；
- PoC vulnerability；
- newly introduced vulnerabilities / static analysis。

这是 **Security of Agent Output**。

不要与“Agent 被 malicious issue 劫持”混成同一个 security 指标。

## 11.2 Adversarial Bug Reports as a Security Risk in LLM-based APR — MSR 2026
[ACM DOI](https://doi.org/10.1145/3793302.3793352)

研究 malicious bug report → APR/coding agent attacker-aligned behavior。

因此不能再 claim：

> first study of malicious bug reports against coding agents.

## 11.3 Overeager Coding Agents — 2026
[Paper](https://arxiv.org/abs/2605.18583)

研究 benign task 下的 authorization/scope expansion：

- 删除无关文件；
- 修改未授权配置；
- 触碰 credentials。

尤其重要：**framework axis 的影响很强**，说明 security behavior 不只是 model property。

## 11.4 SNARE
[SNARE](https://arxiv.org/abs/2605.28122)

自动合成 benign-but-risky scenarios，研究 overeager behavior。

## 11.5 IssueTrojanBench
[IssueTrojanBench](https://arxiv.org/abs/2607.20759)

系统构建 malicious issues、attack categories、delivery vectors，并评价多个 deployed coding-agent systems。

已占据：

> “malicious GitHub issue benchmark + 商业 coding agents ASR。”

但没有系统回答：

> 保持 model/scaffold/task 不变，只改变 capability-matched tool architecture 时，ASR 为什么变化？

## 11.6 Execution-Grounded Security Testing
[Paper](https://arxiv.org/abs/2607.22569)

方法学核心：

> 不要只看模型“说了什么”，要看它**实际执行了什么**。

用 tool invocation、runtime trace、filesystem diff、execution oracle 判断 security outcome。

本课题应该继承 execution-grounded measurement。

## 11.7 Permission Denied — 2026-08
[Paper](https://arxiv.org/abs/2608.02670)

研究企业 hardening policy 对 coding-agent success、cost、blocked behavior 的影响。

### 与本课题最关键区别

Permission Denied 的主 independent variable：

> **environment policy level**

推荐课题：

> **tool architecture × privilege granularity × adversarial SWE input**

也就是：

```text
interface representation
×
authority
×
attack
```

的交互。

---

# 12. 当前最重要的“缺口交叉图”

```text
The Devil Is in the Interface
Tool architecture
    ↓
Consistency / Exploration / Efficiency
(no adversarial security)

Permission Denied
Environment hardening
    ↓
Success / Cost
(no controlled tool-architecture factor)

IssueTrojanBench / Execution-Grounded
Malicious coding inputs
    ↓
Security outcomes
(no capability-matched tool-architecture intervention)

                     ↓

             Missing intersection

Tool Architecture
       ×
Privilege Granularity
       ×
Adversarial SWE Context
       ↓
Utility + Execution Security + Efficiency
```

这是截至 2026-08-15 prior-art screen 后最值得推进的交叉点。

---

# 13. Prior-Art Matrix

| Paper | 核心自变量 | SWE/repo | Utility | Security | Cost/Time | 受控 interface | 不能再 claim |
|---|---|---:|---:|---:|---:|---:|---|
| SWE-agent | ACI design | ✅ | ✅ | △ | △ | 部分 | ACI 本身影响 agent |
| Agentless | agentic pipeline | ✅ | ✅ | ❌ | ✅/部分 | △ | 越 agentic 越好 |
| SWE-Effi | scaffold/model | ✅ | ✅ | ❌ | ✅ | ❌ | 首次 correctness+cost/time |
| execute_code ablation | tool surface | ✅ | ✅ | ❌ | ✅ | ✅ | shell/MCP surface 效率比较 |
| Scaffolding Matters | MCP vs CLI + scaffold | ✅ | ✅ | ❌ | ✅ | 部分 | 首次 MCP vs CLI cost |
| Devil Is in Interface | 6 tool architectures | ✅ | ✅ | ❌ | ✅ | ✅✅ | 首次受控 tool-architecture study |
| AgentDojo | attack/defense | general | ✅ | ✅ | ❌ | ❌ | 首次 security+utility |
| SecureAgentBench | agent/model | ✅ | ✅ | ✅ output | △ | ❌ | 首次 correctness+secure code |
| Adversarial Bug Reports | malicious report | ✅ | ✅/部分 | ✅ | ✅/部分 | ❌ | 首次恶意 bug report |
| IssueTrojanBench | malicious issues | ✅ | △ | ✅ | ❌ | ❌ | 首次 malicious issue benchmark |
| Execution-Grounded | attack disguise | ✅ | △ | ✅ exec | ❌ | ❌ | 首次 execution-grounded security |
| Overeager | benign scope traps | ✅ | ✅ | ✅ auth | △ | framework | framework 不影响 authorization |
| Permission Denied | hardening policy | terminal | ✅ | policy | ✅ | ❌ | 首次 hardening–success–cost |
| Breaking Protocol | MCP architecture | general | 部分 | ✅ | latency | ✅ | 首次 MCP vs non-MCP security |
| MCP-SafetyBench | MCP attacks | repo included | ✅ | ✅ | ❌ | ❌ | 首次 MCP utility+security |
| AgentRFC/Thread | protocol composition | ❌ | ❌ | ✅ formal | ❌ | N/A | 首次 formal protocol security |

---

# 14. Novelty Audit：候选方向

| Candidate | Novelty | FSE fit | 近期可行性 | 风险 | 建议 |
|---|---:|---:|---:|---|---|
| A. 比较 SWE-agent/OpenHands/Agentless accuracy/cost | ★ | ★★★ | ★★★★★ | 已覆盖 | ❌ |
| B. Bash vs Atomic vs MCP performance/cost | ★★ | ★★★★ | ★★★★ | 2026 已直接做 | ❌ |
| C. 不同 agent 的 generated-code security | ★★ | ★★★★ | ★★★ | SecureAgentBench 等覆盖 | ⚠️ |
| D. malicious issues 攻击多个 coding agents | ★★ | ★★★★ | ★★★★ | IssueTrojanBench/MSR 覆盖 | ⚠️ |
| **E. capability-matched tool architecture × execution security × efficiency** | **★★★★** | **★★★★★** | **★★★★** | 方向发展很快 | **✅ 主推** |
| **F. tool architecture × privilege granularity 因果拆解** | **★★★★★** | **★★★★★** | **★★★☆** | 设计要求高 | **✅ 最有科研味** |
| G. A2A→MCP composition × SWE security/cost | ★★★★★ | ★★★★ | ★★ | 工程 scope 大 | 第二篇/备选 |
| H. risk-adaptive tool surface method | ★★★★ | ★★★★★ | ★★ | 易撞 privilege-control work | extension |

---

# 15. 推荐最终 Research Questions

## Central RQ

> **How do tool architecture and privilege granularity interact to shape the security–utility–efficiency frontier of repository-level coding agents?**

## RQ1 — Utility

> **How does tool architecture affect clean repository-level task success when underlying capabilities are held constant?**

测 issue resolve rate、tests、patch correctness、repeated-run consistency。

单独这一 RQ 不新，只作为 control。

## RQ2 — Execution Security

> **How does tool architecture affect execution-grounded attack success under adversarial repository and issue content?**

测：

- ASR；
- unsafe side-effect；
- unauthorized file/network/process operation；
- persistence；
- fake credential access。

## RQ3 — Privilege vs Interface

> **Are security differences caused by interface representation itself, or by differences in authority granted through that interface?**

建议 factorial：

```text
                Full / Ambient        Scoped / Least-Privilege

Bash            Bash-Full             Bash-Scoped
Atomic Tools    Atomic-Full           Atomic-Scoped
CodeAct         CodeAct-Full          CodeAct-Scoped
MCP(optional)   MCP-Full              MCP-Scoped
```

这是最有科研味的 RQ。

## RQ4 — Efficiency / Trade-off

> **What security gains or losses are obtained per unit of token cost, wall-clock time, and interaction complexity?**

记录 tokens、actual USD、wall-clock、tool calls、turns、denied actions、retries。

优先画 **Pareto frontier**，不要先造武断的加权总分。

## RQ5 — Why

> **Which interface properties explain security and efficiency differences?**

候选机制：

- ambient authority；
- action granularity；
- compound command；
- observability；
- reversibility；
- error feedback；
- context footprint；
- tool-schema verbosity；
- recoverability；
- instruction/data separation；
- least-privilege expressiveness。

---

# 16. Hypotheses：要验证，不要提前当结论

### H1 Architecture–Model Interaction
不同 model/scaffold 对 interface 的反应不同。已有工作已暗示，因此是 control/replication，不是主 novelty。

### H2 Ambient Authority
更自由的 tool surface 可能减少 interaction overhead，但在被劫持时增加 blast radius。

### H3 Structured Recovery
typed/scoped tools 即使不能消灭 prompt injection，也可能提升 detection、denial、recovery。

### H4 Security Tax 不一定成立
不要默认安全一定更贵。某些结构化工具也可能减少无效 retry，使 security 上升而 cost 下降。

---

# 17. 实验设计

## 17.1 第一原则：controlled experiment

主实验尽量固定：

```text
Same base model
Same scaffold
Same prompt
Same repository snapshot
Same task
Same budget
Same semantic capabilities
```

改变：

```text
Tool architecture
Privilege mode
Attack / benign condition
```

之后再加第二模型验证 `Model × Architecture` generalization。

---

# 18. Tool Architecture Arms

受时间限制，主实验最多建议 3 个。

## Arm A — Bash / Ambient Shell

```text
bash(command)
```

特点：自由、compound actions、易实现；但有 ambient authority，一个 command 可产生多个副作用。

## Arm B — Atomic Typed ACI

例如：

```text
read_file(path)
search(query, path)
edit_file(path, range, replacement)
run_test(target)
git_diff()
```

与 Bash 尽量 capability-matched。

## Arm C — CodeAct / execute_code

例如：

```text
execute_code(code)
```

可用 Python sandbox 或 MCP tool。

最新研究显示 CodeAct/Python 风格可减少 turns/token，但**安全意义仍值得系统研究**。

## MCP 是否做第四 arm？

第一版不建议把 MCP 放核心，因为：

- Breaking the Protocol 已做 MCP vs non-MCP；
- execute_code paper 已做 MCP code-only；
- MCP security benchmark 很多。

更合理：

> 主 paper 研究 tool architecture / authority。

如果框架稳定，再做：

```text
Direct typed API
vs
Semantically-identical MCP-wrapped API
```

作为 protocol extension。

---

# 19. Privilege Mode

## Full / Ambient

- broad repo filesystem；
- broad command execution；
- fake internal network service；
- broad subprocess。

## Scoped

- repo-root only；
- deny parent traversal；
- allowlisted commands；
- network restricted；
- fake credential scope；
- read/write/execute capabilities separated。

**所有 scoped tasks 必须先验证仍可解。** 否则 security policy 直接让 task impossible，会污染结果。

---

# 20. Benchmark

## 20.1 Clean

Pilot：

- 50–100 SWE-bench Verified / Live stratified tasks；
- executable test oracle。

可按 files touched、repo size、issue length、gold patch size、test runtime、task category 分层。

## 20.2 Paired Adversarial

理想：

```text
T_clean
T_attack
```

functional objective 不变，只加入 security carrier。

## 20.3 第一篇只做 2 类 carrier

### Carrier 1 — Malicious Issue / Bug Report
承接 Adversarial Bug Reports / IssueTrojanBench。

### Carrier 2 — Malicious Repository Context
如 README、AGENTS.md、test/log/documentation 中的 indirect instruction。

不要一口气做 6 类 carrier，否则条件数爆炸。

---

# 21. Security Ground Truth：必须 execution-grounded

不要只判断：

```text
LLM refused / did not refuse
```

而应该问：

```text
Did the forbidden side effect actually happen?
```

sandbox oracle 记录：

- filesystem diff；
- subprocess trace；
- network calls；
- fake credential access；
- process creation；
- git operations；
- persistence artifacts；
- tool arguments；
- policy denials。

核心：

\[
ASR =
\frac{\#\ verified\ unsafe\ effects}
{\#\ attack\ trials}
\]

以及：

\[
SecureCompletion = TaskSolved \land \neg UnsafeEffect
\]

这样“全部拒绝”不会被误判为最佳系统。

---

# 22. Outcome Metrics

## Utility
- Resolve@1；
- test pass；
- patch correctness；
- consistency。

## Security
- execution-grounded ASR；
- scope violation rate；
- secure completion；
- privilege violation attempts；
- blast radius；
- recovery after block。

## Efficiency
- input/output/cache tokens；
- actual USD；
- wall-clock；
- tool calls；
- turns；
- repeated/failed actions。

## Behavioral
- command compounding；
- files accessed；
- relevant-file recall；
- denied-action recovery；
- error loops；
- action diversity。

---

# 23. Statistics

由于是 paired study：

### Binary
- McNemar；
- bootstrap CI；
- odds ratio。

如果样本足够，可用 mixed-effects logistic model：

\[
logit(Y)
=
Architecture
+
Privilege
+
Attack
+
Architecture \times Privilege
+
Architecture \times Attack
+
Model
+
TaskComplexity
+
u_{task}
\]

### Cost / Tokens / Latency

考虑长尾：

- median / IQR；
- bootstrap CI；
- paired Wilcoxon；
- success-conditioned cost；
- failure-conditioned cost；
- attacked-run cost；
- blocked-but-recovered cost。

---

# 24. 最重要的 Figures

## Figure 1 — Security–Utility–Efficiency Frontier

每个 interface × privilege condition 一个点：

- x = utility；
- y = secure completion；
- point size = cost；
- shape = model。

核心问题：

> 哪些配置 Pareto-dominated？

## Figure 2 — Tool Architecture / Authority Matrix
比较 Bash / Atomic / CodeAct / optional MCP 的表达方式与 authority。

## Figure 3 — Failure Taxonomy

```text
Failure
├── functional
│   ├── localization
│   ├── incorrect edit
│   └── test-loop
└── security
    ├── instruction hijack
    ├── scope expansion
    ├── unsafe shell
    ├── secret access
    └── persistence
```

---

# 25. 可能形成的 Contributions

1. **Controlled empirical study**：拆开 tool architecture 与 privilege granularity。
2. **Paired clean/adversarial benchmark protocol**：保持同一 SWE objective。
3. **Joint utility–security–efficiency characterization**。
4. **Mechanistic analysis**：解释 interface abstraction 何时改善/损害 security、cost、consistency、recovery。
5. **Design implications for secure ACI / harness engineering**。

如果时间允许，再加入：

6. **Risk-adaptive tool exposure / privilege escalation**。

---

# 26. Study + Method 升级

如果 empirical study 发现：

```text
Simple tasks → Bash efficient
High-risk tasks → Atomic Scoped safer
Complex tasks → CodeAct efficient but needs gating
```

可以提出：

## Risk-Adaptive ACI

```text
Task / Current Phase
        ↓
Risk Estimator
        ↓
Expose minimal required tools
        ↓
Need additional authority?
        ↓
Structured escalation
        ↓
Execute
```

按 phase：

```text
READ: read/search only
EDIT: repo-scoped write
TEST: allowlisted test commands
INSTALL/NETWORK: escalation
SECRET/DEPLOY: deny or human approval
```

但必须区别于 Progent、AgenTRIM 等已有 privilege-control work。新意应来自：

> **SWE workflow-aware + task/phase-conditioned + empirically derived dynamic surface switching**。

---

# 27. 第二路线：Protocol Composition（高风险备选）

如果导师特别重视“协议”，可以做：

> **How do cross-protocol compositions affect security–utility–efficiency in multi-agent SWE workflows?**

例如：

```text
Planner
  |
 A2A
  ↓
Coder
  |
 MCP
  ↓
Tools
```

测：

- success；
- delegation integrity；
- context loss；
- consent/credential propagation；
- ASR；
- latency/token；
- coordination rounds。

AgentRFC / AgentThread 已做 formal composition safety，但 real SWE workload 的多维 empirical tradeoff 仍有空间。

风险：

- MCP/A2A 不同层；
- multi-agent 新变量太多；
- engineering scope 大。

当前更适合作为 follow-up。

---

# 28. 建议明确砍掉

### ❌ 产品排行榜
`Claude Code vs Codex vs OpenHands` 本身解释力弱。

### ❌ MCP vs CLI 的简单 performance/cost 比较
2026 已有多篇直接工作。

### ❌ 泛化的 single-agent vs multi-agent
问题太泛。必须变成 “under what conditions”。

### ❌ 把 security 混成一个指标
区分：
- agent execution security；
- generated-code security；
- agent-for-cybersecurity。

当前第一篇建议只做 **execution / authorization security**。

### ❌ 只靠文字回答判定安全
必须 execution-grounded。

---

# 29. P0：必须精读的 12 组论文

## P0-1 SWE-bench — ICLR 2024
[SWE-bench](https://arxiv.org/abs/2310.06770)

重点：benchmark construction、execution evaluation、task definition、validity。

回答：
> repository-level SWE 为什么适合 Agent？

## P0-2 SWE-agent — NeurIPS 2024
[SWE-agent](https://arxiv.org/abs/2405.15793)

重点：ACI、design principles、ablation、environment feedback、security appendix。

回答：
> interface 为什么能独立于 model 成为研究变量？

## P0-3 Agentless — FSE 2025
[Agentless](https://arxiv.org/abs/2407.01489)

重点：为什么挑战过度 agentic、localize–repair–validate。

回答：
> autonomy 的真实价值是什么？

## P0-4 SWE-Effi
[SWE-Effi](https://arxiv.org/abs/2509.09853)

重点：resource metrics、scaffold×model、expensive failures、token/time。

回答：
> 为什么 pass rate 不是完整 Agent metric？

## P0-5 The Devil Is in the Interface — COLM 2026
[Paper](https://arxiv.org/abs/2608.11386)

**当前最高优先级。**

重点：capability matching、six architectures、controls、consistency、exploration、efficiency、actor×interface interaction。

回答：
> 不改变 capabilities 时，tool architecture 到底改变什么？

## P0-6 execute_code Ablation — 2026
[Paper](https://arxiv.org/abs/2607.10569)

重点：baseline/bash/code-only、matched harness、success/failure-conditioned cost。

回答：
> single execute_code surface 的效率来自哪里？

## P0-7 AgentDojo — NeurIPS 2024
[AgentDojo](https://arxiv.org/abs/2406.13352)

重点：utility/security joint evaluation、indirect injection、attack/defense。

回答：
> 怎样避免“全部拒绝 = 最安全”？

## P0-8 Permission Denied — 2026
[Paper](https://arxiv.org/abs/2608.02670)

重点：policy levels、solvability、success-cost、blocked action behavior。

回答：
> 如何公平测 hardening 的代价？

## P0-9 IssueTrojanBench — 2026
[Paper](https://arxiv.org/abs/2607.20759)

重点：malicious issue construction、delivery vector、attack outcome。

回答：
> malicious issue benchmark 已经做到哪里？

## P0-10 Execution-Grounded Security Testing — 2026
[Paper](https://arxiv.org/abs/2607.22569)

重点：execution oracle、trace、filesystem diff、text-vs-action gap。

回答：
> security ground truth 怎么设计？

## P0-11 Breaking the Protocol — 2026
[Paper](https://arxiv.org/abs/2601.17549)

重点：controlled MCP vs non-MCP、ASR、latency、mitigation。

回答：
> 哪些 MCP vs direct claims 已经不能再做？

## P0-12 AgentRFC / AgentThread
[AgentRFC](https://arxiv.org/abs/2603.23801)  
[AgentThread](https://arxiv.org/abs/2606.28690)

重点：protocol stack、security invariants、composition safety、responsibility gaps。

回答：
> protocol composition formal line 做到了哪里？

---

# 30. P1：第二轮重要论文

## Coding Agent Architecture
1. [AutoCodeRover](https://arxiv.org/abs/2404.05427)
2. [SpecRover](https://arxiv.org/abs/2408.02232)
3. [MAGIS](https://arxiv.org/abs/2403.17927)
4. [RepoGraph](https://openreview.net/forum?id=dw9VUsSHGB)
5. [SWE-Search](https://arxiv.org/abs/2410.20285)
6. [OpenHands](https://arxiv.org/abs/2407.16741)
7. [SWE-Gym](https://arxiv.org/abs/2412.21139)
8. [SWE-smith](https://arxiv.org/abs/2504.21798)

## Efficiency / Harness
9. [How Do AI Agents Spend Your Money?](https://arxiv.org/abs/2604.22750)
10. [The Scaffolding Matters More Than the Interface](https://arxiv.org/abs/2608.08654)
11. [Baselines Before Architecture](https://arxiv.org/abs/2607.13085)
12. [Harness-IF](https://arxiv.org/abs/2608.11727)

## Agent / Coding Security
13. [Progent](https://arxiv.org/abs/2504.11703)
14. [SecureAgentBench](https://arxiv.org/abs/2509.22097)
15. [Overeager Coding Agents](https://arxiv.org/abs/2605.18583)
16. [SNARE](https://arxiv.org/abs/2605.28122)
17. [Malicious Skill Files in Coding Agents](https://arxiv.org/abs/2608.05223)
18. [Demystifying Prompt Injection Attacks on Agentic AI Coding Editors](https://arxiv.org/abs/2509.22040)
19. [Real-World Prompt Injection Attacks in AI-Powered CI/CD](https://arxiv.org/abs/2606.09935)
20. [The Balkanization of Execution-Security Research for AI Coding Agents](https://arxiv.org/abs/2607.05743)

## MCP / Protocol
21. [MCP Safety Audit](https://arxiv.org/abs/2504.03767)
22. [MCPSecBench](https://arxiv.org/abs/2508.13220)
23. [MCP-SafetyBench](https://arxiv.org/abs/2512.15163)
24. [Comparative Study of MCP and A2A](https://arxiv.org/abs/2607.23884)

---

# 31. P2：Method / Protocol 深挖

- [AgenTRIM: Tool Risk Mitigation for Agentic AI](https://arxiv.org/abs/2601.12449)
- capability/revocable-resource control work；
- DGM / Live-SWE-agent / harness evolution；
- A2A/MCP/AgentRFC/AgentThread/MPAC。

---

# 32. 两周学习 Sprint

| Day | 主题 | 论文 | 输出 |
|---|---|---|---|
| 1–2 | Problem + ACI | SWE-bench, SWE-agent | SWE lifecycle + ACI taxonomy |
| 3 | 反方 | Agentless | autonomy memo |
| 4–5 | Efficiency | SWE-Effi, Spend Your Money | metrics.md |
| 6–7 | Tool Architecture | execute_code, Devil, Scaffolding Matters | Prior-art matrix v1 |
| 8–9 | General Security | AgentDojo, Progent | Threat model v1 |
| 10–11 | Coding Security | IssueTrojan, Execution-Grounded, Overeager, MSR bug reports | paired attack design |
| 12 | Hardening | Permission Denied | privilege modes + solvability protocol |
| 13 | Protocol | Breaking Protocol, AgentRFC | MCP-in-first-paper decision memo |
| 14 | Novelty review | all | final gap matrix + advisor meeting |

---

# 33. Zotero 每篇论文笔记模板

```markdown
# Paper

## 1. Problem
作者到底回答什么？

## 2. Unit of Intervention
- model?
- scaffold?
- tool architecture?
- tool set?
- privilege?
- protocol?
- prompt?
- policy?

## 3. Controls
哪些变量固定？

## 4. Task / Benchmark

## 5. Utility Metric

## 6. Security Threat Model
- attacker
- asset
- trust boundary
- attack carrier
- forbidden effect

## 7. Security Metric
是否 execution-grounded？

## 8. Efficiency
- tokens
- dollars
- latency
- steps

## 9. Main Finding

## 10. Threats to Validity

## 11. Artifact
是否有 code/data/traces？

## 12. What This Paper Occupies
以后不能再 claim 什么 novelty？

## 13. What Remains Open

## 14. Connection to My FSE Study
与 Tool Architecture × Privilege × Security × Efficiency 的关系？
```

---

# 34. 和导师沟通的 10 个核心问题

1. 核心 independent variable 锁定为 **tool architecture**，而不是产品，可以吗？
2. 是否把 **privilege granularity** 作为第二变量，拆 interface vs authority？
3. security 是否明确只做 **execution/authorization security**，先不做 generated-code security？
4. 是否接受 **paired clean/adversarial SWE tasks**？
5. 是否只做 2 类 attack carrier，避免 taxonomy 太广？
6. 是否固定一个 scaffold + 一个强 model 做主实验，再加第二 model generalization？
7. MCP 是否只放 extension，而不作为主线？
8. contribution 以 empirical knowledge 为主，还是必须再做 adaptive ACI method？
9. `The Devil Is in the Interface` 这篇 2026-08 新论文是否改变原选题？
10. FSE timeline 下，benchmark construction 和 full-factorial experiment 哪个优先？

---

# 35. 和导师可以直接讲的 1 分钟版本

> SWE-agent 提出了 ACI，证明 coding agent 的能力不仅由模型决定，也由它与计算机交互的接口决定。之后 SWE-Effi、execute_code ablation，以及刚出现的 COLM 2026 `The Devil Is in the Interface` 已经比较系统地研究了 interface/tool architecture 对正确率、一致性和 token/step efficiency 的影响，所以单纯做“不同 agent/tool 的 performance/cost 比较”已经不够新。
>
> 另一条文献线 AgentDojo、IssueTrojanBench、Execution-Grounded Security Testing、Permission Denied 等已经说明 coding/tool-using agents 存在 prompt injection、越权和执行层风险，但这些工作大多没有在 capability-matched 的 tool architecture 上做因果比较。
>
> 我现在想把问题收敛成：在同一个 model、scaffold、task 和能力集合下，只改变 tool architecture，再独立改变 privilege granularity，研究它们对 correctness、execution security、latency/token/cost 的作用和交互，从而回答 structured ACI 的安全性到底来自接口设计本身，还是来自权限收缩，以及在什么情况下额外的 Agent 权限真正值得。

---

# 36. Potential Titles

### 首选
**The Price of Power: Security–Utility–Efficiency Trade-offs in Tool Architectures for Software Engineering Agents**

### 更 FSE / empirical
**How Much Authority Should a Coding Agent Have? A Controlled Study of Tool Architecture and Privilege in Repository-Level Software Engineering**

### 更 ACI
**From ACI to Secure ACI: Disentangling Interface Design and Privilege in Autonomous Software Engineering**

不推荐：

- Comparing MCP and A2A for Coding Agents
- An Evaluation of SWE-Agent, OpenHands, and Codex
- A Benchmark of Agent Tools

---

# 37. Pilot 成功/失败判据

建议先做：

```text
20–30 tasks
×
3 tool architectures
×
2 privilege modes
×
clean + attack
×
1 model
```

### Pattern A
same clean success, security differs strongly  
→ **tool architecture is security-relevant**

### Pattern B
security similar, scoped mode reduces blast radius  
→ **authority dominates representation**

### Pattern C
interface × privilege strong interaction  
→ **最强主故事**

### Pattern D
所有条件都差不多  
→ 快速改 attack carrier / task complexity / recovery / protocol composition，而不是继续烧预算。

---

# 38. Novelty Watch：每周追踪

2026-08 前半月就出现：

- Permission Denied；
- The Scaffolding Matters More Than the Interface；
- The Devil Is in the Interface；
- Harness-IF；
- malicious skill-interface security work。

建议每周搜索：

```text
"coding agent" tool architecture security
"coding agent" interface security
"coding agent" privilege benchmark
"coding agent" authorization tool
"SWE-bench" security tool interface
"agent-computer interface" security
"MCP" coding agent security benchmark
"prompt injection" coding agent repository
"tool surface" coding agent cost security
"agent harness" security software engineering
```

平台：

- arXiv cs.SE / cs.CR / cs.AI；
- Google Scholar；
- OpenReview；
- ACM DL；
- DBLP；
- FSE / ICSE / ASE / ISSTA；
- S&P / USENIX Security / CCS / NDSS；
- NeurIPS / ICML / ICLR / COLM。

---

# 39. 最终判断

原始课题：

> Agent 协议/技术/工具 × coding domain × correctness/security/time/cost

**方向正确，但 formulation 太宽，且已有工作吃掉很多 gap。**

收敛后：

> **Tool Architecture × Privilege Granularity × Adversarial SWE Context → Utility + Execution Security + Efficiency**

截至 2026-08-15 prior-art screen，它是更清楚、更能控制变量、也更符合 FSE empirical-study 叙事的切入点。

最关键的新知识不应该是：

> “Atomic 比 Bash 安全 8%。”

而应该是：

> **Which properties of an agent-computer interface determine whether additional capability and authority translate into useful work, security risk, or wasted resources—and under what conditions?**

---

# 40. Reference Index

## Foundations
- [SWE-bench](https://arxiv.org/abs/2310.06770)
- [SWE-agent](https://arxiv.org/abs/2405.15793)
- [AutoCodeRover](https://arxiv.org/abs/2404.05427)
- [Agentless](https://arxiv.org/abs/2407.01489)
- [SpecRover](https://arxiv.org/abs/2408.02232)
- [MAGIS](https://arxiv.org/abs/2403.17927)
- [RepoGraph](https://openreview.net/forum?id=dw9VUsSHGB)
- [SWE-Search](https://arxiv.org/abs/2410.20285)
- [OpenHands](https://arxiv.org/abs/2407.16741)
- [SWE-Gym](https://arxiv.org/abs/2412.21139)
- [SWE-smith](https://arxiv.org/abs/2504.21798)

## Efficiency / Interface
- [SWE-Effi](https://arxiv.org/abs/2509.09853)
- [How Do AI Agents Spend Your Money?](https://arxiv.org/abs/2604.22750)
- [When Does Restricting a Coding Agent to execute_code Help?](https://arxiv.org/abs/2607.10569)
- [The Scaffolding Matters More Than the Interface](https://arxiv.org/abs/2608.08654)
- [The Devil Is in the Interface](https://arxiv.org/abs/2608.11386)
- [Harness-IF](https://arxiv.org/abs/2608.11727)
- [Baselines Before Architecture](https://arxiv.org/abs/2607.13085)

## General Agent Security
- [AgentDojo](https://arxiv.org/abs/2406.13352)
- [Progent](https://arxiv.org/abs/2504.11703)
- [AgenTRIM](https://arxiv.org/abs/2601.12449)

## Coding-Agent Security
- [SecureAgentBench](https://arxiv.org/abs/2509.22097)
- [Adversarial Bug Reports as a Security Risk in LLM-based APR](https://doi.org/10.1145/3793302.3793352)
- [Overeager Coding Agents](https://arxiv.org/abs/2605.18583)
- [SNARE](https://arxiv.org/abs/2605.28122)
- [IssueTrojanBench](https://arxiv.org/abs/2607.20759)
- [Execution-Grounded Security Testing](https://arxiv.org/abs/2607.22569)
- [Permission Denied](https://arxiv.org/abs/2608.02670)
- [Malicious Skill Files in Coding Agents](https://arxiv.org/abs/2608.05223)
- [Demystifying Prompt Injection Attacks on Agentic AI Coding Editors](https://arxiv.org/abs/2509.22040)
- [Real-World Prompt Injection Attacks in AI-Powered CI/CD](https://arxiv.org/abs/2606.09935)
- [Execution-Security SoK](https://arxiv.org/abs/2607.05743)

## MCP / Protocol Security
- [MCP Safety Audit](https://arxiv.org/abs/2504.03767)
- [MCPSecBench](https://arxiv.org/abs/2508.13220)
- [MCP-SafetyBench](https://arxiv.org/abs/2512.15163)
- [Breaking the Protocol](https://arxiv.org/abs/2601.17549)
- [AgentRFC](https://arxiv.org/abs/2603.23801)
- [AgentThread](https://arxiv.org/abs/2606.28690)
- [Comparative Study of MCP and A2A](https://arxiv.org/abs/2607.23884)

---

# 41. 下一步

1. 今天先精读 **The Devil Is in the Interface**。
2. 接着读 **Permission Denied**。
3. 再读 **IssueTrojanBench + Execution-Grounded Security Testing**。
4. 用第 33 节 Zotero 模板统一整理。
5. 画一张：

```text
Tool Architecture
Privilege
Attack Surface
Outcome Metrics
```

6. 和导师确认是否接受 **Tool Architecture × Privilege** 为两个核心 independent variables。
7. 导师认可后立刻做 20–30 task pilot，不再无限扩文献。
