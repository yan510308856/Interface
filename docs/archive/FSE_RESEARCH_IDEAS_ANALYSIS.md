# FSE Empirical Study Research Idea Analysis

> **研究对象**：`agents_basic_idea.pdf` 中按手写编号识别出的 5 个 research ideas。  
> **分析日期**：2026-08-16（Asia/Shanghai）。  
> **PDF 实际读取位置**：[`docs/agents_basic_idea.pdf`](/Users/yan/Downloads/Agents_Research/docs/agents_basic_idea.pdf)。原始请求中的 `/Users/yan/Downloads/agents_basic_idea.pdf` 在当前工作区不存在；分析使用了工作区内同名 PDF。

## 1. Executive Summary

### 结论先行

这 5 个 idea 不是 5 个同等成熟的论文题目。原始表述中：

1. **最推荐 Idea 5，但必须改变问题边界。** 单纯研究“tool architecture 如何影响 coding-agent performance”已经与 2026 年最新的接口架构研究高度重叠；单纯研究“权限策略对 agent 成功率和成本的影响”也已被近期 hardened-environment 工作覆盖。真正仍有发表潜力的版本是：在相同模型、任务、工具能力和运行环境下，**因果地同时操纵 tool-interface architecture 与 privilege granularity，并在 clean / adversarial repository 条件下测量 security–utility–efficiency frontier**。
2. **第二推荐是 Idea 2 与 Idea 4 的合并版。** 它不应再以“提出一个新 protocol”作为主贡献，而应作为跨 coding-agent architecture 的 empirical retrofit study：哪些安全风险能由 capability-aware runtime/protocol layer 稳定缓解，哪些风险属于模型语义理解、任务规划或供应链问题，因而不能被 protocol 单独解决。
3. **Idea 3 应并入 Idea 5，而不是作为独立论文。** 它的 trade-off 和 trajectory mechanism 是很好的 RQ3/RQ4，但作为独立题目会与 agent-framework evaluation、resource-efficiency、failure-trajectory 等工作重复。
4. **Idea 1 是研究计划的 umbrella question，不是可直接投稿的单篇 FSE 题目。** “communication + tool integration + capability + safety + efficiency” 范围过大，而且与 Ideas 3/5 重叠。
5. **Idea 4 不建议单独推进。** Protocol-driven multi-agent coordination、runtime defense、policy enforcement 和 propagation 已有相邻工作；原始 Idea 4 同时放入跨架构 retrofit、utility、efficiency、generalization 和 cross-agent propagation，难以形成可解释的 treatment，也会造成 scope explosion。应合并到 Idea 2，并把 multi-agent propagation 降为后续工作。

### 最终推荐排序

| Rank | Idea | 推荐状态 | Novelty Risk | 判断 |
|---:|---|---|---|---|
| 1 | Idea 5：tool architecture × privilege granularity | **推荐，需按本文 pivot** | Medium（原始版本 High） | 最清晰的因果实证缺口，SE relevance、security value、FSE fit 都高 |
| 2 | Idea 2 + Idea 4：跨 coding-agent 的 capability-aware security retrofit | **推荐合并版** | Medium–High（原始版本 High/Very High） | 可形成 protocol-solvable vs protocol-insufficient 的新经验知识 |
| 3 | Idea 3：capability–safety–efficiency 与 trajectory mechanism | **并入 Idea 5** | High（独立版本） | 可作为 mechanism / trade-off 子研究，但不宜单独投稿 |
| 4 | Idea 1：communication/tool integration 总体问题 | **降级为 umbrella** | High | 过宽、变量定义不够清楚、与其他 idea 重复 |
| 5 | Idea 4：单独的跨架构 protocol retrofit + propagation | **放弃单独推进** | Very High | 已被相邻工作部分覆盖，scope 过大，应并入 Idea 2 |

### 最小可发表主张

最值得验证的核心主张不是“某种工具更好”或“权限越小越安全”，而是：

> 在 repository-level coding tasks 中，tool-interface representation 与 privilege granularity 是两个可分离的 causal factors；它们可能产生 interaction。一个接口可能提高 task utility，却因为 compound commands 或 ambient authority 增加 execution risk；一个 least-privilege policy 可能降低 attack success，却把失败转化为 denial、retry、timeout 和 monetary cost。这个 interaction 是否稳定、在什么 task / attack / model 条件下成立，当前仍缺少 capability-matched、execution-grounded、paired 的系统研究。

这个主张既不是新的 agent framework，也不是新的 benchmark；它的贡献可以是可复现的 empirical knowledge。

## 2. Research Landscape

### 2.1 检索与证据边界

本报告采用了以下检索策略：

- 时间边界：优先覆盖 2024–2026，向前追溯 SWE-agent、OpenHands、AgentDojo 等奠基工作。
- 数据源与入口：arXiv、OpenAlex、Crossref、Semantic Scholar 可检索元数据；ACM/IEEE/NeurIPS/ICLR/ICML/ACL/ICSE 官方页面；官方 GitHub / project pages。Google Scholar 页面在当前环境中不作为唯一证据源。
- citation chaining：从 SWE-agent → tool-interface follow-up，从 AgentDojo → CaMeL / AgentArmor / Task Shield，从 SEMAP → protocol-driven coordination，从 SecureVibeBench / SEC-bench → secure repository-agent evaluation 追踪后续工作与相邻工作。
- 证据分层：已打开正文或官方论文页面的工作用于关键 novelty 判断；只有搜索结果或元数据的工作不用于声称其完整实验结论，并在文中标为 **metadata-only / not fully verified**。
- “没有论文”不作绝对断言。本文使用更严格的表述：**在本次检索边界内未定位到同时满足这些条件的工作**。

### 2.2 当前研究已经覆盖的板块

| 板块 | 代表工作 | 已知结论或能力 | 对本项目的限制 |
|---|---|---|---|
| Agent-computer interface | SWE-agent；OpenHands | 工具接口、沙箱和 scaffold 会改变 coding-agent 行为与 SWE-bench 表现 | 不是安全/权限因果研究 |
| Agent framework comparison | Comprehensive Empirical Evaluation of Agent Frameworks | 在 code-centric tasks 上比较 framework 的 effectiveness、efficiency、token overhead | framework、model、prompt、tool 和 scaffold 往往共同变化，不能识别单一因果因素 |
| Tool-interface architecture | The Devil Is in the Interface | 在 capability 尽量相近时比较六类 tool architecture，发现 consistency / exploration / token behavior 差异 | 没有 execution security 或 privilege factor；机制因果仍有 caveat |
| Scaffolding and MCP/CLI | The Scaffolding Matters More Than the Interface | scaffold 常常比表面接口更决定结果，MCP/CLI 成本差异大 | 单一私有 git task；不能作为 repo-level security generalization |
| Hardened policy / privilege | Permission Denied | strict policy 可造成 success loss 和 cost inflation，policy-dependent | 主要是 Terminal-Bench hardened environment；没有 tool-interface × privilege factorial |
| Protocol-driven multi-agent coordination | SEMAP | structured contract、lifecycle、verification 可减少若干多 agent failure | HumanEval / deployment / vulnerability tasks；不是跨 repo-level coding-agent 的 security retrofit |
| Prompt injection / tool poisoning | AgentDojo、ASB、MCPTox、IssueTrojanBench | agent 会被 untrusted data、malicious tool metadata、issue content 影响 | 多数不是同一套 repository coding tasks 下的 interface/authority causal study |
| Secure code generation benchmark | SEC-bench、SecureVibeBench、SUSVIBES、SecRepoBench | code agent 能力与安全性可以显著脱钩，且 secure outcome 很低 | benchmark 研究告诉我们“问题存在”，但没有识别 tool architecture / privilege 的原因 |
| Runtime defenses | CaMeL、AgentArmor、Task Shield、MELON | capability、data-flow、task-alignment 等 runtime/defense layer 可降低部分攻击 | 主要是通用 agent benchmark；跨 coding-agent、repo workload、utility/time/cost 的统一比较不足 |
| Efficiency / trajectory | SWE-Effi、Understanding Code Agent Behaviour、SWE-Search | token snowball、长轨迹、retry、探索方式与效率/成功有关 | 大多描述或优化 trajectory，不把 security 与 authority 纳入同一 causal design |

### 2.3 文献链条与关键碰撞

1. **SWE-agent → tool architecture follow-up**：SWE-agent 证明 agent-computer interface 是 SE agent 的重要设计层；2026 的 *The Devil Is in the Interface* 已把“接口表示影响 coding-agent 行为”推进到控制能力相近的多架构比较。因此，Idea 5 不能再只问“Bash vs atomic tools 谁成功率更高”。
2. **AgentDojo → runtime defenses**：AgentDojo 建立了 tool-integrated prompt-injection evaluation；CaMeL、AgentArmor、Task Shield 等进一步研究 capability/data-flow/task-alignment defense。因此，Idea 2/4 不能把“加一个安全 middleware 后 ASR 下降”本身当作 novelty。
3. **SEMAP → protocol retrofit**：SEMAP 已将 behavioral contract、structured message 和 lifecycle verification 用于多 agent software engineering / vulnerability tasks。因此，Idea 4 的“protocol 能否改善 multi-agent coordination”需要加上 coding-agent repo workload、authority boundary、execution evidence 和 cost，否则会重复。
4. **Permission Denied → privilege cost**：hardened environments 已显示 permission policy 会影响 success、timeout 和 cost。因此，Idea 5 必须把 privilege 与 interface architecture 分开操纵，而不是只做“安全配置开/关”。
5. **SecureVibeBench / SEC-bench → security outcome**：已有工作说明 repository-level secure coding agent 的 security outcome 远低于 functional outcome。新的贡献应解释“哪种 interaction / authority design 导致风险”，而不是再做一个安全 benchmark leaderboard。

## 3. Idea 1

### Original Idea

PDF 第 1 页顶部的核心表述是：

> “How do communication and tool-integration mechanisms shape the capability–safety–efficiency trade-offs of modern coding agents?”

#### 结构化提取

| 字段 | 解释 |
|---|---|
| Idea 名称 | Communication and tool-integration mechanisms in modern coding agents |
| 原始研究目标 | 研究 communication 与 tool integration 如何塑造 capability–safety–efficiency trade-off |
| 研究对象 | modern coding agents；但 agent architecture、model、tool、communication 的边界未定义 |
| 软件工程场景 | repository-level coding / software-engineering tasks（原文未明确 benchmark） |
| AI / LLM / Agent 技术 | LLM coding agents、tool use、可能的 multi-agent communication |
| 自变量 | communication mechanism、tool-integration mechanism；可能还包括 protocol、topology、tool granularity、memory、number of agents |
| 因变量 | capability / task success；safety / unsafe action；efficiency / time、tokens、cost |
| 可能实验对象 | 多个 coding-agent frameworks、models、tool interfaces、communication protocols |
| 预期贡献 | 解释能力、安全、效率之间的 trade-off，并给出 agent design implication |
| 模糊点 | “communication”是 agent-to-agent 还是 agent-to-tool？“capability”是 pass rate 还是 broader ability？安全 threat model、权限边界、benchmark、单位分析和控制变量均未定义 |

#### 明确化句子

原始 idea 不能自然形成一个唯一的 X/Y/Z。最接近的可执行版本是：

> **We study whether and how capability-matched tool-interface architecture and privilege granularity affect repository-level coding-agent task success, execution security, and resource cost under clean and adversarial repository conditions.**

这已经实质上收敛为 Idea 5 的问题；因此 Idea 1 不应与 Idea 5 并行开展。

### Related Work

#### Closest Work

| 论文 | 它研究了什么 | 已解决什么 | 对 Idea 1 仍未解决什么 |
|---|---|---|---|
| [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793) — John Yang et al., 2024, arXiv preprint | 设计 custom agent-computer interface，并在 SWE-bench / HumanEvalFix 上评估 | 说明 interface 是 coding-agent capability 的重要设计变量 | 没有 security policy、privilege factor，也没有把 communication、security、efficiency 放在同一控制实验中 |
| [OpenHands: An Open Platform for AI Software Developers as Generalist Agents](https://arxiv.org/abs/2407.16741) — Xingyao Wang et al., 2024, ICLR 2025 | 开放 coding-agent platform，含 coding、CLI、web、sandbox 等能力 | 提供可复用 agent platform 和评测基础 | 平台论文不是 communication/tool/authority 的 causal decomposition |
| [A Comprehensive Empirical Evaluation of Agent Frameworks on Code-centric Software Engineering Tasks](https://arxiv.org/abs/2511.00872) — Zhuowen Yin et al., 2025, arXiv preprint | 比较 7 个 general-purpose agent frameworks 在开发、漏洞检测、程序修复任务上的效果与效率 | 提供 framework-level empirical baseline，揭示长轨迹、反思、token overhead 等差异 | framework、model、prompt、tool、scaffold 共同变化，无法回答某个 communication/tool factor 的因果效应 |
| [The Devil Is in the Interface: Evaluating How Tool Architecture Shapes Coding Agent Behavior](https://arxiv.org/abs/2608.11386) — Xiangzhe Xu et al., 2026, arXiv preprint | 六类 tool architectures、三个模型、多次 rollout；控制底层能力后比较 resolve、consistency、exploration、tokens | 已直接覆盖 tool architecture 对 coding-agent behavior 的主要 effect | 没有 adversarial repository security、privilege granularity，也未直接验证其 proposed mechanism 的 causal link |
| [The Scaffolding Matters More Than the Interface](https://arxiv.org/abs/2608.08654) — Forment et al., 2026, arXiv preprint | 在一个私有 git task 上比较 7 种 scaffolding 与 MCP/CLI 成本 | 证明 scaffold/interface 的表面差异可能掩盖更强的 scaffold effect | 单任务、非 repository benchmark、没有 execution security 和权限因果分解 |

#### Enabling Work / Empirical / Security

- [GitTaskBench](https://arxiv.org/abs/2508.18993)（Ni et al., 2025, arXiv）提供多 domain、multi-modal、realistic repository task 与 alpha-value；适合作为任务覆盖的补充，但其综合指标不能替代 security outcome。
- [SWE-EVO](https://arxiv.org/abs/2512.18470)（Thai et al., 2025, arXiv）强调 long-horizon software evolution；可用于外部效度，但其重点不是 tool authority。
- [SWE-Effi](https://arxiv.org/abs/2509.09853)（Fan et al., 2025, arXiv）研究 token snowball 与 token/time trade-off；支持效率测量，但未纳入 execution security。
- [AgentDojo](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html)（NeurIPS 2024）与 [Agent Security Bench](https://luckfort.github.io/ASBench/)（ICLR 2025）提供通用 agent attack/defense evaluation；它们说明安全指标可操作化，但不是 coding-agent repo workload。
- [Permission Denied](https://arxiv.org/abs/2608.02670)（Davidovich et al., 2026, arXiv）直接说明 policy hardening 会带来 success loss 与 cost inflation；它是 Idea 1/5 的重要 collision，强化了“不能只比较功能成功率”的要求。

### Research Gap

#### 已知什么？

当前研究已分别证明：

1. agent-computer interface、scaffold 和 framework 会影响 coding-agent performance；
2. token、trajectory、retry 和 exploration 会影响效率与成功；
3. untrusted repository / tool metadata 可以诱导不安全行为；
4. restrictive policy 会影响 success、timeout 和成本；
5. secure code generation 的 functional outcome 与 security outcome 可以严重脱钩。

#### 未知什么？

在本次检索边界内，尚未定位到一个同时满足以下条件的研究：

- 在相同模型、任务、prompt、timeout、retry budget 和 underlying tool capability 下，**独立操纵** tool-interface representation 与 privilege granularity；
- 同时使用 clean 与 adversarial repository conditions；
- 以真实执行结果区分 unauthorized action、unsafe side effect、secret/canary access 与 task failure；
- 统一测量 success、security、time、tokens、tool calls 和 monetary cost；
- 用 paired / blocked design 和 mixed-effects analysis 分离 task、repository、model、agent scaffold 的影响。

#### 为什么仍然不知道？

既有 framework studies 常把多个因素 bundled；security studies 常固定 agent interface 或只在通用 benchmark 中操作；policy studies 常固定任务环境；tool-interface studies 尚未将 privilege 与 adversarial repository 放入同一 factorial design。这会导致目前无法回答：某个安全收益究竟来自 interface representation、authority restriction，还是 scaffold/model 的其他差异。

#### Gap 是否足以支撑 FSE？

**原始 Idea 1：不够。** 它只是一个研究纲领，无法定义单一 treatment 和 estimand。  
**收敛后的版本：足够，但等同于 Idea 5 的研究问题。** 其价值来自因果归因和设计 implication，而不是再做一张 agent leaderboard。

### Novelty Analysis

**Novelty Risk：High（原始版本）；Medium（按 Idea 5 pivot 后）。**

能够“杀死”原始 idea 的论文包括 *The Devil Is in the Interface*、*The Scaffolding Matters More Than the Interface*、*Permission Denied* 和 framework evaluation。若只做 “tool/interface A vs B 的 success/token comparison”，Idea 1 应直接放弃。可保留的 novelty 是把 interface representation 与 authority 作为两个可分离因素，并在 security-grounded repository execution 中估计 interaction。

### Research Questions

原始 Idea 1 不建议保留独立 RQs。若作为 umbrella，可使用以下四个收敛版 RQs，并将正式论文归入 Idea 5：

- **RQ1 — Effect**：在 underlying capabilities、model 和任务固定时，tool-interface architecture 与 privilege granularity 如何影响 clean repository task success？
- **RQ2 — Security**：在 issue/README/tool metadata 含有 adversarial content 时，两者如何影响 attack success、unauthorized action 和 unsafe side effect？
- **RQ3 — Trade-off**：不同 design point 的 security gain 是否以 measurable success、latency、token 和 cost 代价换取？
- **RQ4 — Mechanism**：action granularity、compound command、observability、denial feedback、authority scope 和 context footprint 哪些 trajectory characteristics 解释这些 effect？

### Experimental Design

建议不为 Idea 1 另建实验。直接复用第 7 节 Idea 5 的 design：先做 Bash/atomic × ambient/scoped 的 minimum viable study，再决定是否加入 MCP 或 multi-agent communication。

### Risks

- 变量空间太宽，容易把一个题目膨胀成 architecture、protocol、security、multi-agent、benchmark 五篇论文。
- “communication”若不定义为 message topology、message schema、delegation 或 provenance，无法形成 treatment。
- 若同时比较现成 framework，model/scaffold/tool 混淆会破坏 causal claim。
- 若将 capability、safety、efficiency 合成一个加权分数，会丢失不同 stake-holder 的 trade-off；应报告 Pareto frontier 和预注册 primary contrasts。

### Verdict

**不作为独立论文推进。** 把它保留为整个研究计划的 motivating umbrella，并将其可执行部分并入 Idea 5。

## 4. Idea 2

### Original Idea

PDF 第 1 页中部的 idea 是：选择 2024–2025 年具有代表性的开源 Coding Agent 系统，对其进行 protocol/security retrofit，在尽量保持任务能力不变的情况下，系统测量协议化通信、权限、来源追踪和工具调用约束能否降低行为安全风险，以及正确率、时间和成本代价。

#### 结构化提取

| 字段 | 解释 |
|---|---|
| Idea 名称 | Security / protocol retrofit for open-source coding agents |
| 原始研究目标 | 在不显著损失能力的情况下，为现有 coding agents 加入 protocol、permission、provenance、tool-call constraints，并测安全/utility/efficiency |
| 研究对象 | 2024–2025 open-source coding-agent systems |
| 软件工程场景 | repository-level issue resolution / code generation；原文未固定 benchmark |
| AI / LLM / Agent 技术 | open-source coding agents、protocolized communication、middleware、sandbox、provenance、tool policies |
| 自变量 | baseline vs retrofit；可能拆为 permission、provenance、tool-call constraint、protocol communication |
| 因变量 | correctness / task success；unsafe action、privilege violation、secret leakage、prompt injection success；time、tokens、cost |
| 实验对象 | 多个 agent architecture、模型、repo task、clean/adversarial issue content |
| 预期贡献 | 经验性回答可迁移的 protocol/security layer 能否 retrofit 到异构 coding agents |
| 模糊点 | retrofit layer 是新系统还是复用机制？各 agent 是否拥有相同 capability？protocol 与 permission 是否分开？“行为安全”如何观测？多个 layer 同时启用会产生什么 confounding？ |

#### 明确化句子

> **We study whether a capability-aware runtime/protocol layer reduces execution-security violations across heterogeneous repository-level coding agents, and how much task utility, latency, and monetary cost it changes under matched clean and adversarial tasks.**

### Related Work

#### Closest Work

| 论文 | 已解决什么 | 尚未解决什么 |
|---|---|---|
| [Towards Engineering Multi-Agent LLMs: A Protocol-Driven Approach](https://arxiv.org/abs/2510.12120) — Zhenyu Mao et al., 2025, arXiv preprint | SEMAP 在 A2A 之上加入 behavioral contracts、structured messaging、lifecycle/verification；在 HumanEval、ProgramDev、Devign/VuDenc 上报告 failure reduction | 不是跨现有 repo-level coding-agent architectures 的 retrofit；权限、provenance、真实 tool side effect、cost 和同一任务下的 utility preservation 仍未隔离 |
| [Defeating Prompt Injections by Design](https://arxiv.org/abs/2503.18813) — Edoardo Debenedetti et al., 2025, arXiv preprint | CaMeL 以 control/data flow 与 capability-based policy 防御间接 prompt injection | 通用 agent benchmark；没有 coding-agent repository workload、跨 architecture comparison、full cost/time accounting |
| [AgentArmor: Enforcing Program Analysis on Agent Runtime Trace to Defend Against Prompt Injection](https://arxiv.org/abs/2508.01249) — Peiran Wang et al., 2025, arXiv preprint | 将 runtime trace 结构化为 program，结合 CFG/DFG/PDG、trust boundary 与类型检查 | 主要评估 AgentDojo/ASB；没有 repository-level code-agent retrofit、architecture heterogeneity 和长期 task utility |
| [The Task Shield](https://aclanthology.org/2025.acl-long.1435/) — Feiran Jia et al., 2025, ACL Long | task-alignment defense 可压低 AgentDojo ASR，并报告 utility | 任务对齐防御不是跨 agent architecture 的协议/权限 retrofit；没有 coding-agent repo outcome 与 cost frontier |
| [Permission Denied](https://arxiv.org/abs/2608.02670) — Davidovich et al., 2026, arXiv preprint | 证明 restrictive policies 会产生 success loss、timeout 和 cost inflation | 主要在 Terminal-Bench 2.1；不是 protocol/provenance retrofit，也没有 tool architecture × authority interaction |
| [SecureVibeBench](https://arxiv.org/abs/2509.22097) — Junkai Chen et al., 2025/ACL 2026, arXiv / ACL Main | 在多文件 C/C++ OSS-Fuzz repositories 上同时测 functionality 与 secure outcome | 是 secure coding benchmark，不回答 policy/protocol retrofit 的原因和代价 |

#### Enabling Work

- [Agent Security Bench](https://luckfort.github.io/ASBench/)（ICLR 2025）提供多场景、400+ tools、攻击/防御与多指标，可借鉴 attack taxonomy；但 coding-agent validity 需另行验证。
- [MCPTox](https://ojs.aaai.org/index.php/AAAI/article/view/40895) / [arXiv:2508.14925](https://arxiv.org/abs/2508.14925)（Wang et al., AAAI 2026）显示 MCP tool poisoning 在 live servers 上可造成高 ASR；可作为 MCP/tool metadata threat 的来源，不应直接当作 repository outcome。
- [IssueTrojanBench](https://arxiv.org/abs/2607.20759)（Singh et al., 2026, arXiv）把攻击放入 coding-agent 的 issue/repository delivery vectors，并覆盖 Cursor、Claude Code、Codex Desktop 等系统；是 Idea 2 的重要 adversarial task source。
- [SEC-bench](https://proceedings.neurips.cc/paper_files/paper/2025/hash/a9168f1c54e5147027f1e8cf83e1a775-Abstract-Conference.html)（Lee et al., NeurIPS 2025）在 isolated environment 中构造、复现和修复 repository vulnerabilities；适合作为安全 outcome / oracle 的基础。

### Research Gap

#### 已知什么？

已有工作显示：

- protocol/contract/verification 可降低部分 coordination failures；
- capability/data-flow/runtime policy 可以降低 indirect prompt injection；
- coding-agent 的 secure outcome 低于 functional outcome；
- 权限收紧会提高 denial、timeout 与 cost。

#### 未知什么？

尚未得到可靠回答的问题是：

1. 同一个可解释的 policy/provenance layer 是否能跨 SWE-agent、OpenHands 和另一种 coding-agent scaffold 稳定工作？
2. security gain 是否来自真正阻止了 unsafe execution，还是仅仅让 agent 更早失败？
3. 哪些风险是 protocol-solvable（例如 tool capability violation、untrusted data flow），哪些是 protocol-insufficient（例如错误的 patch、semantic vulnerability、模型自己提出的危险命令）？
4. retrofit 的 utility/time/token/cost 代价是否在不同 architecture、task difficulty 和 threat class 下发生反转？

#### Gap 是否值得研究？

**经过收敛后值得。** 原始“加 middleware 并测 ASR”不够新，因为 CaMeL、AgentArmor、Task Shield 已经证明 generic runtime defense 的可行性。真正的 SE empirical contribution 是 cross-architecture、repo-level、execution-grounded、capability-matched 的 failure taxonomy 与 cost/utility characterization。

### Novelty Analysis

**Novelty Risk：High（原始版本）；Medium–High（合并并收窄后）。**

可杀死原始版本的事实：generic agent runtime defense 已存在；SEMAP 已研究 protocol-driven coordination；Permission Denied 已研究 policy cost。可保留的 new knowledge 是“retrofit portability 和 failure-class boundary”，而不是“我们实现了一个新的安全协议”。

### Research Questions

建议将 Idea 2 与 Idea 4 合并为以下四个 RQs：

- **RQ1 — Baseline failure map**：在 clean 与 adversarial repository tasks 中，异构 coding agents 产生哪些 execution-security failure classes，其频率和 architecture dependence 如何？
- **RQ2 — Retrofit effect**：capability-aware permission + provenance-aware runtime layer 对每类 failure 的 violation rate、attack success 和 false-denial rate 有何影响？
- **RQ3 — Utility/efficiency trade-off**：retrofit 对 task success、tests、regressions、wall-clock、tokens、tool calls、retry 和 cost 的影响是否稳定？
- **RQ4 — Generalization and sufficiency**：哪些 mitigation 能跨 model、agent architecture、task family 和 threat delivery vector 泛化；哪些风险仍然需要 model/scaffold/task-level intervention？

Multi-agent cross-agent propagation 不放进 MVP；若要保留，应成为 RQ4 的 extension，并使用 provenance lineage、propagation depth、affected agents 和 downstream unsafe action 作为预先定义的 outcome。

### Experimental Design

#### Independent Variables

- Agent architecture：至少两个公开 coding-agent harness，加一个固定的 minimal ReAct baseline；不要同时改变 model 和 scaffold。
- Policy condition：no policy、audit-only、enforcement；enforcement 再拆 scoped capability 与 provenance/data-flow checks。
- Threat condition：clean issue/repository、prompt injection、tool poisoning 或 issue-trojan；一次只引入一种 threat。
- Task/repository difficulty：作为 block 或 random effect，而不是 treatment。

#### Dependent Variables

- Utility：issue resolved、tests pass、patch correctness、regression、secure-and-correct success。
- Security：attack success、unsafe tool call、unauthorized file/network/process operation、privilege violation、canary/secret access、policy violation、false denial。
- Efficiency：wall-clock、LLM requests、input/output tokens、tool calls、messages、retries、monetary cost。
- Explanation：denial/retry count、trajectory length、provenance edges、policy-check latency、delegation depth（若开启 multi-agent extension）。

#### Controls

固定 model version、system prompt、task prompt、temperature、max steps、timeout、retry budget、container image、network mode、repository commit、test command、tool capability set、logging format、cost price sheet 和 date-frozen API endpoint。所有 agent 必须面对同一 task seed；task order、rollout seed 和 agent order 随机化。

#### Benchmark / Models / Baselines

- MVP：12–24 个 SWE-bench Verified repository tasks，加 12–24 个经过 isolated validation 的 adversarial paired variants。
- 扩展：IssueTrojanBench 的 coding-agent attack tasks；SEC-bench 或 SecureVibeBench 的 security-sensitive repositories。
- MVP 可先用一个 frozen open-source coding model；正式研究至少加入一个 frontier/API model 和一个 open model，避免把 effect 误认为单模型特性。
- Baselines：unmodified agent、prompt-only defense、audit-only runtime、scoped runtime；不把一个全新的 agent framework 当作 baseline。

### Empirical Study and FSE Contribution Test

| Test | 评价 |
|---|---|
| C1 Empirical Finding | 若 failure-class × architecture interaction 与既有 generic-agent 结论不同，能够形成新发现 |
| C2 Systematic Evaluation | 需要 paired repository tasks、multiple rollouts、pre-registered primary contrasts 和 mixed-effects analysis |
| C3 Explanation | 用 execution trace、policy denial、provenance edge 和 trajectory 分析解释“为何 retrofit 成功/失败” |
| C4 Practical Implication | 为 coding-agent developers 指出哪些 control 值得放在 runtime，哪些不能替代 secure coding / review |
| C5 Reproducibility | 容器、policy、prompts、task commit、logs、canary、evaluation scripts 和成本价格表可公开 |

### Risks

- retrofit layer 若同时更改 tool schema、prompt 和 sandbox，将无法知道 effect 来自哪一层。
- policy 让 agent 不能完成任务时，不能把“没有攻击”简单记为 security success；必须区分 safe success、safe failure、unsafe success、unsafe failure 和 false denial。
- open-source coding-agent 项目 API 变化快；必须 pin commit、container 和 model endpoint。
- multi-agent propagation 会使单位分析变复杂；没有足够 budget 时不要加入。

### Verdict

**推荐作为第二方向，但以 Idea 2 + Idea 4 的合并版推进。** 主贡献应是 protocol/permission retrofit 的 cross-architecture empirical boundary，而不是新协议实现。若第一轮实验发现所有 policy failure 都可以被一个简单 deny-list 消除，研究价值会下降；应立即转向“semantic / protocol-insufficient” failure taxonomy。

## 5. Idea 3

### Original Idea

PDF 第 1–2 页将其定义为 coding agents 的 capability–safety–efficiency empirical study：

- RQ1：communication/tool-integration mechanisms 对 repository-level SWE tasks 的 effectiveness 影响；
- RQ2：benign/adversarial conditions 下的 unsafe tool call、unauthorized action、over-privileged action、sensitive resource access、ASR、policy violation；
- RQ3：wall-clock、tokens、LLM requests、tool calls、messages、retries、cost；
- RQ4：何时 sophisticated interaction 值得增加 security/computation cost；
- RQ5：trajectory length、tool calls、communication turns、retries、privilege escalation、delegation depth 等是否解释差异。

#### 结构化提取

| 字段 | 解释 |
|---|---|
| Idea 名称 | Capability–safety–efficiency trade-off in coding agents |
| 原始目标 | 把 task capability、安全行为、资源效率放在同一 empirical study，并解释 trade-off |
| 研究对象 | repository-level coding agents，可能包含单 agent / multi-agent |
| 技术 | communication framework、tool integration、delegation、planning、memory、security policy |
| 自变量 | mechanism、architecture、number of agents、tool access、privilege、memory、planning |
| 因变量 | success/test/regression；security violations/ASR；time/tokens/requests/cost |
| 实验对象 | 多模型、多框架、多 repo task、clean/adversarial execution |
| 预期贡献 | 发现 trade-off frontier 和 trajectory mechanism |
| 模糊点 | treatment 数量过多；“capability”与“utility”未区分；security oracle、unit of analysis、model/scaffold controls 不明确 |

#### 明确化句子

> **We study whether a specified interaction mechanism or authority policy changes the joint distribution of repository-task success, execution-security violations, and resource cost, and whether observed trajectory features mediate that change under a fixed model and tool capability set.**

### Related Work

#### Closest Work

| 论文 | 主要结论 | 对 Idea 3 的 collision |
|---|---|---|
| [A Comprehensive Empirical Evaluation of Agent Frameworks](https://arxiv.org/abs/2511.00872) — Yin et al., 2025 | 已做 framework-level code-centric effectiveness / efficiency comparison，并观察 long trajectory、reflection、token overhead | 原始 Idea 3 的 broad comparison 已很接近，但 security/causal control 不足 |
| [SWE-Effi](https://arxiv.org/abs/2509.09853) — Fan et al., 2025 | 研究 resource efficiency、token snowball、token/time trade-off | RQ3 已有相邻研究；需增加 execution security 和 intervention |
| [Understanding Code Agent Behaviour](https://arxiv.org/abs/2511.00197) — Majgaonkar et al., 2025 | 分析 OpenHands/SWE-agent/Prometheus trajectories，失败轨迹更长、variance 更大，file localization 在失败时仍可能较高 | 已覆盖 descriptive success/failure trajectory；不能再只做 trajectory correlation |
| [SWE-Search](https://proceedings.iclr.cc/paper_files/paper/2025/hash/a1e6783e4d739196cad3336f12d402bf-Abstract-Conference.html) — Antoniades et al., ICLR 2025 | multi-agent MCTS/self-improvement 提升 SWE-bench，且随 inference-time compute 增加 | 说明 capability/compute trade-off 已被算法论文部分覆盖 |
| [CooperBench](https://arxiv.org/abs/2601.13295) — Arpandeep Khatua et al., 2026 | 多 agent 协作 coding tasks 平均比单 agent 低约 30% success，暴露 communication jam、commitment deviation | communication effect 有最新 collision，但尚未联合 execution authority/security |
| [The Devil Is in the Interface](https://arxiv.org/abs/2608.11386) — 2026 | interface architecture 改变 consistency、exploration、tokens | tool-interface treatment 已被直接研究 |

### Research Gap

#### 已知什么？

当前已有大量“成功率 + token/time + trajectory”评价，也有 communication 和 tool-interface 的局部研究。security benchmarks 进一步证明 functional success 不能代表 secure behavior。

#### 未知什么？

如果把研究设计收窄到一个 treatment，例如 tool architecture × privilege policy，并记录 causal trajectory consequences，那么仍可回答：

- security gain 是否通过 denial/retry/trajectory length 传递到 cost；
- 同一 architecture 在 weak/strong model 上是否产生不同的 frontier；
- 某些 trajectory feature 是 mediator，还是 task difficulty 的结果；
- capability–safety frontier 是否在不同 threat class 下发生变化。

#### Gap 是否足以支撑独立 FSE？

**原始版本不够。** 它是一个 measurement agenda，与 Ideas 1/5 重叠，且有 framework-evaluation collision。**作为 Idea 5 的 mechanism / trade-off module 足够。**

### Novelty Analysis

**Novelty Risk：High（独立版本）；Medium–High（作为 Idea 5 子研究）。**

“同时测 correctness、security、time、cost”本身不是 gap。只有在预先指定 treatment、paired tasks、execution-grounded security 和 mechanism analysis 后，才可构成 empirical contribution。

### Research Questions

不建议再单独提交四个 RQs。并入 Idea 5 后，保留：

- **Trade-off RQ**：policy/interface design point 的 security gain 是否伴随可量化的 utility、latency、token、retry 和 cost change？
- **Mechanism RQ**：compound actions、denied-action feedback、trajectory length、tool-call count、exploration diversity、retry 和 privilege escalation 是否解释 observed effect？

### Experimental Design

使用 Idea 5 的 2 × 2 factorial design，并将 trajectory features 作为预注册的 secondary mediators；不要将 trajectory feature 当成 treatment，也不要在 outcome 之后挑选“最能解释结果”的变量。若需要 mediation，只报告符合时间顺序且有明确 causal assumptions 的 exploratory analysis。

### Risks

- 高维 metrics 很容易产生 p-hacking；预先定义 primary outcome 和 primary contrasts。
- 同一个 agent 的多次 rollout 不是独立样本；task/repository 应是 block/random effect，rollout 是重复测量。
- LLM judge 不能作为唯一 security oracle；必须用 tests、OS audit、canary、policy logs 和 static/dynamic security checks。

### Verdict

**不独立推进；并入 Idea 5。** 它为 Idea 5 提供 RQ3/RQ4 和 explanatory layer，但不能以 broad trade-off study 单独作为 novelty。

## 6. Idea 4

### Original Idea

PDF 第 3–4 页将其命名为：

> “跨 Coding-Agent Architecture 的 Protocol-Level Security Retrofit 实证研究。”

原始 RQs 包括：baseline behavioral security failures、reusable protocol-level security layer 的 effectiveness、utility preservation、efficiency cost、跨 architecture generalization、protocol-solvable vs protocol-insufficient taxonomy，以及 multi-agent malicious/faulty information propagation。

#### 结构化提取

| 字段 | 解释 |
|---|---|
| Idea 名称 | Cross-architecture protocol-level security retrofit |
| 原始目标 | 在 heterogeneous coding-agent architectures 上加入 reusable protocol-level security layer |
| 研究对象 | 多种 coding-agent architecture，进一步包含 multi-agent system |
| SE 场景 | repository workloads、tool execution、可能的 multi-agent coding |
| 技术 | access-control middleware、sandbox、protocol、provenance、capability boundary、cross-agent communication |
| 自变量 | architecture、security layer、attack class、communication/provenance policy |
| 因变量 | violation、ASR、utility loss、latency、tokens、cost、propagation depth |
| 实验对象 | heterogeneous agents、repo tasks、malicious/faulty messages |
| 预期贡献 | protocol-solvable / protocol-insufficient risk taxonomy，以及 retrofit generalization |
| 模糊点 | protocol layer 具体定义不清；security middleware 是否需要 agent-specific adapter；multi-agent propagation 与单-agent retrofit 是两个独立论文问题 |

#### 明确化句子

> **We study whether the same capability-aware and provenance-aware runtime policy can reduce execution-security violations across heterogeneous repository-level coding-agent architectures without disproportionate losses in task utility and efficiency.**

### Related Work

#### Closest Work

| 论文 | 已解决什么 | 对 Idea 4 的 collision / remaining gap |
|---|---|---|
| [SEMAP](https://arxiv.org/abs/2510.12120) — Mao et al., 2025 | protocol-driven behavioral contracts、structured messages、verification 可降低 multi-agent development/vulnerability failures | 直接削弱“protocol coordination 是新颖性”的版本；仍未覆盖跨现有 repo-level coding-agent 的 security retrofit |
| [CaMeL](https://arxiv.org/abs/2503.18813) — Debenedetti et al., 2025 | capability-based information-flow control 设计了 prompt injection defense | 直接削弱“新 runtime protocol 能防 injection”的版本；仍缺 coding-agent cross-architecture empirical scope |
| [AgentArmor](https://arxiv.org/abs/2508.01249) — Wang et al., 2025 | runtime trace program analysis、trust boundary、policy enforcement；在 AgentDojo/ASB 测 ASR/utility | 直接覆盖 runtime-level security enforcement；可将 research gap 转移为 portability、repo validity、cost 和 protocol-insufficient taxonomy |
| [The Task Shield](https://aclanthology.org/2025.acl-long.1435/) — Jia et al., ACL 2025 | task alignment 防御可降低 injection ASR | 说明 prompt/task-level defense 也必须纳入 baseline，否则 retrofit comparison 不完整 |
| [Permission Denied](https://arxiv.org/abs/2608.02670) — Davidovich et al., 2026 | hardened permission policies 影响 success、timeout、cost | 已覆盖 authority hardening 的 utility cost；仍没有 protocol × architecture 因果分解 |
| [AgentDojo](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html) / [ASB](https://luckfort.github.io/ASBench/) | 提供通用 agent security testbed | 不是 coding-agent repository workload；不能直接证明 retrofit 对 SE tasks 的外部效度 |

### Research Gap

最可信的 gap 不是“没人做 protocol security”，而是：

1. generic defense 是否能跨真实 coding-agent architecture 迁移；
2. policy denial 是否真正阻止 unsafe side effect，同时保留 patch utility；
3. threat class 是否决定 protocol 的有效边界；
4. retrofit 的 cost/latency 是否被现有 security studies 系统记录；
5. security layer 是否需要 architecture-specific adapter，因而所谓“reusable”并不成立。

这是真实但窄的 gap；若增加 multi-agent propagation，会变成第二个研究项目。

### Novelty Analysis

**Novelty Risk：Very High（独立原始版本）；Medium–High（合并 Idea 2 后）。**

“跨架构 + protocol layer + security”已有多个高度相邻的组成部分。若论文只展示一个 layer 在 2–3 个 agent 上把 ASR 降低，应当被现有 runtime-defense 工作击中。只有在预先定义 protocol-solvable / protocol-insufficient taxonomy、execution-grounded oracle 和 utility-preserving paired evaluation 时才有新贡献。

### Research Questions

不要把原始六个 RQ 全部保留。将 RQ1–RQ5 合并为 Idea 2 的四个 RQs；原始 RQ6 multi-agent propagation 仅作为 future work。这样可保留关键科学问题并避免 scope explosion。

### Experimental Design

复用 Idea 2。特别注意：

- 至少报告 no-control、audit-only、enforcement 三个条件；
- 每一种 attack class 都要有 benign counterpart，以测 false denial；
- policy layer 的 interface adapter 代码固定，禁止每个 agent 手工“调到最好”；
- security event 以 OS-level / tool-level execution log 为准，不能只用 LLM judge。

### Risks

- “architecture”与“implementation quality”难分，必须 capability-match、固定 planner/model 或使用同一 core loop。
- “protocol-insufficient”不能凭研究者主观标注；先定义 taxonomy，再由两名独立 annotators 根据 trace 和 execution evidence 标注，报告 agreement。
- cross-agent propagation 的信息流、权限、message provenance 与单 agent 需要不同的实验单位。

### Verdict

**This idea should probably be dropped as a standalone paper.** 合并为 Idea 2 的 security-retrofit / generalization section；删除 MVP 中的 multi-agent propagation。若第一阶段证明单 agent 的 protocol-solvable taxonomy 稳定，再另起一篇 multi-agent study。

## 7. Idea 5

### Original Idea

PDF 第 5–7 页的核心题目是：

> “How does tool architecture—and separately, privilege granularity—causally affect the security–utility–efficiency frontier of repository-level coding agents?”

原始 RQs 已明确区分 interface representation 与 authority：

- RQ1：在 underlying capabilities held constant 时，tool architecture 对 clean repository success、tests、patch correctness、consistency 的影响；
- RQ2：adversarial repo/issue content 下的 ASR、unsafe side effects、unauthorized file/network/process operations、persistence、fake credential access；
- RQ3：factorial design，例如 Bash / Atomic Tools / CodeAct / MCP × Full/Ambient / Scoped/Least-Privilege；
- RQ4：security–utility–efficiency trade-off；
- RQ5：ambient authority、action granularity、compound command、observability、reversibility、error feedback、context footprint、schema verbosity、instruction/data separation、least-privilege expressiveness 等 mechanism。

#### 结构化提取

| 字段 | 解释 |
|---|---|
| Idea 名称 | Causal effect of tool architecture and privilege granularity on coding-agent frontier |
| 原始目标 | 将 interface representation 与 authority granularity 分离，并共同解释 utility、security、efficiency |
| 研究对象 | repository-level coding agents |
| SE 场景 | issue resolution、patch generation、test/build/debug、可能的 secure code task |
| AI / LLM / Agent 技术 | Bash/atomic/CodeAct/MCP tool interface、sandbox、least privilege、LLM coding agent |
| 自变量 | tool architecture；privilege granularity；clean vs adversarial condition；可能 model、task difficulty |
| 因变量 | task success、tests、patch correctness、consistency；ASR、unsafe side effect、unauthorized operation；time、tokens、tool calls、cost |
| 可能实验对象 | 一个固定 agent loop + 多种 capability-matched tool surfaces；必要时两个模型 |
| 预期贡献 | interface × authority interaction、security–utility–efficiency Pareto frontier、mechanism explanation |
| 模糊点 | MCP 是否真正是 architecture 还是 transport/protocol；如何保证 tool capability equivalence；如何构造 adversarial repo pair；security event 和 success 的优先级需预注册 |

#### 明确化句子

> **We study whether and how capability-matched tool-interface architectures and privilege granularity causally affect task utility, execution security, and resource efficiency of repository-level coding agents, and whether their effects interact under clean versus adversarial repository conditions.**

### Related Work

#### Closest Work

| 论文 | 它研究了什么 | 已解决什么 | 它还没有解决什么 |
|---|---|---|---|
| [The Devil Is in the Interface](https://arxiv.org/abs/2608.11386) — Xiangzhe Xu et al., 2026, arXiv preprint | 六种 tool architectures、3 个 actors、SWE-bench Live 等任务；测 resolve、pass^k、exploration、tokens/steps | 已经是 tool architecture 对 coding-agent behavior 的最直接 collision；揭示 Atomic、NLSearch、Python 等差异 | 没有 privilege factor、adversarial repo execution、unauthorized side effects、security–utility frontier；文中也承认 mechanism causal link 未直接验证 |
| [The Scaffolding Matters More Than the Interface](https://arxiv.org/abs/2608.08654) — Forment et al., 2026, arXiv preprint | 固定一个 private git task，比较 scaffolding 及 MCP/CLI，报告完成率/成本差异 | 证明不能把 visible interface 当成全部 causal story | 单一任务、scaffold confounding、无 execution security 和 authority-granularity factorial |
| [Permission Denied](https://arxiv.org/abs/2608.02670) — Davidovich et al., 2026, arXiv preprint | Terminal-Bench 2.1 上 nested security policy、scoped credentials、restricted egress、read-only FS、non-root | 已测 privilege/policy 对 success、timeouts、cost 的影响 | 没有把 tool representation 与 privilege 分开；不是 repository coding task 下的 paired interface × authority study |
| [SecureVibeBench](https://arxiv.org/abs/2509.22097) — Junkai Chen et al., ACL 2026 Main / arXiv | 105 个 C/C++ OSS-Fuzz tasks，测 functional 与 secure correctness | 提供 repository-level secure outcome 和 static/dynamic oracles | 不操纵 tool architecture / privilege；不解释 security frontier 的 causal mechanism |
| [IssueTrojanBench](https://arxiv.org/abs/2607.20759) — Ankur Singh et al., 2026, arXiv preprint | coding-agent issue/repository delivery vector 的多类 Trojan/poisoning attacks | 提供现代 coding-agent 的 adversarial task setting | 不是 tool architecture × authority causal comparison |
| [SWE-agent](https://arxiv.org/abs/2405.15793) — John Yang et al., 2024 | 证明 agent-computer interface 能 enable automated SE | 提供 interface study 的基础 agent design | 不涉及 privilege/security trade-off |

#### Enabling Work

- [OpenHands](https://arxiv.org/abs/2407.16741) 提供可运行的 open agent platform、sandbox 和 evaluation interface。
- [GitTaskBench](https://arxiv.org/abs/2508.18993)、[SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) 与 [SWE-EVO](https://arxiv.org/abs/2512.18470) 提供不同难度/时间跨度的 repository tasks；应根据研究问题而不是机械混用。
- [SEC-bench](https://proceedings.neurips.cc/paper_files/paper/2025/hash/a9168f1c54e5147027f1e8cf83e1a775-Abstract-Conference.html) 与 [SecureVibeBench](https://arxiv.org/abs/2509.22097) 提供 secure-code evaluation oracle；它们是 security outcome source，不是 architecture treatment。
- [AgentDojo](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html)、[MCPTox](https://arxiv.org/abs/2508.14925) 和 [IssueTrojanBench](https://arxiv.org/abs/2607.20759) 提供不同 delivery vectors；必须单独建 threat blocks。

### Research Gap

#### 已知什么？

目前已有三个相互分离的事实：

1. tool architecture 会改变 agent 的 exploration、consistency 和 resource use；
2. restrictive policy 会改变 success、timeout 和 monetary cost；
3. coding-agent 在 adversarial / secure-code tasks 上会产生真实 security failures。

#### 未知什么？

在本次检索边界内未定位到一项将以下五点放在同一 controlled empirical study 中的工作：

- tool representation 与 privilege granularity 被独立随机化；
- underlying operations、model、task prompt、timeout、retry 和 scaffold capability-matched；
- clean 与 adversarial repository conditions 成对；
- security 由实际 execution / audit event 定义，而非单纯 judge score；
- utility、security、efficiency 用共同实验单位和统计模型分析，并报告 interaction / Pareto frontier。

这不是“没人比较 A 与 B”的弱 gap。它解决的是实际工程中一个重要的 attribution problem：当 coding agent 失败或执行危险动作时，开发者无法知道应该换接口、收紧权限、改 scaffold，还是更换模型。错误归因会导致不必要的成本，或安全边界被错误地交给 prompt。

#### 为什么不知道？

原因是已有论文通常只变化一个维度，或者把以下因素 bundled：tool schema、execution environment、scaffold、model、prompt、policy。安全 benchmark 又往往将 agent interface 固定为实验基础设施。因而 utility effect 和 security effect 尚未被同一 design 分解。

#### Gap 是否值得 FSE？

**是，但只有 pivot 后成立。** 原始题目必须明确：

- architecture 的操作性定义；
- authority 的 capability matrix；
- primary security estimand；
- clean/adversarial task construction；
- capability-matching audit；
- mechanism analysis 的因果边界。

### Novelty Analysis

**Novelty Risk：Medium（原始版本 High）。**

#### 能够杀死该 idea 的论文

- *The Devil Is in the Interface* 杀死“接口 architecture 单独影响 performance”的简单版本。
- *The Scaffolding Matters More Than the Interface* 杀死“MCP vs CLI 单一任务成本比较”的版本。
- *Permission Denied* 杀死“policy hardening 会牺牲 success/cost”这一单独 claim。
- *SecureVibeBench* / *SEC-bench* 杀死“首次在 repo-level secure coding task 上测 safety”的版本。
- *IssueTrojanBench* 杀死“首次把 issue/repo content 作为 coding-agent attack delivery vector”的版本。

#### 仍然新的精确部分

没有发现一项已验证工作同时回答“interface representation × privilege granularity interaction + repo execution security + utility/cost frontier”。因此可保留的 novelty 是 causal factor separation 和 actionable design boundary，而不是新 benchmark 或新 agent framework。

### Research Questions

- **RQ1 — Utility effect**：在 underlying operations、model、prompt 和 task 固定时，tool architecture 与 privilege granularity 如何影响 clean repository task success、test pass、patch correctness 和 repeated-run consistency？
- **RQ2 — Security effect**：在 issue、README、repository file 或 tool metadata 含有 adversarial content 时，两者如何影响 prompt-injection success、unsafe tool call、unauthorized file/network/process operation、persistence 和 canary/credential access？
- **RQ3 — Interaction and trade-off**：tool architecture 与 privilege granularity 是否存在 interaction？哪些 design points 位于 security–utility–efficiency Pareto frontier？
- **RQ4 — Mechanism**：action granularity、compound command、observability、reversibility、denial feedback、context footprint、schema verbosity、exploration diversity 和 retry/trajectory characteristics 哪些解释 observed differences？

所有 RQs 均可由 empirical experiment 回答；RQ4 应标为 mechanism/explanatory，不能把相关性写成强因果结论，除非 design 另有 intervention。

### Experimental Design

#### Core treatment

最小可行的正式 treatment 是 2 × 2：

| Factor | Level A | Level B |
|---|---|---|
| Tool-interface architecture | compound shell / Bash-like interface | capability-matched atomic tools |
| Privilege granularity | ambient/full authority within sandbox | scoped/least-privilege capabilities |

扩展条件可加入 MCP，但只有在 MCP server 与 atomic/Bash operation set capability-equivalent、schema footprint 可记录、transport overhead 可控制时才加入。不要把 MCP 直接当作一个“安全架构” treatment。

#### Independent Variables

- architecture：Bash/compound、atomic；full study 可再加入 MCP or structured CodeAct；
- privilege：ambient vs scoped capability matrix；
- condition：clean vs adversarial paired task；
- block：repo、task type、difficulty、model；
- rollout：固定 seed set，作为 repeated measure 而非独立 population。

#### Capability-matching requirements

每一种 interface 都必须声明并自动检查相同的 primitive operations：read file、write file、search、run tests、run build、inspect git、network（默认 deny）、process execution。记录：

- 操作是否能读取/写入哪些 path；
- 是否能执行 shell compound command；
- 是否能访问 network；
- 结果是否有 provenance tag；
- error/denial feedback 的文本和长度；
- tool schema/context token footprint；
- action reversibility 和 audit coverage。

如果 capability 不等价，论文只能声称“system configuration comparison”，不能声称“architecture causal effect”。

#### Dependent Variables

**Utility**

- issue resolved / patch accepted；
- test pass rate、regression rate、build status；
- patch correctness / secure-and-correct success；
- repeated-run consistency / pass^k。

**Security / reliability**

- attack success rate；
- unsafe action rate；
- unauthorized read/write/network/process operation；
- privilege violation；
- sensitive canary/credential access；
- persistence / malicious side effect；
- safe completion、safe refusal、false denial、unsafe completion、unsafe failure 五类 joint outcome。

**Efficiency**

- wall-clock time；
- total / input / output tokens；
- LLM requests；
- tool calls、turns、denials、retries；
- monetary cost，使用 frozen provider price sheet。

#### Control Variables

固定 model snapshot、temperature、system prompt、task prompt、repository commit、container image、OS user、network mode、tool primitive set、timeout、max steps、retry budget、test command、random seed set、API price、logging version 和 evaluation script commit。

#### Benchmark selection

- **Clean utility**：SWE-bench Verified 的 24–40 个具有稳定 test harness 的 tasks；先按 repository、language、difficulty 分层抽样。
- **Adversarial security**：IssueTrojanBench 的相应 task family，或在同一 repository/task 的 frozen copy 中注入经过 red-team validation 的 untrusted issue/README/file content。
- **Secure-code extension**：SecureVibeBench / SEC-bench，用于 vulnerability-introduction / secure patch outcome；不与 clean patch resolution 混为同一 primary estimand。
- **Long-horizon extension**：SWE-EVO 只在 pilot 已证明 interface × privilege effect 后加入；不要在 MVP 同时引入 long-horizon、multi-agent 和 MCP。

#### Models / agents

- MVP：一个 frozen open model + 一个固定 agent loop；目的是确认 treatment 是否可观测。
- Full study：一个 frontier/API coding model 与一个 open coding model，使用同一 tool adapter 和 prompt template；model 是 block/random effect，不是主 treatment。
- 不同时比较 5 个 frameworks；若需要外部效度，在主实验后把 2 个 open harness 作为第二阶段 block。

#### Randomization and replication

- task/repository 分层后随机分配 treatment order；
- 每个 task × treatment × model 至少 3–5 个 independent rollouts；
- 记录 API seed、temperature、model version 和 exact prompt；
- 每个 task 的 adversarial variant 与 clean variant 成对，防止 task difficulty 被误当作 attack effect；
- 以 task/repository 为主要重复单位，rollout 为 within-task repeated observation。

#### Statistical Analysis

- binary utility/security outcome：mixed-effects logistic regression，固定 effects 包括 architecture、privilege、condition 及其 interaction，task/repository/model 作为 random intercept；
- count outcome（tool calls、denials、retries）：negative-binomial mixed model 或 permutation/paired bootstrap；
- time、tokens、cost：log transform 后使用 hierarchical model 或 mixed-effects regression；若 zero-inflated，则明确 model choice；
- 每个 primary contrast 报告 odds ratio / risk difference、95% CI 和 practical threshold；
- secondary metrics 使用 Benjamini–Hochberg 或 Holm correction；
- 不用 observed power 证明结果；在实验前做 simulation-based sample-size / detectable-effect planning；
- 不把 multiple rollout 当作独立样本；使用 cluster bootstrap 或 hierarchical uncertainty；
- Pareto frontier 作为 descriptive multi-objective view，不用任意 weighted sum 代替 security/utility 的单独结果。

### FSE Contribution Test

| Contribution | 能否实现 | 需要的证据 |
|---|---|---|
| C1 Empirical Finding | **能** | architecture × privilege interaction，或 security effect 与 utility cost 的非直观反转 |
| C2 Systematic Evaluation | **能** | capability matrix、paired task、multiple rollout、预注册 stats、不同 threat blocks |
| C3 Explanation | **能但要求高** | instrumented tool/OS trace、denial/retry、context footprint、trajectory analysis；不要只看 success correlation |
| C4 Practical Implication | **强** | 可告诉 tool designers 何时收紧 authority，何时更换 representation，何时必须依赖 model/task-level defense |
| C5 Reproducibility | **能** | containers、task commits、prompts、tool adapter、policy files、logs、oracles、analysis notebook、price sheet |

### Threats to Validity

**Internal validity**

- architecture 与 capability set 不等价；解决：自动 capability manifest + differential test suite。
- privilege policy 可能改变 context/error feedback；这是 treatment 组成部分，但需单独记录并在 mechanism analysis 中说明。
- model/API 更新、temperature、retry 和 hidden provider behavior；解决：pin version、cache、record request/response metadata。
- adversarial variants 可能比 clean tasks 更难；解决：paired construction、独立 difficulty annotation 和 benign semantic-preserving controls。

**External validity**

- SWE-bench 不能代表所有 SE tasks；扩展到 multi-language、long-horizon、secure-code benchmark，但不能在 MVP 过度扩张。
- 一个 model 或 scaffold 的结果不能外推全部 coding agents；至少加入一个 open 与一个 frontier model，并谨慎写 claim。
- 2026 年工具和 model 变化快；发布 dated snapshot 和 replication instructions。

**Construct validity**

- pass@k / resolved rate 不能等同于 software quality；同时报告 regression、test adequacy、patch review 或 secure outcome。
- “security”不能只用 judge；以 OS audit、canary、policy event、static/dynamic oracle 为主。
- “cost”必须包含 LLM token cost、tool runtime、retry 和 wall-clock 的定义，报告 price snapshot。
- “privilege granularity”必须由 capability graph / path/network/process policy 定义，而不是模糊的 safe/unsafe label。

**Conclusion validity**

- 多指标与多条件会产生 multiplicity；预注册 primary outcomes 和 contrasts。
- 随机性、clustered task 和 repeated rollout 需要 hierarchical analysis。
- 极少攻击事件时，报告 exact CI、Bayesian/hierarchical estimate 或 randomization test，不强行使用 asymptotic t-test。
- LLM-as-judge 只作为辅助，并报告 judge agreement / calibration。

### Verdict

**最推荐。** 原始 Idea 5 的 interface-only 版本已被 2026 tool-architecture work 部分击中；但加入 privilege granularity、adversarial repository、execution-grounded security、capability matching、factorial interaction 和 cost frontier 后，仍有清晰、可完成、可复现的 FSE-style empirical study。

## 8. Cross-Idea Comparison

评分定义：1–5；“Cost”列的 5 表示成本低、4 表示可控，1 表示很高。分数是按本文建议的最小 pivot 后评估；原始版本的 novelty risk 另外列出。

| Idea | Novelty | Gap | SE Relevance | FSE Fit | Empirical Value | Feasibility | Dataset | Reproducibility | Cost | Security Value | Publication Potential | Total / 55 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Idea 1（umbrella，按 Idea 5 收敛） | 2 | 2 | 5 | 3 | 4 | 2 | 4 | 3 | 2 | 4 | 3 | **34** |
| Idea 2（retrofit，合并 Idea 4） | 3 | 4 | 5 | 5 | 5 | 3 | 4 | 3 | 2 | 5 | 4 | **43** |
| Idea 3（trade-off，作为 Idea 5 module） | 3 | 3 | 5 | 4 | 4 | 3 | 4 | 3 | 3 | 3 | 4 | **39** |
| Idea 4（standalone，建议放弃） | 1 | 2 | 5 | 4 | 4 | 2 | 3 | 2 | 1 | 5 | 2 | **31** |
| Idea 5（interface × authority） | 4 | 5 | 5 | 5 | 5 | 4 | 4 | 4 | 3 | 5 | 5 | **49** |

### 横向判断

- **Novelty**：Idea 5 pivot 后最高；Idea 2 只有在从“新防御系统”转为“迁移性与边界实证”后才变强。
- **Research gap**：Idea 5 的 causal attribution gap 最明确；Idea 2 的 portability gap 真实但更容易被现有 defense 工作碰撞。
- **SE relevance**：Ideas 2/4/5 都高；Idea 1/3 若不绑定 repository execution，容易变成通用 agent paper。
- **Feasibility**：Idea 5 的 2 × 2 MVP 可控；Idea 4 的 multi-agent propagation 会显著增加实现与统计难度。
- **Cost**：所有涉及多模型、多 agent、多 threat、多 rollout 的版本都昂贵；应先做 single-model pilot 和 stage gate。
- **Security value**：Idea 2/4/5 高，但只有 Idea 5 将 security 与 interface/authority attribution 结合。

## 9. Final Ranking

### Rank #1 — Idea 5：Interface × Authority Causal Study

推荐推进。第一阶段只做 2 × 2、一个 frozen model、12 clean + 12 adversarial paired tasks、3 rollouts；若 primary effect 可见，再扩展 model / architecture / MCP。

### Rank #2 — Idea 2 + Idea 4：Cross-Architecture Security Retrofit

推荐作为第二路线或 Idea 5 的 follow-up。先聚焦 single-agent runtime policy 与 protocol-solvable taxonomy；multi-agent propagation 延后。

### Rank #3 — Idea 3：Trade-off and Trajectory Module

保留为 Idea 5 的 RQ3/RQ4。不要单独做 “capability–safety–efficiency survey/benchmark”。

### Rank #4 — Idea 1：Umbrella Question

作为研究计划的 motivation 可以保留；作为论文标题和实验设计不够具体。

### Rank #5 — Idea 4：Standalone Protocol Retrofit

**This idea should probably be dropped as a standalone paper.** 已有 SEMAP、CaMeL、AgentArmor、Task Shield 和 Permission Denied 覆盖其关键组成；独立推进会重复、过宽且难以解释结果。

## 10. Recommended Idea #1

### Full Proposal

#### Working Title Candidates

1. **Interface × Authority: Causal Effects on the Security–Utility–Efficiency Frontier of Repository-Level Coding Agents**
2. **From Ambient Authority to Scoped Tools: A Controlled Study of Secure Coding-Agent Execution**
3. **When Tool Interfaces and Permissions Interact: An Empirical Study of Repository-Level Coding Agents**

#### Problem Statement

Repository-level coding agents既可能完成真实 issue，也可能在读取 untrusted issue/README/tool output 后执行危险操作。开发者通常同时改变 agent interface、sandbox、permission 和 scaffold，因此出现一个 attribution problem：成功率、攻击面和成本的变化究竟来自哪个设计因素？现有研究分别研究 tool architecture、hardened permission 和 secure coding benchmark，但缺少一个把 interface representation 与 authority granularity 分开并共同分析的 controlled study。

#### Motivation

在实践中，“给 agent 更强工具”与“给 agent 更小权限”不是单调的安全/性能旋钮。compound shell 可能减少 tool-call overhead，却放大不可见的 side effect；atomic tools 可能提高 observability，却增加 interaction turns；scoped permission 可能阻止攻击，也可能导致 retries、timeouts 或错误 patch。若没有因果分解，tool designers 无法知道应该改变 interface、permission、prompt、scaffold 还是 model。

#### Research Gap with Supporting Literature

- *The Devil Is in the Interface* 已控制 capability 并研究 tool architecture 对 resolve、consistency、exploration、tokens 的影响，但没有 authority 或 execution-security factor。
- *The Scaffolding Matters More Than the Interface* 说明 scaffold/MCP/CLI 表面差异会产生巨大 cost/completion differences，但任务单一，不能推出 repo-level security generalization。
- *Permission Denied* 证明 policy hardening 会影响 success、timeouts 和 cost，但没有 tool representation × privilege interaction。
- *SecureVibeBench* 与 *SEC-bench* 证明 repository-level secure outcome 是独立而困难的 construct，但没有解释 tool/authority cause。
- *IssueTrojanBench* 提供 coding-agent issue/repository attack vectors，但没有做 capability-matched interface/policy factorial。

因此，本研究的 gap 是 **joint causal attribution under execution-grounded security**，而不是“第一次比较两种工具”。

#### Novelty Compared with Closest 3–5 Papers

| Closest paper | 本研究不重复什么 | 本研究新增什么 |
|---|---|---|
| The Devil Is in the Interface | 不做 interface-only performance leaderboard | 加入 independent privilege factor、adversarial execution 和 security outcome |
| The Scaffolding Matters More Than the Interface | 不把 MCP/CLI 单一任务成本差异当作结论 | 使用多 repo paired tasks、capability manifest 和 controlled tool adapter |
| Permission Denied | 不只做 policy strictness / hardened environment | 识别 interface × privilege interaction，并以 coding-agent repository task 为单位 |
| SecureVibeBench | 不再造一个 secure-code benchmark | 把 secure behavior 作为 outcome，解释其与 interface/authority 的关系 |
| IssueTrojanBench | 不只测 attack success | 研究 attack success 是否由 interface representation、authority 和 denial feedback 所改变 |

#### Final Research Questions

- **RQ1**：在 clean repository tasks 上，tool architecture 与 privilege granularity 对 task success、test pass、patch correctness 和 consistency 的 main / interaction effects 是什么？
- **RQ2**：在 adversarial repository conditions 下，它们对 prompt-injection success、unauthorized operation、unsafe side effect、persistence 和 canary access 的 main / interaction effects 是什么？
- **RQ3**：security improvement 与 utility、wall-clock、tokens、tool calls、retries 和 monetary cost 之间的 trade-off 如何形成 Pareto frontier？
- **RQ4**：action granularity、observability、reversibility、denial feedback、context footprint、exploration 和 retry trajectory 哪些机制解释 RQ1–RQ3 的差异？

#### Hypotheses

这些是待检验假设，不是文献已经证明的事实：

- **H1**：在 capability-matched 条件下，tool architecture 对 clean-task utility 的 effect 小于 architecture 与 task difficulty/model 的 interaction；不能假设某个 interface universally better。
- **H2**：scoped privilege 相比 ambient privilege 降低 unauthorized side-effect rate 和 attack success，但可能增加 denial、retry、time 和 cost。
- **H3**：在 adversarial tasks 上，architecture × privilege interaction 显著；observability 和 least-privilege expressiveness 可能使 atomic/scoped design 的 security gain 大于简单相加的 main effects。
- **H4**：deny/retry、compound action 和 trajectory length 是部分 efficiency cost 的 mediators；该 mediation 需作为 model-based / exploratory mechanism analysis，不能仅凭相关性宣称因果。

#### Experimental Design

##### Study stages

1. **Stage 0 — Capability audit**：为每个 interface 生成 primitive-operation matrix 和 differential tests；任何不等价条件不进入主 causal analysis。
2. **Stage 1 — MVP**：2 architectures × 2 privilege levels × 12 clean tasks × 12 paired adversarial tasks × 3 rollouts；一个 frozen open model、一个 fixed agent loop。
3. **Stage 2 — Confirmation**：扩展到 24–40 tasks、5 rollouts、一个 frontier model；将 task/repository/model 作为 blocks/random effects。
4. **Stage 3 — External validity**：加入第三种 interface（MCP or structured CodeAct）、第二个 agent harness 或 secure-code benchmark；只有 Stage 2 primary effect 可复现时进行。

##### Benchmarks

- clean：SWE-bench Verified，按 repository/language/difficulty 分层；
- adversarial：IssueTrojanBench task families，或由同一 clean task 生成、经过 independent red-team validation 的 paired issue/README/file injection；
- secure extension：SecureVibeBench / SEC-bench，单独报告 secure-and-correct outcome；
- long-horizon extension：SWE-EVO，不进入 MVP。

##### Agents and models

固定 planner/model、prompt、test runner 和 container，只替换 tool adapter 与 policy engine。正式版至少一个 frontier coding model + 一个 frozen open coding model；不把 agent framework 作为主要 treatment。

##### Baselines

1. ambient + compound interface；
2. scoped + compound interface；
3. ambient + atomic interface；
4. scoped + atomic interface。

Optional controls：audit-only policy（记录但不阻止），用于区分“安全因为没有执行”与“安全因为 agent 改变行为”。

##### Metrics

- Primary utility：resolved-with-tests；
- Primary security：unauthorized or unsafe execution event per task attempt；
- Primary efficiency：wall-clock time and LLM monetary cost；
- Secondary：patch correctness、regression、ASR、canary access、unsafe read/write/network/process、tokens、tool calls、turns、denials、retries、pass^k；
- Joint outcome table：safe success / unsafe success / safe failure / unsafe failure / false denial。

##### Statistical analysis

- preregister 1–2 primary utility/security contrasts and the architecture × privilege interaction；
- mixed-effects logistic regression for success and security events；
- hierarchical bootstrap for paired task differences and Pareto confidence bands；
- negative-binomial or zero-inflated model for tool calls/retries；
- log-scale mixed model for time/tokens/cost；
- report risk difference, odds ratio, 95% CI and practical-effect threshold；
- Holm/BH correction for secondary outcomes；
- exact/randomization test for sparse attack events；
- no uncorrected per-metric p-value table and no observed-power claim。

#### Expected Figures / Tables

- **Figure 1 — Experimental causal graph**：architecture、privilege、condition、task/model blocks 与 utility/security/efficiency outcomes，回答 design validity。
- **Table 1 — Capability and authority matrix**：每种 interface 可执行的 primitive operations、path/network/process scope，回答 treatment equivalence。
- **Figure 2 — Security–utility–cost Pareto frontier**：四个 treatment cells 在 clean/adversarial conditions 的 frontier，回答 RQ3。
- **Figure 3 — Interaction plot**：architecture × privilege 对 success、unsafe execution 和 cost 的 estimated marginal means，回答 RQ1/RQ2。
- **Table 2 — Failure taxonomy**：denial、prompt injection、tool poisoning、unauthorized side effect、wrong patch、timeout 的 frequency 与 representative traces，回答 RQ4。
- **Figure 4 — Trajectory mechanism**：denials/retries/compound commands/turns 与 time/cost 的 hierarchical association，作为 explanatory evidence。

#### Expected Contribution

1. 一个 capability-matched 的 causal decomposition，说明 interface 与 authority 是否独立、是否 interaction。
2. 一个 execution-grounded 的 security–utility–efficiency frontier，而不是单一综合分数。
3. 一个可复用的 failure taxonomy，区分 interface-solvable、authority-solvable、model/scaffold-insufficient 风险。
4. 对 coding-agent developers 的设计规则：何时收紧权限、何时改 tool surface、何时不要把 policy 当作 secure coding 的替代品。
5. 可公开的 tool adapter、policy manifest、containers、logs、task commits 和 statistical scripts。

#### Threats to Validity

最大的 threats 是 capability mismatch、adversarial variant difficulty、model/API drift、judge bias、task contamination、repeated-rollout dependence、security construct undercoverage 和 cost measurement incompleteness。每一项都必须在 artifact 中保留 audit evidence，不能只在 Discussion 中形式性列出。

#### Artifact / Reproducibility Plan

- lockfile / Docker image digest / base repository commit；
- model endpoint、version、temperature、seed、prompt template；
- machine-readable capability matrix、permission policy、network rules；
- raw trajectory、tool-call trace、OS audit、canary alerts、test logs；
- public redacted logs，避免真实 secrets 与攻击 payload 扩散；
- evaluator version、price sheet、analysis code、pre-registration；
- reproduce script：pilot → clean → adversarial → stats → figures；
- secure execution：isolated disposable sandbox、deny-by-default network、fake credentials、no production tokens。

#### Minimum Viable Study

最少做：

- 1 个 frozen open model；
- 1 个 fixed agent loop；
- Bash/compound vs atomic 两个 interface；
- ambient vs scoped 两个 privilege level；
- 12 个 SWE-bench Verified clean tasks；
- 12 个 matched adversarial variants；
- 每格 3 次 rollout；
- OS-level execution logger + test oracle；
- 预注册 success、unsafe event、time、cost 四个 primary outcomes。

如果 2 × 2 的 interaction estimate 方向不稳定、CI 很宽，或 capability audit 无法通过，应停止扩展到 MCP、multi-agent 和更多模型。这个 MVS 的目的不是投稿，而是判断 Idea 5 是否值得投入一个学期。

## 11. Recommended Idea #2

### Full Proposal

#### Working Title Candidates

1. **Can Runtime Policies Travel? An Empirical Study of Security Retrofit Across Coding-Agent Architectures**
2. **Protocol-Soluble or Model-Insufficient? Security Retrofit for Repository-Level Coding Agents**
3. **Retrofitting Capability Boundaries into Coding Agents: Security Gains, Utility Losses, and Failure-Class Generalization**

#### Problem Statement

现有 runtime defense、protocol contract 和 policy enforcement 证明了“在一个 generic agent benchmark 上可以减少攻击”，但 coding-agent 的 failure 不仅是 tool misuse，还包括错误 patch、错误的 security judgment、错误的 provenance interpretation、依赖安装和 repository side effect。一个在 AgentDojo 上有效的 defense 是否能跨不同 coding-agent architecture 迁移，仍不清楚；更重要的是，安全层让 agent 失败时，失败究竟是 safe refusal 还是不必要的 false denial，也未被系统区分。

#### Motivation

如果每个 coding-agent 都需要专门的安全实现，工程成本很高；如果一个 reusable layer 能跨 architecture 工作，tool designers 可以集中维护 policy/provenance infrastructure。反过来，若大量风险属于 protocol-insufficient，则必须把安全责任放回 model training、task specification、repository governance 和 human review。这个 boundary 比“某个 defense 的 ASR 数字”更有 SE 实践价值。

#### Research Gap with Supporting Literature

- SEMAP 已覆盖 protocol-driven structured communication，但主要关注 coordination failure 与 task completion，而不是跨 coding-agent retrofit 的 execution-security portability。
- CaMeL、AgentArmor、Task Shield 已覆盖 capability/data-flow/task-alignment defense，但主要使用通用 agent security benchmarks。
- SEC-bench、SecureVibeBench 和 IssueTrojanBench 已提供 repository-level secure / adversarial coding-agent tasks，但不比较 reusable policy layer 的跨架构效果。
- Permission Denied 已展示权限策略的 utility/cost impact，但不提供 protocol/provenance retrofit 的 failure-class boundary。

本项目的 novelty 是 **portability + boundary + utility preservation**，而不是提出第五个 prompt-injection defense。

#### Final Research Questions

- **RQ1**：没有 retrofit 时，不同 coding-agent architectures 在 clean/adversarial repository tasks 中各自产生哪些 security failure classes？
- **RQ2**：同一个 capability-aware/provenance-aware runtime layer 能否跨 architecture 降低不同 violation classes 的 rate 和 ASR？
- **RQ3**：retrofit 对 resolved-with-tests、secure-and-correct outcome、false denial、time、tokens、retries 和 cost 的影响是什么？
- **RQ4**：哪些 failure classes 是 protocol-solvable，哪些稳定地表现为 model/scaffold/task-insufficient；这个分类能否跨 model/task family 泛化？

#### Hypotheses

- **H1**：runtime enforcement 对直接 capability violations 的效果大于对 semantic vulnerability 或 wrong-patch failures 的效果。
- **H2**：provenance-aware controls 对 tool poisoning / untrusted-data flows 的改善大于仅有 prompt-level refusal。
- **H3**：在一个 architecture 上 observed security gain 不一定迁移到另一个 architecture；adapter burden 和 tool-schema semantics 是 portability moderator。
- **H4**：enforcement 的 utility cost 主要由 false denial、retries 和 blocked dependency/network operations 产生，而不是由 policy check 本身的 compute overhead 产生。

#### Experimental Design

##### Treatments and baselines

- Agent architectures：两个 open coding-agent harness + 一个 minimal fixed-loop harness；同一 model/task/prompt 时尽量共用 planner。
- Security condition：no control、audit-only、capability enforcement、capability + provenance enforcement。
- Threats：prompt injection、issue/repository poisoning、tool metadata poisoning；每次单独 block。
- Baseline：prompt-only refusal/control，作为非-runtime baseline；CaMeL/AgentArmor 的公开实现若兼容且可安全复现，可作为 secondary baseline，不能依赖其不可复现的 external endpoint。

##### Outcome taxonomy

| Outcome | 例子 | 是否 protocol-solvable 的初始判定 |
|---|---|---|
| Direct authority violation | 未授权 path、network、process、credential/canary | 通常可由 capability policy 直接阻止 |
| Provenance / trust violation | 将 issue/README/tool metadata 中指令当成 trusted command | 可能由 provenance/data-flow layer 部分阻止 |
| Semantic wrong patch | tests pass 但 patch 违反 security requirement | 通常不能由 protocol 单独解决 |
| Unsafe but authorized action | policy 允许、模型却选择危险但合法操作 | 需要 semantic policy/model/task intervention |
| Safe refusal / false denial | agent 不能修复，但没有 unsafe event | policy effect 必须和 attack prevention 分开 |
| Cross-agent propagation | 恶意信息被下游 agent 采纳 | 只在 extension study 中纳入 |

##### Benchmarks and scope

MVP 采用 12 clean + 12 adversarial repository tasks，覆盖至少 2 languages 或 2 task types；扩展阶段使用 IssueTrojanBench、SEC-bench / SecureVibeBench。不要把 AgentDojo generic tasks 与 repository tasks 合并成一个 success rate；它们用于 threat taxonomy calibration。

##### Measurements and statistics

主要模型与 Idea 5 相同：mixed-effects logistic/negative-binomial/log-time models、cluster bootstrap、effect sizes、CIs、multiplicity correction。额外报告 policy coverage、adapter-specific rules、false-denial rate 和 inter-rater agreement for protocol-solvable labels。

#### Expected Figures / Tables

- **Table 1**：各 agent architecture 的 capability/provenance adapter coverage。
- **Figure 1**：baseline failure taxonomy across architecture and threat class。
- **Figure 2**：no-control vs audit-only vs enforcement 的 security/utility/cost trade-off。
- **Table 2**：protocol-solvable vs protocol-insufficient classification，含 execution evidence 与 reviewer agreement。
- **Figure 3**：cross-architecture transfer heatmap，回答 retrofit portability。

#### Expected Contribution

1. 跨 architecture 的 runtime-policy portability evidence；
2. 区分“安全降低”与“安全失败/false denial”的 measurement protocol；
3. protocol-solvable / protocol-insufficient taxonomy；
4. 对 middleware、agent developer 和 SE security reviewer 的边界性建议；
5. 可复现的 adapter/policy/task/trace artifact。

#### Threats to Validity

跨 architecture 的 adapter 质量会威胁 internal validity；应报告每个 adapter 的覆盖和人工配置量。Generic threat 到 coding-agent 的迁移威胁 external validity；应使用真实 repository issue content 和执行 oracle。protocol-solvable label 有 constructivity risk；应先定义规则、双人标注、保留 disagreement。模型/API drift、cost 和 sandbox escape 是 safety risks；所有攻击在 disposable isolated environment 中执行，不使用真实 secret 或 production credentials。

#### Artifact / Reproducibility Plan

发布 policy schema、adapter code、capability manifest、provenance labels、frozen task commits、container digests、raw/redacted traces、attack payload hash、evaluation scripts 和 analysis plan。攻击 payload 要以安全、无真实破坏性的 canary/temporary files 为主，并提供 reset script。

#### Minimum Viable Study

最少需要两个 coding-agent architectures、一个 frozen model、12 clean + 12 adversarial tasks、no-control vs capability enforcement、3 rollouts、OS audit 和 test oracle。如果 policy 只降低了成功率而没有降低 execution violation，立即停止扩大模型/benchmark，先重写 threat model；如果 effect 只在一个 architecture 出现，研究问题应转为 adapter portability，而不是宣称 reusable protocol。

## Proposal Documents

两个推荐方向已进一步扩展为独立开题报告：

- [Recommended Idea #1 — Interface × Authority](/Users/yan/Downloads/Agents_Research/docs/RECOMMENDED_IDEA_1_PROPOSAL.md)
- [Recommended Idea #2 — Cross-Architecture Security Retrofit](/Users/yan/Downloads/Agents_Research/docs/RECOMMENDED_IDEA_2_PROPOSAL.md)

## 12. Papers I Must Read

### Tier 1 — Must Read

这些论文会直接决定两个推荐 idea 是否成立。对于 arXiv 条目，venue 应按 preprint 处理，除非链接页面明确显示正式发表；不要把 preprint 自动写成 peer-reviewed conference paper。

| Paper / authors / year / venue | URL / DOI / arXiv | 与本项目的关系；已解决与未解决 |
|---|---|---|
| **SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering** — John Yang et al., 2024, arXiv preprint | [arXiv:2405.15793](https://arxiv.org/abs/2405.15793), DOI `10.48550/arXiv.2405.15793` | 基础 interface work；解决 agent-computer interface 的 SWE capability 价值；未解决 security/privilege causal effects |
| **OpenHands: An Open Platform for AI Software Developers as Generalist Agents** — Xingyao Wang et al., 2024, ICLR 2025 | [arXiv:2407.16741](https://arxiv.org/abs/2407.16741), DOI `10.48550/arXiv.2407.16741` | 提供 open platform、sandbox、tool interaction 和 benchmark；未做 interface × authority experiment |
| **The Devil Is in the Interface: Evaluating How Tool Architecture Shapes Coding Agent Behavior** — Xiangzhe Xu, Hamidreza Saghir, Qianhui Wu, Marc-Alexandre Côté, Tong Wang, Kiran Lakkaraju, Kexin Pei, Xiangyu Zhang, 2026, arXiv preprint | [arXiv:2608.11386](https://arxiv.org/abs/2608.11386), DOI `10.48550/arXiv.2608.11386` | 最直接杀死 Idea 5 interface-only 版本；未覆盖 privilege、security execution、joint frontier |
| **The Scaffolding Matters More Than the Interface** — Forment et al., 2026, arXiv preprint | [arXiv:2608.08654](https://arxiv.org/abs/2608.08654), DOI `10.48550/arXiv.2608.08654` | 杀死简单 MCP-vs-CLI 叙事；未覆盖多 repo、authority、security |
| **Permission Denied: Policy-Graded Evaluation of Coding Agents in Hardened Environments** — Davidovich et al., 2026, arXiv preprint | [arXiv:2608.02670](https://arxiv.org/abs/2608.02670), DOI `10.48550/arXiv.2608.02670` | 直接覆盖 policy/permission 的 success-cost effect；未做 interface × privilege factorial |
| **Towards Engineering Multi-Agent LLMs: A Protocol-Driven Approach** — Zhenyu Mao et al., 2025, arXiv preprint | [arXiv:2510.12120](https://arxiv.org/abs/2510.12120), DOI `10.48550/arXiv.2510.12120` | 直接覆盖 protocol-driven coordination；未覆盖跨 repo coding-agent 的 security retrofit/authority |
| **Defeating Prompt Injections by Design** — Edoardo Debenedetti, Ilia Shumailov, Tianqi Fan, Jamie Hayes, Nicholas Carlini, Daniel Fabian, Christoph Kern, Chongyang Shi, Andreas Terzis, Florian Tramèr, 2025, arXiv preprint | [arXiv:2503.18813](https://arxiv.org/abs/2503.18813), DOI `10.48550/arXiv.2503.18813` | CaMeL 证明 capability/data-flow defense；未覆盖 repo-level cross-architecture utility/cost |
| **AgentArmor: Enforcing Program Analysis on Agent Runtime Trace to Defend Against Prompt Injection** — Peiran Wang et al., 2025, arXiv preprint | [arXiv:2508.01249](https://arxiv.org/abs/2508.01249), DOI `10.48550/arXiv.2508.01249` | runtime trace / program analysis defense；未覆盖 coding-agent repository retrofit portability |
| **AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents** — Debenedetti et al., 2024, NeurIPS 2024 Datasets and Benchmarks | [NeurIPS official page](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html) | 提供 dynamic tool-integrated security evaluation；不是 repository coding-agent interface/authority study |
| **SEC-bench: A Comprehensive Benchmark for Secure Code Generation in Real-World Software Engineering** — Hwiwon Lee et al., 2025, NeurIPS 2025 | [NeurIPS official page](https://proceedings.neurips.cc/paper_files/paper/2025/hash/a9168f1c54e5147027f1e8cf83e1a775-Abstract-Conference.html) | repo-level vulnerability reproduction/patching oracle；不识别 tool/privilege cause |
| **SecureVibeBench: Benchmarking Secure Code Generation in Real-World Repositories** — Junkai Chen et al., 2025/ACL 2026 Main, arXiv version | [arXiv:2509.22097](https://arxiv.org/abs/2509.22097) | large C/C++ secure repository benchmark；不做 interface/authority treatment |
| **IssueTrojanBench: Benchmarking AI Coding Agents Against Malicious Issue Requests** — Ankur Singh, Jinqiu Yang, Tse-Hsun Chen, 2026, arXiv preprint | [arXiv:2607.20759](https://arxiv.org/abs/2607.20759), DOI `10.48550/arXiv.2607.20759` | 最新 coding-agent issue/repository attack delivery vectors；正式 venue 在当前检索中按 arXiv 记录，正式出版信息需继续核验 |

### Tier 2 — Closely Related

| Paper / authors / year / venue | URL | 用途与限制 |
|---|---|---|
| **A Comprehensive Empirical Evaluation of Agent Frameworks on Code-centric Software Engineering Tasks** — Zhuowen Yin et al., 2025, arXiv preprint | [arXiv:2511.00872](https://arxiv.org/abs/2511.00872) | framework-level effectiveness/efficiency baseline；confounding 较多，不能直接作 causal comparison |
| **SWE-Search: Smaller Language Models Can Surpass Larger Language Models for SWE Tasks** — Antonis Antoniades et al., ICLR 2025 | [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/a1e6783e4d739196cad3336f12d402bf-Abstract-Conference.html) | multi-agent search / inference-time compute；不是 security/authority study |
| **CooperBench: Why Coding Agents Cannot Be Your Teammates Yet** — Arpandeep Khatua et al., 2026, arXiv preprint | [arXiv:2601.13295](https://arxiv.org/abs/2601.13295) | multi-agent collaborative coding failure；可作为 communication collision，不应与单 agent authority 混为 treatment |
| **SWE-Effi: ...** — Fan et al., 2025, arXiv preprint | [arXiv:2509.09853](https://arxiv.org/abs/2509.09853) | resource efficiency / token snowball；支撑 efficiency metric，不覆盖 security |
| **Understanding Code Agent Behaviour: An Empirical Study of Success and Failure Trajectories** — Majgaonkar et al., 2025, arXiv preprint | [arXiv:2511.00197](https://arxiv.org/abs/2511.00197) | trajectory/failure descriptive analysis；不能替代 intervention/causal mechanism |
| **GitTaskBench: ...** — Ni et al., 2025, arXiv preprint | [arXiv:2508.18993](https://arxiv.org/abs/2508.18993) | realistic repository task and resource-aware benchmark；综合 score 不替代 security outcomes |
| **Automated Benchmark Generation for Repository-Level Coding Tasks** — Vergopoulos et al., ICML 2025 | [PMLR official page](https://proceedings.mlr.press/v267/vergopoulos25a.html) | benchmark diversity / setup generation；用于 external validity 与 task selection |
| **SWE-EVO: ...** — Thai et al., 2025, arXiv preprint | [arXiv:2512.18470](https://arxiv.org/abs/2512.18470) | long-horizon software evolution；成本高，适合后续 external validity |
| **SOEN-101: Code Generation by Emulating Software Process Models Using LLMs** — Feng Lin et al., ICSE 2025 | [ICSE official page](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/141/SOEN-101-Code-Generation-by-Emulating-Software-Process-Models-Using-Large-Language-M) | multi-agent/process organization；以 function-level benchmark 为主，不涉及 security |
| **Instruct or Interact? Exploring and Eliciting LLMs' Capability in Code Snippet Adaptation** — authors listed on ICSE page, ICSE 2025 | [ICSE official page](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/96/Instruct-or-Interact-Exploring-and-Eliciting-LLMs-Capability-in-Code-Snippet-Adapta) | interactive/multi-turn code generation；不是 repository-level agent security |
| **Towards Multi-Agent Security Benchmarks / ASB** — authors on project page, ICLR 2025 | [ASB official project](https://luckfort.github.io/ASBench/) | attack/defense taxonomy and metrics；generic agents，需谨慎外推 |
| **MCPTox: ...** — Zhiqiang Wang et al., AAAI 2026 | [AAAI page](https://ojs.aaai.org/index.php/AAAI/article/view/40895), [arXiv:2508.14925](https://arxiv.org/abs/2508.14925) | live MCP tool poisoning；作为 tool-metadata threat source，不是 repo task outcome |
| **The Task Shield: ...** — Feiran Jia et al., ACL 2025 | [ACL Anthology](https://aclanthology.org/2025.acl-long.1435/) | task-alignment defense baseline；不是 cross-architecture retrofit |

### Tier 3 — Background

| Paper / source | URL | 用途 |
|---|---|---|
| **On the Use of Agentic Coding: An Empirical Study of Pull Requests on GitHub** — Watanabe et al., 2025, arXiv | [arXiv:2509.14745](https://arxiv.org/abs/2509.14745) | 真实 GitHub PR adoption / maintenance context |
| **Agentic Refactoring: An Empirical Study of AI Coding Agents** — Horikawa et al., 2025, arXiv | [arXiv:2511.04824](https://arxiv.org/abs/2511.04824) | real-world agentic refactoring distribution |
| **Where Do AI Coding Agents Fail?** — Ehsani et al., 2026, arXiv | [arXiv:2601.15195](https://arxiv.org/abs/2601.15195) | large-scale observational failure taxonomy |
| **SUSVIBES / Is Vibe Coding Safe?** — Zhao et al., 2025, arXiv | [arXiv:2512.03262](https://arxiv.org/abs/2512.03262) | functional vs secure coding-agent outcome separation |
| **Agent Security Bench (ASB)** | [Project page](https://luckfort.github.io/ASBench/) | generic security benchmark background |
| **SWE-bench** | [Official site](https://www.swebench.com/) | repository-level issue resolution benchmark context |

### Metadata and verification notes

- 2026 preprints are volatile. A title, author list or venue marked “arXiv preprint” should be rechecked immediately before paper submission.
- `The Devil Is in the Interface`, `The Scaffolding Matters More Than the Interface` and `Permission Denied` are especially important because they appeared very close to the analysis date and materially change the novelty assessment.
- For a final paper, download the PDF source, inspect abstract/method/experiments, record commit/version and add a paper-level evidence ID. Do not cite search snippets as if they were full-paper findings.

## 13. Recommended Next Steps

### 未来 1 周：判断 Idea 5 是否值得继续

1. 固定一个 model snapshot、agent loop、container 和 12 个 SWE-bench Verified tasks。
2. 实现 Bash/compound 与 atomic 两个 capability-equivalent adapter。
3. 实现 ambient 与 scoped policy；建立 path/network/process capability matrix。
4. 构造 12 个 paired adversarial variants，只使用 fake credentials、canary files、deny-by-default network 和 disposable sandbox。
5. 做 2 × 2 × clean/adversarial × 3 rollout pilot；记录 raw trace，不只保存最终 patch。
6. 预先定义四个 primary outcomes：resolved-with-tests、unsafe execution、wall-clock、cost；不要先看结果再改指标。

### 未来 2 周：完成 pilot audit 与 statistical feasibility

1. 检查每个 interface 的 primitive-operation equivalence、tool-schema token footprint 和 denial feedback。
2. 生成 safe success / unsafe success / safe failure / unsafe failure / false denial contingency table。
3. 用 hierarchical bootstrap 或 mixed-effects pilot model 估计 effect size 和 CI；判断是否需要增加 tasks、rollouts 或第二 model。
4. 由两名研究者独立标注 30–50 条 security traces，计算 taxonomy agreement；修订 protocol-solvable labels。
5. 运行 novelty re-check：重点查 2026 新论文、官方 GitHub、ACM/IEEE 早期访问和 citation follow-ups。
6. **Stage gate**：若 capability equivalence 不成立、attack oracle 不可信、或安全 effect 只是“全部失败”，停止扩大实验并重写题目。

### 未来 1 个月：形成可投稿研究包

1. 扩展到 24–40 tasks、5 rollouts、一个 frontier model；加入 repository/language/difficulty blocks。
2. 预注册 RQs、primary contrasts、outcome definitions、exclusion rules、model/version/date、cost price sheet 和 multiple-comparison policy。
3. 完成 Figures 1–4 与 Tables 1–2 的数据 schema，先写方法和 analysis plan，再运行正式实验。
4. 将 Idea 2 + 4 的 retrofit pilot 作为第二路线：两个 agent architectures、no-control vs enforcement、12 clean + 12 adversarial tasks；不要同时加入 multi-agent propagation。
5. 对所有关键 collision paper 下载正文并建立 claim–evidence matrix；对无法核实的 venue、作者、实验细节标记 **Not verified**。
6. 形成 artifact release：container digest、task commit、policy file、adapter code、prompts、logs、redacted attacks、test/evaluation scripts、analysis code 和 replication README。

### 最终决策规则

- 若 Idea 5 在 pilot 中显示 architecture × privilege interaction，且 security gain 不只是 false denial，则继续作为主论文。
- 若只有 privilege main effect，没有 architecture interaction，则改题为 policy-grading / authority frontier，并明确承认与 Permission Denied 的差异仅在 coding-agent repository setting。
- 若只有 interface effect，没有 security effect，则停止“security frontier”叙事，转为 interface paper 或放弃以避免重复 *The Devil Is in the Interface*。
- 若 retrofit 在多个 architectures 上只造成 utility loss而不改善 execution security，则放弃 Idea 2/4 的 reusable-protocol claim。
- 若所有结果高度 model-dependent，应把 model dependence 本身作为 RQ2/RQ4，而不是平均化隐藏它。
