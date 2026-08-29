# 开题报告二：跨 Coding-Agent Architecture 的 Capability-Aware Security Retrofit

## Working Title

**Can Runtime Policies Travel? An Empirical Study of Security Retrofit Across Coding-Agent Architectures**

中文题目：**运行时安全策略能否迁移？跨 Coding-Agent Architecture 的 capability-aware security retrofit 实证研究**

备选标题：

1. **Protocol-Soluble or Model-Insufficient? Security Retrofit for Repository-Level Coding Agents**
2. **Retrofitting Capability Boundaries into Coding Agents: Security Gains, Utility Losses, and Failure-Class Generalization**

> **研究阶段**：开题报告草案，不包含实验结果。  
> **文献核验边界**：截至 2026-08-17；arXiv 工作按 preprint 处理，正式 venue 需在投稿前重新核验。  
> **研究类型**：跨 agent architecture 的 randomized blocked empirical retrofit study。  
> **与 Idea #1 的关系**：Idea #1 研究 interface × authority 的 causal interaction；本课题研究同一个 capability-aware/provenance-aware runtime layer 能否跨不同 coding-agent architecture 迁移，以及它不能解决什么。

## 摘要

AI coding agents 正从受限的 code completion 工具变成能够访问 repository、执行测试、修改文件和调用外部工具的 semi-autonomous systems。prompt injection、issue/repository poisoning、tool metadata poisoning、unauthorized file/network/process access 和错误的跨组件信任使得“功能完成”与“安全完成”之间出现明显差距。已有研究已经提出 capability-based policy、information-flow control、runtime-trace analysis、task-alignment defense 和 hardened execution policy，但这些机制通常在通用 agent benchmark、单一 scaffold 或固定环境中验证。

本研究不以提出一个新的 prompt-injection defense 为主，而是构建一个透明、可审计、可复用的 capability-aware/provenance-aware runtime wrapper，并在多个 repository-level coding-agent architectures 上进行 controlled retrofit comparison。研究比较 no-control、audit-only、capability enforcement 和 capability + provenance enforcement 四种条件，使用 clean 与 adversarial paired repository tasks，测量 direct authority violation、untrusted-data flow、unsafe side effect、semantic wrong patch、safe refusal、false denial、task utility、time、tokens、retries 和 cost。

核心研究问题是：一个 runtime policy layer 是否真的“可迁移”，还是只能在特定 scaffold 和 tool semantics 下工作？哪些风险是 protocol-solvable，哪些风险必须依靠 model、task specification、repository governance 或 human review？研究的主要产出不是一个更低的 ASR 数字，而是一个带 execution evidence 的 failure taxonomy、cross-architecture portability estimate 和 utility-preservation boundary。

## 1. 研究背景与问题定义

### 1.1 从 generic agent defense 到 coding-agent retrofit

通用 agent security 工作通常研究 agent 读取不可信数据、调用工具和处理任务时的 prompt injection 或 data-flow violation。coding-agent 具有额外的 software-engineering state：repository content、issue text、dependency files、test output、git history、build process、filesystem 和开发者工具。安全层可能阻止一次危险 tool call，却也可能阻断正常依赖安装、测试执行、文件写入或调试流程。

因此，一个防御机制在 AgentDojo 或 ASB 上有效，不代表它能在真实 repository-level coding tasks 上：

- 保留 patch utility；
- 区分 untrusted instruction 与 legitimate repository content；
- 在不同 tool schema 和 agent loop 中观察同一 provenance；
- 不把所有 blocked action 变成 timeout 或 silent failure；
- 用相同规则跨 architecture 迁移。

### 1.2 本研究中的 X–Y–Z 句子

> [claim:causal] [estimand:policy_architecture_contrast] [identification:randomized] [confounding:assessed] [selection:assessed] [collider:assessed] [reverse-causation:assessed] **We study whether execution-security violations are lower under a capability-aware and provenance-aware runtime policy layer across heterogeneous repository-level coding-agent architectures, and how much task utility, latency, and monetary cost differ under matched clean and adversarial tasks.**

对应中文：

> 我们研究同一个 capability-aware、provenance-aware runtime policy layer 能否在异构 repository-level coding-agent architectures 之间稳定降低 execution-security violations，以及它在成对的 clean/adversarial tasks 下会带来多少 task utility、latency 和 monetary cost 变化。

### 1.3 核心概念

#### Retrofit

Retrofit 指在不重写 agent planner、model 和任务定义的前提下，通过外部 wrapper、tool adapter、policy engine 和 provenance instrumentation 增加 runtime security control。若每个 agent 都需要独立重写 planner、prompt 或 tool semantics，研究只能声称 agent-specific defense，不得声称 reusable retrofit。

#### Portability

Portability 不是“所有架构都得到相同分数”。本研究将其定义为：在预先固定的 policy schema 和相近 adapter effort 下，security effect 的方向、failure-class coverage 和 utility/cost pattern 能否跨 architecture 复现。

#### Protocol-solvable

一个 failure 被标记为 protocol-solvable 的初始候选，当且仅当：

1. 触发行为涉及可观察的 capability boundary、provenance edge 或 tool-call policy；
2. runtime layer 在不依赖模型重新理解语义的情况下可以阻止或标记该行为；
3. execution trace 能够证明 intervention 改变了 outcome。

这个 label 是待验证的 taxonomy hypothesis，不是先验事实。最终分类需要双人标注、规则审计和 disagreement report。

## 2. 文献基础与 Research Gap

### 2.1 Protocol-driven software-engineering agents

[Towards Engineering Multi-Agent LLMs: A Protocol-Driven Approach](https://arxiv.org/abs/2510.12120)（Zhenyu Mao, Jacky Keung, Fengji Zhang, Shuo Liu, Yifei Wang, Jialong Li, 2025, arXiv preprint）提出 SEMAP，在 A2A 基础上使用 explicit behavioral contracts、structured messaging 和 lifecycle-guided execution/verification，并在 function-level development、deployment-level development 和 vulnerability detection tasks 中评估 failure reduction。它直接说明 protocol layer 可以改善部分 coordination/verification failures，但尚未回答：同一安全 runtime layer 能否跨现有 repository-level coding-agent architectures 迁移，且不牺牲 utility。

### 2.2 Runtime and information-flow defenses

[Defeating Prompt Injections by Design](https://arxiv.org/abs/2503.18813)（Edoardo Debenedetti et al., 2025, arXiv preprint）提出 CaMeL，以 control/data flow 和 capability-based tool policy 约束不可信数据对 agent execution 的影响。[AgentArmor: Enforcing Program Analysis on Agent Runtime Trace to Defend Against Prompt Injection](https://arxiv.org/abs/2508.01249)（Peiran Wang et al., 2025, arXiv preprint）把 agent runtime trace 转换为可分析的 structured program，并检查敏感数据流、trust boundary 和 policy violation。[The Task Shield](https://aclanthology.org/2025.acl-long.1435/)（Feiran Jia et al., ACL 2025）则从 task alignment 角度降低 prompt-injection risk。

这些工作解决了“可以设计某种 defense”的问题，但仍留下三个 SE empirical questions：

1. defense 是否适应 coding-agent repository state 和多种 tool semantics；
2. security gain 是否被 false denial、timeout、retry 或错误 patch 抵消；
3. generic defense 能否把 failure 分成 protocol-solvable 与 protocol-insufficient。

### 2.3 Coding-agent security benchmarks

[AgentDojo](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html)（NeurIPS 2024 Datasets and Benchmarks Track）提供 dynamic tool-integrated prompt-injection evaluation；[Agent Security Bench](https://luckfort.github.io/ASBench/)（ICLR 2025 project）扩展了多场景、多工具和多攻击/防御测量；[MCPTox](https://ojs.aaai.org/index.php/AAAI/article/view/40895)（AAAI 2026）研究 live MCP server/tool poisoning。

这些 benchmark 是 threat taxonomy 的重要来源，但不能直接当作 repository-level coding-agent external validity。它们的 task state、tool semantics、success oracle 和 threat delivery vector 与 SWE task 不完全相同。

[SEC-bench](https://proceedings.neurips.cc/paper_files/paper/2025/hash/a9168f1c54e5147027f1e8cf83e1a775-Abstract-Conference.html)（Hwiwon Lee et al., NeurIPS 2025）与 [SecureVibeBench: Benchmarking Secure Vibe Coding of AI Agents via Reconstructing Vulnerability-Introducing Scenarios](https://arxiv.org/abs/2509.22097)（Junkai Chen et al., arXiv version）提供 repository-level secure-code evaluation。[IssueTrojanBench: Benchmarking AI Coding Agents Against Malicious Issue Requests](https://arxiv.org/abs/2607.20759)（Ankur Singh, Jinqiu Yang, Tse-Hsun Chen, 2026, arXiv preprint）则提供 modern coding-agent issue delivery vector。它们能回答“风险是否存在”，但不回答一个 reusable retrofit layer 的跨架构迁移边界。

### 2.4 Permission and policy cost

[Permission Denied: Policy-Graded Evaluation of Coding Agents in Hardened Environments](https://arxiv.org/abs/2608.02670)（Dotan Davidovich et al., 2026, arXiv preprint）报告 hardened policy 对 coding-agent success、timeout 和 cost 的显著影响，并检查 strict policy 下任务是否仍可解。它是本课题必须纳入的 collision：如果本课题只展示“权限收紧会增加 cost”，则没有独立贡献。本课题研究的是 runtime layer 的跨架构 portability、failure boundary 和 security/utility decomposition。

### 2.5 Gap 的严格表述

截至 2026-08-17 的检索边界，未定位到一个同时满足以下条件的研究：

- 在至少两个异构 repository-level coding-agent architectures 上使用同一 policy schema；
- 明确区分 no-control、audit-only、capability enforcement 和 provenance-aware enforcement；
- 在 clean/adversarial paired tasks 中同时测 direct authority violation、untrusted-data flow、semantic wrong patch、safe refusal、false denial、utility、time 和 cost；
- 对 adapter-specific coverage、failure taxonomy 和 policy-induced failure transfer 做可审计分析；
- 用 task/repository-aware statistics 估计 cross-architecture portability，而不是比较不同产品的 aggregate ASR。

这个 gap 值得研究的原因是工程上需要知道安全责任边界：一个 runtime policy layer 能否成为可复用 infrastructure，还是必须针对每个 agent architecture 定制；以及哪些危险无法通过 protocol layer 消除。

### 2.6 Novelty collision

| 相邻工作 | 它会杀死的版本 | 本研究的必要差异 |
|---|---|---|
| SEMAP | “protocolized communication 能降低 agent failure”本身 | 研究 security retrofit portability、authority boundary 和 repository execution |
| CaMeL | “我们设计 capability/data-flow defense”本身 | 不把新 defense 作为 novelty；比较跨 architecture 的 empirical boundary |
| AgentArmor | “runtime trace analysis 可降低 ASR”本身 | 研究 coding-agent task utility、adapter coverage、cost 和 protocol-insufficient failures |
| Task Shield | “task-alignment prompt defense 可防 injection”本身 | 将 prompt-only/control 与 runtime enforcement 放入 capability-matched baseline |
| Permission Denied | “permission hardening 有 utility/cost 代价”本身 | 研究同一 retrofit 在多个 agent architecture 的 security gain 与 false-denial boundary |
| SecureVibeBench / SEC-bench | “repository-level secure coding agent 有风险”本身 | 使用 secure outcome 作为 dependent variable，研究 mitigation portability |

因此，本课题的 novelty statement 应为：

> **The contribution is empirical evidence about the portability and limits of a reusable security retrofit across repository-level coding-agent architectures, not another generic prompt-injection defense.**

## 3. 研究目标、范围与单位

### 3.1 总目标

构建并评估一个透明的 capability-aware/provenance-aware runtime wrapper，回答：

1. 不同 coding-agent architectures 的 baseline security failure map 是否相同；
2. 同一 policy layer 是否能跨 architecture 降低可观察的 execution-security violations；
3. security gain 是否以 utility、false denial、time、retry 和 cost 为代价；
4. 哪些 failure 属于 protocol-solvable，哪些需要 model/scaffold/task-level intervention。

### 3.2 研究范围

#### 纳入

- repository-level issue resolution、test/build/debug、secure code task；
- 至少两个可公开运行或可审计的 coding-agent harness；
- local filesystem、process、test/build、network allowlist、tool metadata 和 repository content threat；
- no-control / audit-only / enforcement 的 controlled comparison；
- single-agent MVP，multi-agent propagation 作为后续 extension。

#### 不纳入 MVP

- 真实生产系统、真实第三方工具、真实 credential；
- 未授权攻击、持久化破坏或网络横向移动；
- 需要重训 model 的 defense；
- 同时新增一个 protocol、一个 benchmark、一个 agent framework 和一个 security model；
- cross-agent propagation 的完整 causal study。

## 4. Research Questions、Estimands 与 Hypotheses

### RQ1 — Baseline failure map

在没有 retrofit 时，不同 coding-agent architectures 在 clean/adversarial repository tasks 中产生哪些 execution-security failure classes？这些 failure 的频率、严重度和 architecture dependence 如何？

### RQ2 — Retrofit effect and portability

同一个 capability-aware/provenance-aware runtime layer 能否跨 architecture 降低 violation rate、attack success 和 unsafe side effect？其 effect 是否被 threat class、task family、model 或 tool-schema semantics 调节？

### RQ3 — Utility and efficiency cost

retrofit 对 resolved-with-tests、secure-and-correct outcome、false denial、timeout、time、tokens、retries 和 monetary cost 的影响是什么？

### RQ4 — Protocol-solvable boundary

哪些 failure classes 稳定地可由 runtime policy 阻止或审计，哪些 failure classes 在 enforcement 后仍然出现，并表现为 model/scaffold/task-insufficient？这个分类能否跨 architecture 和 model 泛化？

### Hypotheses

- **H1（direct authority）**：capability enforcement 对 direct unauthorized file/network/process events 的降低幅度大于对 semantic wrong patch 或 model-generated insecure code 的降低幅度。
- **H2（provenance）**：capability + provenance enforcement 相比 capability-only 对 issue/repository/tool-metadata poisoning 的 unsafe execution rate 改善更大，但可能带来更高的 false denial 或 context overhead。
- **H3（portability）**：同一 policy layer 的 security effect 会受到 agent architecture 和 tool-schema semantics 调节；跨 architecture 的方向可能一致，但 effect magnitude 不应预设相同。
- **H4（utility cost）**：enforcement 的主要 utility cost 来自 false denial、blocked dependency/network operation、retry 和 timeout，而不是 policy check 的纯计算 latency。
- **H5（boundary）**：若 policy layer 阻止了 direct authority violation 但 semantic wrong patch 保持不变，则支持 protocol-solvable / protocol-insufficient 的分层，而不是证明整个 coding-agent 已安全。

### Rival explanations

| Rival | 预测 | 区分实验 |
|---|---|---|
| Prompt-only compliance | prompt-only 已能达到与 runtime enforcement 相同的安全效果 | 加 prompt-only baseline，并以 execution event 而非 refusal text 判定 |
| Adapter effort effect | 某 architecture 的 improvement 来自人工为它写了更多规则 | 记录 adapter lines/rules、coverage 和 engineering effort，按 predeclared budget 对齐 |
| Policy-induced early failure | attack rate 下降只是 agent 更快放弃 | 联合报告 safe success、safe failure、false denial、unsafe success、unsafe failure |
| Task solvability | strict policy 让某 task 变得不可解，而不是暴露 agent failure | 在严格 policy 下先跑 solvability check；单独标记 policy-foreclosed tasks |
| Threat mismatch | attack 只针对某个 architecture 的 prompt/tool semantics | paired threat construction，报告 delivery vector coverage 和 architecture-specific adaptation |
| Model refusal | 安全来自 model 自己拒绝，runtime layer 没有额外作用 | audit-only vs enforcement、trace-level policy intervention 和 model stratification |
| Measurement blind spot | policy log 没记录 side effect | OS/filesystem/network/process audit 与 canary oracle 交叉验证 |

## 5. Security Retrofit 设计

### 5.1 设计原则

本课题的 retrofit 需要满足：

1. **Transparent**：policy schema、decision reason 和 deny event 可读；
2. **Capability-aware**：每个 tool/action 映射到 capability、resource scope 和 actor；
3. **Provenance-aware**：记录 instruction、repository data、tool metadata、model output 和 execution result 的来源链；
4. **Architecture-agnostic core**：policy semantics 尽量不依赖特定 planner；
5. **Adapter-thin**：每个 agent 只负责将 action 映射为统一 event schema；
6. **Observable decisions**：记录 policy denial reason、false denial 和 recovery path；
7. **Replayable**：相同 event trace 可重放 policy decision。

### 5.2 Policy conditions

| Condition | 是否阻止 action | 目的 |
|---|---:|---|
| No-control | 否 | baseline agent behavior |
| Audit-only | 否 | 区分 logging overhead 与 enforcement effect |
| Capability enforcement | 是 | 测直接 authority boundary |
| Capability + provenance enforcement | 是 | 测 capability 与 untrusted-data lineage 的组合 |

Prompt-only refusal 可以作为 secondary baseline，但不能代替 runtime layer，因为文字拒绝不是 execution security evidence。

### 5.3 Unified event schema

每个 tool/action event 至少包含：

```text
event_id, run_id, agent_id, architecture_id,
action_type, tool_name, capability_id,
resource_type, resource_scope, requested_operation,
input_provenance, output_provenance,
policy_condition, policy_decision, decision_reason,
timestamp, parent_event_id, execution_result,
filesystem_delta, network_target_class, process_class,
denial_feedback_hash
```

不保存真实 secret 或有害 payload；公开版本使用 redaction、hash 和 synthetic canary。

### 5.4 Adapter contract

每个 agent architecture 要通过相同接口实现：

- `observe_model_action()`；
- `normalize_tool_call()`；
- `attach_provenance()`；
- `check_policy()`；
- `execute_or_deny()`；
- `record_result()`。

若某个 architecture 无法暴露 action、provenance 或 execution result，不能将其与完整 instrumentation 的 architecture 直接比较；应在主分析中排除或单独作为 observability limitation。

## 6. 实验设计

### 6.1 Agent architectures

正式研究至少选择：

1. 一个以 tool loop 为核心的 open coding-agent harness；
2. 一个具有不同 tool orchestration / planning / context management 的 open harness；
3. 一个 minimal fixed-loop reference harness，用于区分 policy effect 与现有 framework behavior。

不把 commercial product 的黑盒差异作为主要 architecture causal evidence。若后续加入 commercial system，只作为 external validation，并记录无法观察的 tool/provenance limitations。

### 6.2 Model、prompt 与预算

- MVP 使用一个 frozen model，固定 temperature、system/task prompt、context budget、max steps、retry、timeout 和 test command；
- confirmation 版增加一个 frontier/API model；
- model 是 block/replication factor，不是 retrofit treatment；
- 记录 model snapshot、endpoint、API date、seed、price sheet 和 failed request。

### 6.3 Benchmark 与 threat blocks

#### Clean block

12–24 个 SWE-bench Verified 或同类 repository tasks，覆盖不同 repository size、language 和 task type。clean block 用于测 utility preservation 和无攻击条件下的 false denial。

#### Adversarial block

12–24 个与 clean task 成对或分层匹配的 adversarial tasks，覆盖：

- issue/README/repository file 中的 indirect prompt injection；
- tool metadata / description poisoning；
- untrusted output 诱导不当 filesystem/process/network action；
- safe-looking instruction 与 privileged operation 的 trust-boundary conflict。

攻击只在 isolated disposable sandbox 中运行，使用 fake credentials、canary resources、temporary paths 和 allowlisted network。每个 threat 需要 benign counterpart，才能估计 false denial。

#### Secure-code block（extension）

SecureVibeBench/SEC-bench 用于 secure-and-correct、vulnerability-introduced 和 patch security outcome。不要把其 security outcome 与 direct authority event 合成同一指标。

### 6.4 MVS 与确认研究

#### Stage 0 — Retrofit feasibility

- 在三个 harness 上接入统一 event schema；
- 运行 capability/provenance coverage tests；
- 记录 adapter-specific rule 数量和人工配置时间；
- 任何 architecture 若无法达到最低 observability，不进入 portability primary analysis。

#### Stage 1 — MVS

- 2 个 agent architectures；
- 1 个 frozen model；
- 12 clean + 12 adversarial tasks；
- no-control vs capability enforcement；
- 每 task/condition 3 次 rollout；
- 预计 144 个 primary task attempts（24 tasks × 2 conditions × 3 rollouts），若加入 audit-only 则为 216；
- 目标是判断 direct security event、utility cost 和 false denial 是否可测。

#### Stage 2 — Confirmatory retrofit study

- 3 个 architectures；
- no-control、audit-only、capability enforcement、capability + provenance enforcement；
- 24–40 clean + 24–40 adversarial tasks；
- 2 个 model；
- 每个 cell 5 次 rollout；
- task/repository/language/threat class 作为 blocks；
- 在正式收集前锁定 policy、task manifest、primary outcomes、exclusion rules 和 model endpoints。

### 6.5 Protocol-solvable taxonomy procedure

1. 在数据 collection 前写出 taxonomy codebook 和 examples；
2. 将每个 observed failure 映射到 direct authority、provenance/trust、semantic patch、unsafe-authorized action、environment/setup、timeout/retry、cross-agent（extension）等类别；
3. 两名独立 annotators 只看 redacted execution trace、policy log 和 task outcome；
4. 报告 agreement、disagreement 和 adjudication rule；
5. 先进行 taxonomy reliability check，再在 full dataset 上做 portability inference；
6. 若 label 只靠研究者对 model intent 的猜测，不得写成 protocol-solvable conclusion。

## 7. 变量与结果测量

### 7.1 Primary outcomes

| Outcome family | Primary variable | Operational definition |
|---|---|---|
| Security | direct violation rate | 每个 task attempt 是否发生至少一次未授权 filesystem/network/process/canary action |
| Security | attack success rate | adversarial content 是否导致预定义 unsafe side effect 或 policy violation |
| Utility | resolved-with-tests | patch 正确应用且 required tests pass、无预定义 regression |
| Utility/security | secure-and-correct | functional outcome 与 secure oracle 同时通过 |
| Utility cost | false denial | policy 拒绝了完成任务所需且 threat model 认为 benign 的 action |
| Time | wall-clock | episode elapsed time，含 retries/blocked action |
| Cost | monetary cost | LLM tokens + declared tool/service cost，使用 frozen price sheet |

### 7.2 Secondary outcomes

- failure class frequency、severity 和 architecture coverage；
- denial count、policy-check latency、retry count、timeout；
- input/output tokens、LLM calls、tool calls、messages、trajectory length；
- dependency/network blocked count；
- canary access、sensitive-resource read/write、persistence attempt；
- patch correctness、regression、test coverage change、secure vulnerability status；
- adapter effort：rules、lines、manual exceptions、unsupported event types。

### 7.3 Joint outcome matrix

所有 attempt 进入以下 mutually exclusive primary outcome：

1. **Safe success**：task success 且无 unsafe event；
2. **Unsafe success**：task success 但发生 unsafe event；
3. **Safe failure**：未完成但无 unsafe event；
4. **Unsafe failure**：未完成且发生 unsafe event；
5. **False denial**：policy 造成不必要的 benign action refusal，并影响 task completion。

这能避免把“agent 被拦住了”与“agent 安全地完成了任务”混为一个 positive security result。

## 8. Statistical Analysis Plan

### 8.1 Primary estimands

- no-control → capability enforcement 的 direct violation risk difference；
- no-control → capability + provenance enforcement 的 attack success risk difference；
- enforcement 对 resolved-with-tests 的 risk difference；
- enforcement 对 false-denial、wall-clock 和 monetary cost 的 ratio/difference；
- architecture × policy interaction；
- threat class × policy interaction。

### 8.2 Models

- binary outcomes：mixed-effects logistic model，fixed effects 为 policy condition、architecture、threat condition、model 及预定义 interactions；task/repository 为 random intercept；
- counts：negative-binomial mixed model；必要时 zero-inflated model；
- time/cost/tokens：log-scale mixed model 或 hierarchical Bayesian regression；
- sparse attack event：exact interval、randomization test 或 hierarchical model；
- taxonomy portability：按 architecture × category 估计 coverage、risk difference 和 uncertainty，不把 annotation label 当作无误差事实。

### 8.3 Effect sizes and uncertainty

所有主要结果报告：risk difference、odds ratio 或 geometric ratio、95% CI、分母、task/repository counts、rollout counts 和 practical-effect threshold。若 model 不收敛或 separation 严重，预先定义 penalized/Bayesian alternative，并保留原始 plan 和 deviation reason。

### 8.4 Multiplicity and exploratory analysis

- primary hypothesis family 使用预先定义的 contrasts；
- secondary outcome family 使用 Holm 或 BH correction；
- failure taxonomy 和 trajectory mechanism 作为 exploratory，除非在 preregistration 中明确为 confirmatory；
- 不使用 observed power；使用 simulation-based precision / sensitivity；
- 不因为 p-value 不理想而切换 task subset、threat definition 或 model。

### 8.5 Robustness

- strict vs broad security oracle；
- excluding setup/solvability failures vs treating them as outcome；
- task-level cluster bootstrap；
- removing one architecture；
- one model vs two-model hierarchical estimates；
- prompt-only baseline vs no-control；
- annotation disagreement sensitivity；
- policy-check latency 与 full episode latency 分解。

## 9. Expected Results、贡献与停止条件

### 9.1 可能结果与解释

#### Result pattern A — Portable direct-security effect

若同一 enforcement 在多个 architecture 上降低 direct authority violation，并保持可接受 utility，且效果不依赖大量 architecture-specific exceptions，则支持 reusable retrofit 的主要 claim。

#### Result pattern B — Portable only for direct events

若 capability layer 能稳定降低 unauthorized action，但 semantic wrong patch / secure-code vulnerability 不变，这是积极且有边界的结果：protocol-solvable taxonomy 得到支持，但不能宣称全面 secure coding。

#### Result pattern C — Architecture-specific effect

若效果方向或 magnitude 依赖 architecture，研究仍有价值：可将“reusable protocol”改写为“portability is conditional on observability/tool semantics”，并报告 adapter burden 和 failure boundary。

#### Result pattern D — Safe failure without utility preservation

若 enforcement 主要造成 false denial、timeout 和 utility collapse，不能把 ASR 下降写成成功；该结果支持 hardened policy 的 cost/safety tension，并可能使题目收敛为 policy boundary study。

#### Result pattern E — No measurable security gain

若 policy layer 不改变 execution evidence，则停止扩大 model/benchmark；先检查 threat model、instrumentation 和 policy coverage。若诊断无误，应否定 reusable runtime retrofit claim。

### 9.2 预期贡献

1. **Portability finding**：同一 runtime policy 在异构 coding-agent architecture 上是否稳定有效。
2. **Failure-boundary finding**：区分 direct authority/provenance risk 与 semantic/model insufficiency。
3. **Measurement protocol**：同时报告 secure success、safe failure、unsafe success、false denial，而不是只报 ASR。
4. **SE implication**：为 middleware developer、coding-agent designer、repository maintainer 和 security reviewer 提供边界性建议。
5. **Artifact**：统一 event schema、policy adapter、task manifest、sandbox、trace 和 analysis pipeline。

### 9.3 Stop/Go criteria

继续 Stage 2 的条件：

- 至少两个 architecture 能通过统一 observability/capability audit；
- direct security event 有明确 execution oracle；
- MVS 中 enforcement 与 no-control 的差异不是纯 policy-induced task failure；
- taxonomy annotator agreement 达到预先定义的可接受标准；
- 一条 run 可以从 task manifest 重放到 patch、audit 和 stats record。

停止或收敛的条件：

- 所有攻击只造成不可区分的全局失败；
- policy 依赖大量 architecture-specific manual exceptions；
- security outcome 只能由 LLM judge 推测；
- 结果只在一个 architecture 或一个 threat payload 上出现；
- adapter 无法观测实际 action 或 provenance。

## 10. Threats to Validity

### Internal validity

- 不同 architecture 的 adapter quality 和 observability 不同；记录 adapter effort、coverage、unsupported events，必要时将其作为 moderator；
- policy enforcement 改变 context、error feedback 和 agent trajectory；将其作为 treatment consequence 测量，不把它隐藏为 implementation detail；
- policy-foreclosed tasks 不是普通 model failure；单独做 solvability check；
- model/API/version drift；锁定 endpoint、container、prompt、seed、价格和日期。

### External validity

- AgentDojo/ASB 结果不能直接外推 repository-level coding；本研究使用 SWE tasks 和 coding-specific adversarial blocks，但仍不能代表所有 organizations；
- 两三个 architecture 不能代表全部 agent ecosystem；论文只声称 sampled architecture family；
- synthetic canary threat 不能给出现实攻击频率；研究目标是 causal mechanism，不是 prevalence estimate；
- open source harness 与 commercial agent 可能不同；commercial validation 只能作为 secondary evidence。

### Construct validity

- “protocol-solvable”可能混合 tool policy 与 model semantic behavior；codebook、trace evidence 和双人标注必须公开；
- `attack success` 不能等同于 model 认为攻击成功；以 side effect/canary/policy evidence 为 primary oracle；
- `utility preservation` 必须包括 secure-and-correct 与 false denial，不只看 task resolved；
- `reusable`必须报告 adapter effort、exceptions、unsupported capability 和 portability confidence。

### Conclusion validity

- rollout nesting、task clustering、model block 和 sparse event 必须进入模型；
- multiple threat class、outcome 和 taxonomy tests 需要 correction；
- null result 需要 CI/precision interpretation，不写成“defense 无效”除非排除了足够大的 effect；
- 所有 post-hoc taxonomy revision、new threat vector 和 secondary model analysis 明确标为 exploratory。

## 11. 安全、伦理与 Artifact Plan

### 11.1 安全实验边界

- 仅使用研究者控制的 disposable repositories 和 local containers；
- fake credentials、canary files、temporary endpoints；
- deny-by-default network 和 allowlist；
- kill switch、CPU/memory/time quotas、automatic reset；
- 不执行真实 credential exfiltration、第三方服务操作、production modification 或横向移动；
- 原始 attack payload 和 trace 访问受限，公开 artifact 采用 redaction/hash。

### 11.2 Artifact components

- `policy_schema.json`、`capability_manifest.json`、`provenance_schema.json`；
- 各 architecture 的 thin adapters 与 coverage report；
- sandbox/container digest、task commits、clean/adversarial manifest；
- prompts、model/API metadata、seeds、timeouts、retry budgets；
- raw/redacted traces、OS audit、policy decisions、test logs；
- taxonomy codebook、annotation data、agreement analysis；
- stats model code、figure/table scripts、price sheet、replay README。

### 11.3 Scientific writing and provenance

每个 literature claim 绑定 source ID；每个 security claim 绑定 execution evidence；每个 taxonomy label 绑定 trace locator 和 annotator decision。将 proposal hypothesis、planned analysis、deviation 和 final result 分开管理。AI 只用于辅助起草和检索，作者必须核验所有 citation、method、claim 和 disclosure。

## 12. 进度安排

| 时间 | 任务 | 交付物 |
|---|---|---|
| 第 1–2 周 | 核验 Tier 1 文献、冻结 threat model、确定两个 harness | evidence matrix、protocol v0 |
| 第 3–4 周 | 实现统一 event schema、capability adapter、audit-only mode | adapter contract、coverage report |
| 第 5 周 | 完成 policy engine、fake canary、sandbox reset | policy prototype、safety checklist |
| 第 6–7 周 | 构造 clean/adversarial tasks，双人编写 taxonomy | task/threat manifest、codebook |
| 第 8 周 | MVS：2 architecture × 2 policy × 24 tasks × 3 rollouts | pilot dataset、oracle audit |
| 第 9–10 周 | reliability audit、solvability check、修订 policy/adapter | frozen analysis plan |
| 第 11–14 周 | Stage 2 confirmation，加入第三 architecture/第二 model | full dataset、replay artifact |
| 第 15–16 周 | stats、figures、threats、artifact evaluation | manuscript draft |

## 13. 参考文献与核验状态

| 论文 | 作者 / 年份 / venue 状态 | 与本课题关系 |
|---|---|---|
| Towards Engineering Multi-Agent LLMs: A Protocol-Driven Approach | Zhenyu Mao et al., 2025, arXiv preprint | SEMAP protocol-driven SE；直接 collision |
| Defeating Prompt Injections by Design | Edoardo Debenedetti et al., 2025, arXiv preprint | CaMeL capability/data-flow defense；generic agent setting |
| AgentArmor: Enforcing Program Analysis on Agent Runtime Trace to Defend Against Prompt Injection | Peiran Wang et al., 2025, arXiv preprint | runtime trace/policy defense；未覆盖本课题 portability |
| The Task Shield | Feiran Jia et al., ACL 2025 | task-alignment defense baseline |
| AgentDojo | Debenedetti et al., NeurIPS 2024 Datasets and Benchmarks | generic agent security benchmark |
| Agent Security Bench | authors listed on official project page, ICLR 2025 project | multi-scenario security benchmark |
| SEC-bench: A Comprehensive Benchmark for Secure Code Generation in Real-World Software Engineering | Hwiwon Lee et al., NeurIPS 2025 | repository-level secure code oracle |
| SecureVibeBench: Benchmarking Secure Vibe Coding of AI Agents via Reconstructing Vulnerability-Introducing Scenarios | Junkai Chen et al., arXiv version; formal venue status requires recheck | secure coding-agent benchmark |
| IssueTrojanBench: Benchmarking AI Coding Agents Against Malicious Issue Requests | Ankur Singh, Jinqiu Yang, Tse-Hsun Chen, 2026, arXiv preprint | coding-agent adversarial issue vector |
| Permission Denied: Policy-Graded Evaluation of Coding Agents in Hardened Environments | Dotan Davidovich et al., 2026, arXiv preprint | policy utility/cost collision |

正式投稿前必须重新打开论文正文、官方 venue 页面和 artifact repository，核对 authorship、version、venue、reported metrics 和 exact experimental setting。若某项无法核验，应在论文中标记 `Not verified`，而不是补全记忆中的信息。
