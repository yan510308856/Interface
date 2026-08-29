# 开题报告一：Interface × Authority 对 Repository-Level Coding Agents 的因果影响

## Working Title

**Interface × Authority: Causal Effects on the Security–Utility–Efficiency Frontier of Repository-Level Coding Agents**

中文题目：**工具接口架构与权限粒度如何共同塑造代码智能体的安全–效用–效率前沿：一项 repository-level coding-agent 控制实验研究**

备选标题：

1. **From Ambient Authority to Scoped Tools: A Controlled Study of Secure Coding-Agent Execution**
2. **When Tool Interfaces and Permissions Interact: An Empirical Study of Repository-Level Coding Agents**

> **研究阶段**：开题报告草案，不包含实验结果。  
> **文献核验边界**：截至 2026-08-20；2026 年 arXiv-only 工作按 preprint 处理。  
> **研究类型**：计算机系统上的 randomized blocked factorial empirical study。  
> **目标投稿风格**：FSE / PACMSE empirical study；若 security contribution 足够强，可考虑 ICSE/安全软件工程交叉方向。

## 摘要

Repository-level coding agents 已经能够读取代码仓库、运行测试、修改多个文件并提交 patch，但它们同时继承了工具调用、未可信输入、权限过宽和执行副作用带来的安全风险。现有工作已经分别研究了 tool architecture 对 coding-agent 行为的影响、严格权限策略的 utility/cost 代价，以及 secure code generation 的安全结果；然而，这些因素通常没有在同一个 capability-matched、execution-grounded 的实验中被拆分。

本研究提出一个 2 × 2 的受控实验：第一因素是 tool-interface architecture（restricted compound-command vs capability-matched typed atomic tools），第二因素是 authorization granularity（ambient/coarse runtime grant vs task-scoped/fine-grained enforcement）。实验在 clean 与 adversarial repository conditions 下运行固定模型、固定 planner、固定任务、固定容器和固定预算，测量 task utility、security behavior、realized security consequence、time 和 cost。[claim:causal] [estimand:main_interaction_contrast] [identification:randomized] [confounding:assessed] [selection:assessed] [collider:assessed] [reverse-causation:assessed]研究重点不是判断某一种工具“总体最好”，而是估计 architecture、authority 及其 interaction 的预注册 treatment contrast，并解释 denial、retry、compound action、observability 和 trajectory 如何与最终的 security–utility–efficiency frontier 联系起来。

预期贡献是一套可复现的 empirical attribution framework：当 coding agent 的成功率、攻击面或成本发生变化时，研究者和工具设计者可以判断问题更可能来自接口 representation、权限边界，还是模型/任务本身。研究不预设某个 treatment 必然优越；若实验只发现单一主效应、没有 interaction，或表面安全收益完全来自 policy-induced failure，论文将如实收敛为 policy-grading 或 interface study，而不继续声称存在更强的 frontier 结论。

## 1. 研究背景与问题定义

### 1.1 软件工程背景

与一次性 code completion 不同，repository-level coding agent 通常需要：

- 定位相关文件与调用链；
- 读取 issue、README、测试、依赖和工具输出；
- 修改多个文件并保持项目状态一致；
- 运行测试、构建、静态检查或调试命令；
- 处理失败、重试、回滚和最终 patch 验证。

因此，agent 的表现不只取决于语言模型本身，也取决于模型看到的工具如何组织、每次 action 的粒度、执行环境的可见性以及 agent 获得的 authority。

### 1.2 核心问题

当前实践经常同时改变以下组件：

1. 把 Bash 换成 atomic tools、MCP 或 CodeAct；
2. 把完整文件系统权限换成路径级 allowlist；
3. 开启网络限制、非 root、只读文件系统或 sandbox；
4. 更换 agent scaffold、prompt、planner 或 model。

当最终 success、token cost 或 unsafe action 发生变化时，很难知道变化来自哪个因素。这是一个 software-engineering design attribution problem，而不只是 benchmark ranking problem。

### 1.3 本研究中的 X–Y–Z 句子

> **We study whether and how capability-matched tool-interface architectures and privilege granularity causally affect task utility, execution security, and resource efficiency of repository-level coding agents, and whether their effects interact under clean versus adversarial repository conditions.**

对应中文：

> 我们研究在模型、任务、工具能力和执行预算固定时，工具接口架构与权限粒度是否以及如何因果地影响 repository-level coding agent 的任务效用、执行安全和资源效率，并检验这种影响是否会随 clean/adversarial repository condition 发生 interaction。

### 1.4 核心概念：本研究到底修改哪一层？

本研究必须把五个容易混淆的层次分开，否则所谓 `interface × privilege` 仍然只是两个产品配置的比较。

| 层次 | 本研究中的含义 | 是否作为 treatment | 固定或记录方式 |
|---|---|---:|---|
| Model / actor | 生成下一步 action 的模型与 reason–act loop | 否；作为 block/replication factor | 固定 model version、prompt、temperature、step budget |
| Capability | 一个 episode 最终能够完成的 primitive operation 集合，例如读文件、精确替换、运行测试 | 否 | 两种 interface 共用同一 backend primitive library，并做 differential audit |
| Interface architecture | capability 如何被组织、命名、参数化，以及一次 action 后何时返回 observation | **是，因素 A** | compound command vs typed atomic call |
| Normative authorization policy | 对当前 task 而言，哪些主体可对哪些对象执行哪些操作 | 否；它是统一的评分 oracle | 每个 task 一份不可被 agent 修改的 `P*` manifest |
| Enforced runtime authority | 环境实际授予 agent 的权限是否与 `P*` 同样细，还是粗粒度地整体授予 | **是，因素 B** | ambient grant vs task-scoped enforcement |

其中最重要的区别是：**capability 回答“系统理论上会做什么”，interface 回答“这些能力如何呈现给模型”，authority 回答“这一次运行实际允许对哪个对象做什么”。** `P*` 在所有实验 cell 中保持不变；改变的是 runtime 是否执行这份细粒度 policy。这样，ambient 条件下“运行成功但越出 `P*`”的操作仍可被统一 oracle 判为越权，而不会因为环境恰好允许就被误记为安全。

这里的 `security` 也不是一个无对象的总称。本研究主要研究的是：**在隔离执行环境内，benchmark repository 的完整性、synthetic secret/canary 的机密性、进程与网络边界的完整性，以及 agent 在未可信 repository 内容影响下仍遵守 task authorization 的能力。** 它不直接代表模型权重安全、训练数据安全、真实生产系统安全，也不等同于 agent 最终生成代码不存在漏洞；后者只在 secure-code extension 中单独测量。

## 2. 文献基础与 Research Gap

### 2.1 研究链条

#### Agent-computer interface

[SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)（John Yang et al., NeurIPS 2024）把 agent-computer interface 作为自动化软件工程的重要设计层；[OpenHands](https://arxiv.org/abs/2407.16741)（Xingyao Wang et al., ICLR 2025）进一步提供了开放的 generalist software-agent platform。它们为本研究提供 agent harness 和 repository-task 语境，但没有把 authority 与 execution security 作为可分离的实验因素。

#### Tool architecture

[The Devil Is in the Interface: Evaluating How Tool Architecture Shapes Coding Agent Behavior](https://arxiv.org/abs/2608.11386)（Xiangzhe Xu et al., COLM 2026）在 underlying information/actions 尽量相近时比较六种 tool architecture、三个 actor 和 11,700 条 trajectory，报告 interface organization 会改变 consistency、exploration、steps 和 token usage。其 `BashOnly` 只暴露通用 shell，`Atomic` 则在 Bash 之外增加 repository search、bounded view、targeted replacement 和 file creation 等显式工具；作者明确将后者解释为对常用 shell action 的重新包装，而不是新增 capability。这是本研究必须正面回应的最近 collision：本研究不能再声称“第一次发现 tool architecture 影响 coding-agent performance”。同时，该研究的 Atomic 并没有移除 Bash，因此不是本提案二选一 treatment 的直接实现模板；它也没有把 privilege granularity、adversarial repository execution 和 unauthorized side effect 纳入同一 factorial study。

#### Scaffolding / MCP / CLI

[The Scaffolding Matters More Than the Interface: A Controlled Comparison of MCP and CLI Tool Use Across Seven Agent Scaffoldings, Five Language Models, and One Software Task](https://arxiv.org/abs/2608.08654)（Marc Alier Forment et al., 2026, arXiv preprint）报告 scaffold、成本和 interface comparison 可能被 agent 是否实际使用指定接口所混淆，并强调需要验证 repository state 而非相信 agent 自报。本研究吸收其两个设计教训：验证 actual tool behavior，并将 scaffold 固定或作为明确 block；但本研究使用多 repository tasks 和 execution-security outcome，不做单任务 MCP-vs-CLI 复现。

#### Authority hardening

[Permission Denied: Policy-Graded Evaluation of Coding Agents in Hardened Environments](https://arxiv.org/abs/2608.02670)（Dotan Davidovich et al., 2026, arXiv preprint）在 Terminal-Bench 2.1 上比较 root/unrestricted/writable control、仅 non-root，以及同时采用 egress allowlist、受保护路径只读和 privilege lockdown 的 `NIST-derived high`。该研究报告 hardening 会改变 success、timeout、trajectory 和 cost，并用 solvability witness 区分“agent 没做好”与“policy 使任务本身不可完成”。作者同时明确说明最高强度 level 一次改变多个轴，只能解释为 whole-configuration effect。这直接说明权限不是“免费安全开关”，也提醒本研究不能把多种 hardening controls 捆成一个处理后再声称是 privilege-granularity 单一因果效应。

#### Secure coding-agent evaluation

[SEC-bench](https://proceedings.neurips.cc/paper_files/paper/2025/hash/a9168f1c54e5147027f1e8cf83e1a775-Abstract-Conference.html)（Hwiwon Lee et al., NeurIPS 2025）和 [SecureVibeBench: Benchmarking Secure Vibe Coding of AI Agents via Reconstructing Vulnerability-Introducing Scenarios](https://aclanthology.org/2026.acl-long.1107/)（Junkai Chen et al., ACL 2026）说明 repository-level code agent 的 functional correctness 与 generated-code security 必须分开测量。SecureVibeBench 进一步用 functional tests 与 static/dynamic security oracles 联合评价 C/C++ repository tasks。它们提供 patch-security benchmark/oracle 语境，但没有将 tool architecture 和 authorization granularity 作为 treatment，也不测 agent 运行过程是否越出权限边界。

#### Adversarial delivery vector

[IssueTrojanBench: Benchmarking AI Coding Agents Against Malicious Issue Requests](https://arxiv.org/abs/2607.20759)（Ankur Singh, Jinqiu Yang, Tse-Hsun Chen, 2026, arXiv preprint）把恶意指令放入 coding-agent 可能读取的 issue/repository delivery vectors，并评估现代 coding agents。它适合用于 threat-condition 设计，但其 attack success 结果本身不能回答 authority/interface 的 causal attribution。

### 2.2 已知与未知

#### 已知什么？

现有证据支持以下较窄的结论：

1. tool/interface organization 可以改变 coding-agent 的行为轨迹和资源消耗；
2. scaffold 与实际 tool-use behavior 可能比表面协议名称更重要；
3. restrictive policy 会造成 utility、timeout 或 cost trade-off；
4. repository-level functional success 不能替代 security outcome；
5. issue/repository/tool metadata 可能成为 coding-agent 的攻击入口。

更具体地说，文献能为本研究提供的是“设计与测量先例”，而不是本研究假设的答案：

| 文献 | 已有证据实际说明什么 | 不能据此推出什么 | 本研究吸收的设计决定 |
|---|---|---|---|
| SWE-agent；The Devil Is in the Interface | 能力的组织与呈现会影响 repository navigation、consistency、exploration、step/token efficiency | structured tool 天然更安全，或 atomic 在所有模型上更优 | capability-matched backend；记录实际 tool use、context footprint 与 compound action |
| Permission Denied | native runtime hardening 会造成不均匀的成功率、超时与成本变化；必须验证 strict policy 下 task solvability | 某一个权限轴单独导致全部变化，或 hardening 一定改善 attack security | 只操纵一项 task-scoping 维度；root、network baseline 等保持恒定；建立 solvability witness |
| AgentDojo；ASB | ASR 必须和 benign utility、refusal/false positive 一起报告 | ASR 下降就等于系统整体更安全 | 同时报 attack-goal completion、safe success、false denial 和 clean utility |
| RedCode；Execution-Grounded Security Testing | code agent 的风险需要用 Docker/runtime trace/file diff 等 execution evidence 验证 | 文本拒绝或 LLM judge 能代替实际 side-effect oracle | primary security label 只接受 policy log、filesystem/process/network trace 或 canary oracle |
| SEC-bench；SecureVibeBench | functional correctness 与 generated-code security 可能分离 | patch 无漏洞就代表 agent 执行过程没有越权，或反之 | generated-code vulnerability 作为独立 extension outcome，不与 execution security 合并 |
| IssueTrojanBench | malicious issue/repository artifact 是现实相关的 delivery vector，现有 coding agents 可能执行其中的攻击目标 | 其总体 ASR 能识别 interface 或 authority 的因果作用 | 构造 clean/adversarial paired task，并在四个 treatment cell 中重复同一攻击目标 |

#### 未知什么？

截至本次检索边界，尚未定位到一个同时满足以下条件的研究：

- 独立操纵 tool-interface architecture 与 privilege granularity；
- 保持 underlying operations、model、prompt、task、timeout、retry 和 scaffold capability-matched；
- 在同一 repository task 的 clean/adversarial paired conditions 下运行；
- 用真实文件、网络、进程、canary 和 policy event 记录 execution security；
- 同时估计 utility、security、time、tokens、tool calls、retries 和 monetary cost；
- 用 task/repository-aware statistical model 识别 interaction，而不是简单比较 aggregate leaderboard。

#### Gap 为什么有价值？

这不是“没有人比较过 A 和 B”的弱 gap。它影响 coding-agent system design 的实际决策：

- 如果安全收益主要来自 privilege，而不是 interface，开发者应优先做 capability boundary；
- 如果 interface × privilege 存在 interaction，单独优化 tool schema 或单独收紧权限可能产生误导；
- 如果所谓安全收益只表现为 safe failure / false denial，系统不能被称为“更安全且保持 utility”；
- 如果风险主要是 semantic wrong patch 或 authorized-but-dangerous action，runtime policy 不能替代 secure coding、review 和 model-level alignment。

### 2.3 Novelty collision 与应对策略

| 可能杀死本课题的工作 | 被杀死的版本 | 本课题必须保留的差异 |
|---|---|---|
| The Devil Is in the Interface | 只比较不同 tool architectures 的 success / token / consistency | 加入 independent authority factor、adversarial execution 和 security event |
| The Scaffolding Matters More Than the Interface | 单任务 MCP vs CLI 成本比较 | 多 repo、paired task、actual-tool-use audit、authorization-policy manifest |
| Permission Denied | 只复现 policy hardening 的 success/cost loss | 估计 architecture × privilege interaction，并使用 repository-level coding tasks |
| SEC-bench / SecureVibeBench | 再造一个 secure-code benchmark | 使用已有或透明派生 benchmark，研究 interface/authority 的原因 |
| IssueTrojanBench | 只报告 modern coding agent 的 attack success | 测量不同 authority/interface 条件下 attack success 与 unsafe side effect 的改变 |

因此，本研究的 novelty statement 应写成：

> **The contribution is a capability-matched causal decomposition of tool-interface architecture and privilege granularity on repository-level coding-agent security, utility, and efficiency—not a new coding-agent framework, a new benchmark, or a generic prompt-injection defense.**

## 3. 研究目标、边界与可证伪性

### 3.1 总目标

建立一个可复现的 2 × 2 controlled empirical study，回答 interface architecture 与 authority granularity 是否产生独立 effect、interaction effect，以及这些 effect 通过哪些可观测 trajectory mechanism 传递到 security–utility–efficiency frontier。

### 3.2 非目标

本研究不试图：

- 训练一个新 LLM 或提出新的 coding-agent architecture；
- 设计一个生产级安全产品；
- 宣称某种 interface 在所有 model/task 上 universally better；
- 仅依赖 LLM-as-judge 判定 security；
- 在真实第三方系统、生产仓库或真实 secret 上执行攻击；
- 同时研究 multi-agent propagation、MCP transport、long-horizon evolution 和所有模型。

这些内容可作为后续工作，不进入 MVP 的主要 estimand。

### 3.3 研究单位与因果 estimand

#### 主要实验单位

- **Task attempt**：一个 frozen repository task 在一个 treatment、一个 model、一个 seed 下的一次完整 agent episode。
- **独立重复单位**：task/repository block；rollout 是同一 task 的 repeated observation，不能直接当作独立 task。
- **Security event unit**：每个 attempt 是否至少发生一次预定义 unsafe/unauthorized execution event；同时保留 event count 作为 secondary outcome。

#### 主要 estimands

1. **Architecture main effect**：在 privilege、condition、model 和 task distribution 固定下，atomic 与 compound interface 的平均 utility/security/efficiency contrast。
2. **Privilege main effect**：在 interface、condition、model 和 task distribution 固定下，scoped 与 ambient authority 的平均 contrast。
3. **Interaction effect**：
   
   \[
   \Delta_{interaction} = (Y_{atomic,scoped}-Y_{compound,scoped})-(Y_{atomic,ambient}-Y_{compound,ambient})
   \]

   对 binary outcomes 使用 risk difference / odds ratio，对 time/token/cost 使用 log-scale difference。
4. **Condition moderation**：clean 与 adversarial condition 是否改变 architecture、privilege 或 interaction effect。

### 3.4 Rival explanations

| Rival explanation | 可能观察到的模式 | 区分方法 |
|---|---|---|
| Capability mismatch | 某接口功能更强，utility/security 同时改善 | capability manifest、differential test、禁止不等价条件进入 primary analysis |
| Context-footprint effect | schema 文本长度或 error message 改变 model behavior | 记录 schema/error tokens；做 context-matched sensitivity analysis |
| Scaffold implementation quality | 结果来自 adapter bug，而非 architecture | 同一 core loop、统一 adapter tests、cross-over runs、记录 adapter coverage |
| Task difficulty confounding | adversarial tasks 本来更难 | clean/adversarial paired variants、task block、difficulty annotation |
| Model stochasticity | effect 只来自随机 rollout | 固定 seed、重复 rollout、hierarchical model、独立 confirmation model |
| Safe refusal masquerading as security | attack rate 下降但 all-task utility 也崩溃 | safe success / safe failure / true/false denial / unsafe success joint outcomes |
| Measurement blind spot | 未记录的 side effect 被误判为 safe | OS audit、filesystem/network/process instrumentation、canary controls |

## 4. Research Questions 与 Hypotheses

### RQ1 — Utility effect

在 underlying operations、model、prompt、task 和 budget 固定时，tool architecture 与 privilege granularity 对 clean repository task success、test pass、patch correctness 和 repeated-run consistency 的 main effect 与 interaction effect 是什么？

### RQ2 — Security effect

在 issue、README、repository file 或 tool metadata 含有 adversarial content 时，tool architecture 与 privilege granularity 如何影响 prompt-injection success、unauthorized operation、unsafe side effect、persistence 和 canary access？

### RQ3 — Frontier and trade-off

不同 design point 的 security gain 是否以 measurable utility、wall-clock、tokens、tool calls、retries 和 monetary cost 为代价？哪些 design point 位于 practical security–utility–efficiency Pareto frontier？

### RQ4 — Mechanism

action granularity、compound command、observability、reversibility、denial feedback、context footprint、exploration diversity 和 retry/trajectory characteristics 哪些解释 RQ1–RQ3 的差异？

### 假设

以下为预注册前的 candidate hypotheses，不是既有证据已经证明的结果：

- **H1（utility heterogeneity）**：architecture 对 clean-task utility 的 effect 依赖 task difficulty 和 model；不存在对所有 task/model 都成立的 universal winner。
- **H2（authority security）**：scoped privilege 相比 ambient privilege 降低 unauthorized side-effect rate 和 attack success，但可能增加 denial、retry、time 和 cost。
- **H3（interaction）**：在 adversarial condition 下，architecture × privilege interaction 不等于 0；atomic observability 与 scoped authority 可能产生超出 additive main effects 的安全变化。
- **H4（mechanism）**：部分 efficiency cost 由 denials、retries、compound action 和 trajectory length 解释；该假设只在预设时间顺序和模型假设支持时作 exploratory mediation interpretation。

### 预先定义的不可支持模式

以下结果会削弱或否定对应主张：

- 若 capability audit 失败，不能支持 architecture causal claim；
- 若 scoped policy 只让所有任务更少完成，却不减少 `out_of_policy_attempt`，则不能支持 agent behavioral security improvement；其 realized-effect 变化只能解释为 enforcement effect；
- 若 interaction CI 极宽且跨 model/task 方向不一致，只能报告不确定性，不能宣称 interaction；
- 若安全指标只在 judge label 上改善、但 execution audit 不改善，不能支持 execution-security claim；
- 若 effect 只在一个 adapter 或单一 task 出现，只能视为 pilot signal。

## 5. 实验设计

### 5.1 总体设计

本研究采用 **randomized blocked 2 × 2 factorial repeated-rollout design**：

| Factor | Level 1 | Level 2 |
|---|---|---|
| Tool-interface architecture | restricted compound-command | capability-matched typed atomic tools |
| Authorization granularity | ambient/coarse runtime grant | task-scoped/fine-grained enforcement |
| Repository condition | clean | adversarial paired variant |

`Repository condition` 是 threat/context factor，不与 architecture/privilege 混为同一个 security treatment。若后续加入 MCP，它将作为 Stage 3 的第三个 interface level，而不是在 MVP 中把“协议”和“权限”同时改变。

### 5.2 Interface 的操作性定义

Interface treatment 只改变**模型可见的 action language、参数 schema、组合边界和 observation cadence**，不改变 backend evaluator、OS policy、可访问 task information 或 episode-level primitive capability。为了避免把“裸 Bash 的额外能力”误当成 architecture effect，MVP 不使用宿主机的 unrestricted shell；两种 interface 都调用同一个受控 backend。

#### Treatment A0 — Restricted compound-command interface

模型只看到一个 `terminal` tool：

```text
terminal(script: string, cwd: repo_relative_path) ->
  {stdout, stderr, exit_code, state_delta_summary, policy_events}
```

- `script` 可在一次 tool call 中顺序或条件组合多个已注册 primitive，例如 `search → view → test`；
- backend 解析 command AST，只允许 capability manifest 中的 executable、arguments、pipes 和 repo-relative redirection；拒绝 command substitution、动态下载执行、后台 daemon、未注册 interpreter 和越出 sandbox 的路径；
- 一次 compound call 完成后才向模型返回聚合 observation，因此模型可以用较少 step 表达多个操作，但中间结果的可见性与可纠错点较少；
- 审计器仍按 primitive 和 syscall 拆分记录，不能只保存整段 command string。
- compound 内按顺序执行；某个 primitive 被拒绝或失败时停止剩余 script，不自动回滚此前已经完成的 side effect。该语义在所有 run 中冻结并记录。

这个 treatment 研究的是**组合式 action representation 与粗 observation boundary**，不是“给 agent 一个真正无限的 Bash”。若实现最终必须暴露额外 shell 语义，则论文必须把因素名称降级为 `restricted compound shell configuration`，并在 capability audit 中列出不等价项。

#### Treatment A1 — Typed atomic-tool interface

模型不能调用通用 shell，只看到一组 typed tools：

```text
list_tree(sandbox_relative_path, depth)
search_text(query, sandbox_relative_path, file_glob, max_results)
read_file(sandbox_relative_path, start_line, end_line)
replace_text(sandbox_relative_path, old_text, new_text, expected_matches)
create_file(sandbox_relative_path, content)
delete_path(sandbox_relative_path, expected_type)
run_command(program, argv, cwd, timeout)  # shell=False
git_status()
git_diff(path?)
```

- 每次 call 只执行一个 primitive，参数在执行前完成 schema、path canonicalization 和 policy check；
- `run_command` 只允许 manifest 中的 test/build/lint executable 与 argument template，不提供 `shell=True`、pipe、redirection 或 command chaining；
- 每个 action 都立即返回局部 observation、policy decision、latency 和 state delta；
- 多步目标必须由模型通过多次 tool calls 显式完成。

这个 treatment 研究的是**typed parameterization、细 action boundary 与逐步 feedback**。它不是一种 defense：在 ambient authority 下，typed tool 仍可能被模型用于读取不相关文件或写入错误位置。

#### Interface 因素实际改变与不改变的内容

| 维度 | A0 compound | A1 atomic | 因果解释 |
|---|---|---|---|
| 模型可见工具数 | 1 个 `terminal` | 多个 typed tools | architecture treatment |
| 一次 action 可包含的 primitive 数 | 多个 | 1 个 | architecture treatment |
| 参数表示 | command text / AST | JSON-like typed fields | architecture treatment |
| observation 时机 | compound call 结束后 | 每个 primitive 后 | architecture treatment |
| policy enforcement | 同一 `P*` / runtime engine | 同一 `P*` / runtime engine | 保持不变 |
| backend primitive / final state reachability | 与 A1 episode-level 对齐 | 与 A0 episode-level 对齐 | 保持不变并审计 |
| model、prompt、task、budget、container | 相同 | 相同 | 保持不变 |

#### Capability equivalence contract

两个 interface 必须通过相同的 operation matrix：

| Capability | Compound | Atomic | Primary audit |
|---|---:|---:|---|
| 读取 repository 文件 | yes | yes | path allowlist + audit |
| 写入 repository 文件 | yes | yes | path allowlist + diff |
| 搜索文件和文本 | yes | yes | query/path log |
| 运行测试 | yes；可在 compound script 中调用 | yes；`run_command` | command/test log |
| 运行 build/lint | yes；可在 compound script 中调用 | yes；`run_command` | process log |
| 读取 git 状态/diff | yes | yes | git log |
| 任意 network | no by default | no by default | egress audit |
| 真实 credential | never | never | fake secret/canary only |
| disposable sandbox 内、repository 外对象 | backend 可表达；由 authority condition 决定 allow/deny | backend 可表达；由 authority condition 决定 allow/deny | 相同 `P*` + filesystem audit |

这里的 equivalence 是 **episode-level reachability equivalence**，不是要求相同 tool-call 数：对预先定义的 benign operation suite，两种 interface 应能从同一初始状态到达相同 repository state、test result 和 git diff。审计至少覆盖单步读写、组合搜索、失败后的恢复、路径 canonicalization、argument quoting、timeout 和相同的 allow/deny 决策。若某个 interface 的能力无法对齐，研究报告必须把该比较降级为 configuration comparison，而不能解释为 architecture-level treatment effect。

### 5.3 Privilege 的操作性定义

Privilege 不用“工具多少”来定义，而用 authorization tuple 表示：

```text
(subject, operation, object, constraints)
```

- `subject`：本次 run 的 agent identity / process tree；
- `operation`：`read`、`create`、`modify`、`delete`、`execute`、`connect`、`spawn`；
- `object`：canonical path、command、process class、network endpoint、synthetic secret；
- `constraints`：task_id、cwd、argument template、time limit、call count、生命周期与 provenance。

每个 task 在运行前生成一份冻结的 normative policy `P*`。例如，一个修改 `src/parser.py` 并运行 parser tests 的 task 可以具有：repository source/test 的 read、`src/parser.py` 与指定 test file 的 write、`pytest tests/test_parser.py` 的 execute、run-specific `/tmp/<run_id>` 的 read/write，以及 network deny。canary、其他 task workspace、宿主路径和持久化位置永远不属于 `P*`。

#### Treatment B0 — Ambient/coarse runtime grant

- runtime 向 agent process tree 粗粒度授予整个 disposable workspace 的 read/write，以及 capability manifest 内全部 command 的 execute；
- network、真实 credential、宿主机与 container escape 在所有 cell 中仍然 deny，避免把研究变成危险的“无 sandbox”实验；
- `P*` 仅以 audit mode 运行：越出 `P*` 的操作会被记录为 `would_deny`，但只要仍在 ambient sandbox grant 内就允许完成；
- 因此，ambient 不是“没有规范”，而是**规范比实际 runtime grant 更细**。这使研究能够观察被过宽权限放大的副作用。

#### Treatment B1 — Task-scoped/fine-grained runtime grant

- runtime 实际执行同一份 `P*`：只有 policy tuple 精确匹配的 action 才执行；
- path 必须 canonicalize 后匹配，避免 `..`、symlink、hardlink 或 alternate path 绕过；子进程继承相同或更窄的 policy；
- 超出 scope 的 action 在 backend/OS 层被拒绝，并返回跨 interface 语义一致的 `DENIED(reason_code, policy_rule_id)`；
- policy 不是根据 agent 临时请求自动放宽；实验内不加入人工 approval，以免引入不同的人类交互 treatment。

#### 粒度究竟细到哪里？

MVP 采用 **task × operation × object** 粒度，而不是 syscall-level 每次动态授权，也不是只做 container-wide root/non-root：

| Authority axis | Ambient B0 | Scoped B1 | MVP 中是否变化 |
|---|---|---|---:|
| Repository read | 整个 task workspace | `P*` 声明的 repo tree；默认 source/test 可读 | yes |
| Repository write/delete | 整个 task workspace | 允许修改的 path set；必要生成文件单列 | yes |
| Test/build execution | manifest 内全部命令 | task-specific program + argv template | yes |
| Temporary files | 共享 run workspace | 仅 `/tmp/<run_id>` | yes |
| Synthetic canary | ambient sandbox 可访问、但不在 `P*`，用于检测越权 | policy deny | yes，作为 confidentiality oracle |
| Network egress | deny-by-default，仅 loopback oracle | 完全相同 | **no，固定** |
| Root / Linux capabilities | non-root、无 sudo、无额外 capability | 完全相同 | **no，固定** |
| Host/production credentials | never present | never present | **no，固定** |

因此，本研究的因素 B 更准确地叫 **authorization granularity / task-scoped authority**，不是一般意义上把 network、filesystem、credential 和 root hardening 全部打包的“高/低安全模式”。若 Stage 3 想研究 network、root 或 credential scope，必须把它们作为新的独立 factor/ablation，而不是悄悄加入 B1。

#### 四个 treatment cell 分别改变什么？

| Cell | 模型如何表达 action | runtime 如何授权 | 主要可观察机制 |
|---|---|---|---|
| A0B0 compound × ambient | 一次可组合多个 primitive | workspace-wide coarse grant；`P*` 只审计 | compound 中是否隐藏/放大越权副作用 |
| A1B0 atomic × ambient | 一次一个 typed primitive | 同一 coarse grant；`P*` 只审计 | 更细 observation 是否改变不安全 action proposal |
| A0B1 compound × scoped | compound AST 中每个 primitive 都按 `P*` enforcement | task-specific fine grant | 部分执行、denial 后重试与 workaround |
| A1B1 atomic × scoped | 每个 typed call 执行前按 `P*` enforcement | 同一 task-specific fine grant | 精确 denial feedback、恢复与 false denial |

`Audit-only` 不再作为第五个模糊 condition：它就是 B0 中 `P*` 的运行模式。另可在固定回放 trace 上做 policy-engine microbenchmark，以估计纯 policy-check latency，但该结果不与 agent behavioral effect 混合。

### 5.4 任务与 benchmark

#### Clean task set

优先使用 SWE-bench Verified 中具备稳定测试、清晰 repository commit 和可重放 environment 的 task。按 repository、语言、任务难度和测试规模分层，避免同一项目的相似 task 过度代表某个 repository。

#### Adversarial task set

两条路线二选一或组合：

1. 使用 IssueTrojanBench 中适合 isolated repository harness 的 delivery vector；
2. 从 clean task 的 frozen copy 构造 paired issue/README/file injection，并由独立 red-team reviewer 验证 attack trigger、benign readability 和 no-real-damage property。

adversarial variant 不应改变需要修复的 functional requirement；攻击内容是额外的 untrusted instruction 或 tool/data artifact。若无法做到语义配对，必须将其作为 separate threat benchmark，不声称 paired causal attack effect。

#### Secure-code extension

SecureVibeBench 或 SEC-bench 仅作为 extension，用于 secure-and-correct 与 vulnerability-introduction outcome；不把它们与普通 issue-resolution 的 `resolved-with-tests` 合成一个未经定义的总分。

### 5.5 Agent、model 与控制变量

主实验固定一个 agent core loop，只替换 tool adapter 与 policy engine。正式 confirmation 版加入：

- 一个 frozen open coding model；
- 一个 frontier/API coding model；
- 同一 system prompt、task prompt、temperature、max steps、timeout、retry budget、test runner、container image 和 log schema。

模型不是主要 treatment，而是 replication/block factor。不要把 SWE-agent、OpenHands、Claude Code 等完整 product framework 同时作为 treatment，否则 architecture、scaffold、prompt 和 model 会重新混淆。

### 5.6 实验阶段与规模

#### Stage 0 — Harness and capability audit

在任何 outcome collection 前运行 differential tests：相同 primitive operation 在两个 interface 上产生等价 repository state、tests、git diff 和 denial behavior。保存 audit report；fail closed。

#### Stage 1 — Minimum Viable Study

- 12 个 clean tasks；
- 12 个 paired adversarial tasks；
- 2 个 interface × 2 个 privilege level；
- 1 个 frozen open model；
- 每个 cell 3 次 rollout；
- 预计 288 个 task attempts（12 + 12 个 task instance × 4 cells × 3 rollouts）；
- 主要目标：检查 outcome 可测、security oracle 可用、interaction 是否有可估计信号。

#### Stage 2 — Confirmation study

- 24–40 clean tasks + paired adversarial tasks；
- 2 个 model；
- 每个 cell 5 次 rollout；
- 以 repository/task difficulty/language 分层；
- 在预注册后冻结 exclusion rules 和 primary contrasts。

#### Stage 3 — External validity

只有 Stage 2 的 primary effect 方向可复现时，才加入：

- 第三种 structured/MCP interface；
- 第二个 open agent harness；
- SecureVibeBench/SEC-bench secure-code task；
- long-horizon SWE-EVO task。

这些不是“越多越好”的扩展；每次扩展都必须回答一个明确的 transportability question。

### 5.7 Randomization、blocking 与 replication

- 按 repository、语言、难度和 task family 建 block；
- treatment order、task order 和 rollout seed 使用预先生成的 seeded randomization；
- clean/adversarial pair 在相同 task block 内配对；
- 每个 task 在各 treatment cell 重复，防止某个任务只出现在一个条件；
- 将 task/repository 作为主要独立结构，将 rollout 作为 nested repeated observation；
- 发生 model/API failure、timeout 或 policy refusal 时不静默丢弃，而按预先规则编码为 outcome。

### 5.8 Security instrumentation 与安全边界

所有 adversarial runs 仅在 disposable sandbox 中执行：

- no production credentials；
- fake secret 与 canary files；
- deny-by-default network，只有必要的 allowlist endpoint；
- disposable repository copy 和 kill switch；
- OS/process/filesystem/network audit；
- 每次 run 自动 reset，禁止对第三方或真实 production system 发起攻击。

primary security labels 必须由 execution trace / policy log / canary oracle 证明；LLM judge 只作为 secondary annotation。

为了避免 scoped 条件“因为所有越权都被内核挡住，所以安全率天然为 100%”这种循环定义，所有 cell 都使用同一个 `P*` 评分，并分别记录四个阶段：

1. **unsafe proposal / attempt**：模型是否提出或发起超出 `P*` 的 action；
2. **policy intervention**：该 action 是 allow、would-deny 还是 enforce-deny；
3. **realized side effect**：文件、进程、网络或 canary 状态是否真的改变/泄露；
4. **attacker objective completion**：预注册攻击目标是否最终达成，包括通过另一路径绕过 policy。

这样，`B1` 对 realized violation 的降低可以被识别为 enforcement effectiveness，而 attempt rate、retry/workaround、utility 和 interface interaction 才反映 agent behavior 与 policy usability。若只报告第 3 项，会高估一条机械阻断规则的科研含义；若只报告第 1 项，又会忽略 sandbox 已经成功阻止危害。

## 6. 变量与测量方案

### 6.1 Primary outcomes

| Outcome family | Primary variable | Operational definition | Unit |
|---|---|---|---|
| Utility | resolved-with-tests | patch applied，required tests pass，且无预定义 regression | task attempt |
| Security behavior | out-of-policy attempt | 至少一次 action 在 canonicalize 后不匹配统一的 `P*`，无论它最终是否被阻止 | task attempt |
| Security consequence | realized unsafe side effect | 至少一次越出 `P*` 的 read/write/delete/execute/connect 实际完成，或预定义 canary/攻击目标 oracle 被触发 | task attempt |
| Time | wall-clock | agent episode 从首个 model request 到终止的 elapsed time | seconds/attempt |
| Cost | LLM monetary cost | input/output token × frozen price sheet + declared service/tool cost | USD/attempt |

其中 `realized unsafe side effect` 是 primary end-to-end security outcome，`out-of-policy attempt` 是解释“agent 是否仍试图越权”的共同 primary behavioral outcome。两者必须并列，不能将 policy denial 本身记作 security failure，也不能把没有实际 side effect 的恶意文本输出记作已攻破系统。

#### “安全”具体保护什么？

| Security property | Protected asset | Violation oracle | 本研究中的地位 |
|---|---|---|---|
| Authorization integrity | task-defined `P*` boundary | policy log + canonical action tuple | primary |
| Repository integrity | 非 task 目标文件、git hooks、CI/config、其他 workspace | pre/post hash、git diff、filesystem audit | primary when in threat manifest |
| Confidentiality | synthetic secret/canary file/token | canary read or egress sink hit | primary when in threat manifest |
| Process/environment integrity | unauthorized child process、persistence location、privileged operation | process tree、syscall/OS audit、restart probe | primary when in threat manifest |
| Attack robustness | adversarial issue/file 中的预注册 attacker goal | goal-specific deterministic oracle | primary in adversarial tasks |
| Generated-code security | patch 是否引入/保留具体 vulnerability | exploit/security tests/static oracle | extension；不与 execution security 合并 |
| Availability / benign usability | clean task 是否因 false denial、timeout、refusal 失败 | task oracle + denial trace | utility trade-off，不称为攻击安全 |

### 6.2 Secondary outcomes

- test pass rate、build status、patch correctness、regression；
- attack-goal completion、attempted/blocked/realized unauthorized read/write/network/process、persistence、canary access；
- safe success、safe failure、unsafe success、unsafe failure、true denial、false denial；
- input/output tokens、LLM requests、tool calls、turns、denials、retries；
- repeated-run consistency / pass^k；
- tool schema token footprint、error-feedback length、policy-check latency；
- exploration diversity、file coverage、trajectory length、compound action count。

attempt-level joint taxonomy 以两个独立二元轴为基础：`task_success` 与 `realized_unsafe_effect`。由此得到 safe success、safe failure、unsafe success、unsafe failure。`False denial` 只在 action 属于 `P*` 却被 enforcement 错误拒绝时成立；agent 因拒绝一个真正越权 action 而最终任务失败，属于 policy-induced failure，但不是 false denial。`Safe failure` 也不是安全收益本身，它只说明未造成已测危害，需要与任务失败原因一起解释。

### 6.3 数据记录 schema

每一条 run 至少包含：

```text
run_id, task_id, repository_id, repository_commit, condition,
interface_level, privilege_level, model_id, agent_commit,
prompt_hash, policy_manifest_hash, capability_manifest_hash,
seed, start_time, end_time, timeout,
success, tests_passed, regression_flag,
out_of_policy_attempt, realized_unsafe_effect, attacker_goal_completed,
subject, operation, canonical_object, constraint_match,
policy_decision, policy_rule_id, event_type, event_path_or_target,
denial_count, true_denial_count, false_denial_count, retry_count,
tool_calls, turns, input_tokens, output_tokens,
compound_primitive_count, state_delta_hash,
llm_cost, container_digest, evaluator_version, oracle_version
```

raw prompt、tool trace 和 adversarial payload 需要做访问控制；公开 artifact 只发布必要的 redacted version 和 hash。

## 7. 统计分析与判定规则

### 7.1 预注册 primary contrasts

1. scoped vs ambient 对 `realized_unsafe_effect` 的 risk difference（enforcement effectiveness）；
2. scoped vs ambient 对 `out_of_policy_attempt`、resolved-with-tests、denial/retry 的 contrast（behavior 与 usability）；
3. atomic vs compound 对 resolved-with-tests 与 `out_of_policy_attempt` 的 risk difference；
4. architecture × privilege interaction 对 `realized_unsafe_effect`、`out_of_policy_attempt` 和 resolved-with-tests 的 contrast；
5. adversarial vs clean 的 condition moderation；adversarial subset 另报 attacker-goal completion。

### 7.2 模型选择

- binary utility/security：mixed-effects logistic regression；fixed effects 为 architecture、privilege、condition、model 及预定义 interactions；task/repository 为 random intercept，必要时加入 model random slope。
- count outcomes：negative-binomial mixed model；零膨胀时提前声明 zero-inflated alternative。
- time/token/cost：log transform 后使用 mixed-effects regression；报告 geometric mean ratio 或 log difference。
- paired sparse attack events：randomization test、exact interval 或 hierarchical Bayesian model，避免稀疏事件下机械套用大样本近似。
- Pareto frontier：作为多目标 descriptive analysis；不把 correctness、security、cost 用未经批准的 weighted sum 合成单一分数。

### 7.3 Uncertainty 与 multiplicity

- 每个主要 effect 报告 risk difference / odds ratio / geometric ratio、95% CI 和 practical-effect threshold；
- secondary metric family 使用 Holm 或 Benjamini–Hochberg correction；
- cluster bootstrap 按 task/repository 重采样，不把 rollout 当独立 task；
- 在数据 collection 前用 simulation-based precision planning 确定需要的 task/rollout 数量；
- 不使用 observed post-hoc power 证明研究“有足够 power”；若信息不足，报告 sensitivity / precision analysis。

### 7.4 假设检查与 robustness

- 检查 complete/separation、overdispersion、zero inflation、残差和随机效应收敛；
- 比较 mixed-effects result 与 paired permutation/bootstrap result；
- 对 task contamination、failed environment setup、model refusal 和 timeout 做预先定义的 inclusion/exclusion sensitivity；
- 对 primary security outcomes 使用 strict oracle 和 broad oracle 两个定义，报告 construct sensitivity；
- 若 LLM judge 参与 secondary label，报告 calibration、agreement 和 judge version。

### 7.5 解释原则

- p-value 不是 hypothesis 为真的概率；
- non-significant 不等于 no effect；
- interaction 不仅看 p-value，也看 CI、方向稳定性和 practical magnitude；
- trajectory features 不自动构成 mediator 或 mechanism evidence；
- 若结果互相冲突，保留冲突，不用综合分数掩盖。

## 8. 预期结果与贡献

这里不预填结果，只预先定义可能的 interpretation：

### Scenario A — Interaction evidence

如果 scoped authority 在 atomic interface 上显著降低 realized unsafe effect，而在 compound interface 上 utility/cost penalty 更大，则可以提出“interface representation 与 authority 是 interacting design factors”的经验结论。

### Scenario B — Privilege-only effect

如果只有 scoped authority 稳定降低 realized unsafe effect，且 architecture interaction 很小，则研究应收敛为 coding-agent policy-grading study，并明确与 Permission Denied 的 repository/task/security distinction。

### Scenario C — Interface-only effect

如果 interface 影响 success/efficiency，但不影响 execution security，则不应继续声称 security frontier；应转为 interface behavior study，且必须承认与 *The Devil Is in the Interface* 的重叠。

### Scenario D — Safety through failure

如果 scoped condition 的 attack success 下降完全由 task completion 崩溃造成，则结论应是 policy 形成了 policy-induced safe failure，而不是“安全性提升且保持 utility”。只有 policy 错误阻止 `P*` 内 action 时才能称为 false denial。

### 预期学术贡献

1. **Empirical finding**：估计 interface、authority 和 condition 的 main/interaction effects。
2. **Measurement contribution**：把 functional success、out-of-policy attempt、realized side effect、attack-goal completion 和 safe failure 分开。
3. **Explanation**：用 trace 解释 denial、retry、compound action 和 token/time cost。
4. **Practical implication**：为 coding-agent tool designer 提供 capability matching、authority scope 和 interface observability 的设计依据。
5. **Reproducibility**：公开容器、task manifest、policy matrix、adapter、logs、oracles 和 analysis code。

## 9. Threats to Validity

### Internal validity

- capability equivalence 失败；通过 differential audit、operation matrix 和 forbidden unequal cells 缓解；
- adapter 实现质量不同；同一 core loop、统一 tests、cross-over 和 adapter coverage report；
- denial feedback 本身改变 prompt context；把它记录为 treatment component，并做 context-footprint sensitivity；
- model/API drift；pin version、endpoint、date、temperature、seed 和 container。

### External validity

- SWE-bench 不代表所有 software tasks；按 language/repository/difficulty 扩展，谨慎外推；
- 两个 interface 不代表全部 MCP、CodeAct、IDE 或 enterprise tools；只声称研究过的 architecture levels；
- adversarial variants 不代表真实组织供应链攻击；将其定义为 controlled threat condition，而非现实攻击频率估计；
- open model 与 frontier model 的 transfer 可能不稳定；把 model dependence 作为结果而不是平均掉。

### Construct validity

- test pass 不是完整 correctness；报告 regression、patch validity 与 secure outcome；
- unsafe action 的定义需要 threat-model-specific oracle；公开 taxonomy、event examples 和 audit rules；
- `P*` 可能遗漏合理 action 或错误包含危险 action，因此公开 policy examples、双人 review 和 disagreement log；
- scoped enforcement 会机械降低一部分 realized violation；通过同时报告 out-of-policy attempt、blocked action、绕过、utility 与 interaction，避免把“规则存在”误写成“agent 本身更安全”；
- cost 必须包括 input/output tokens、retries、tool/service cost、wall-clock 的定义和 price snapshot；
- least privilege 不是简单的“更少工具”；用 machine-readable authorization-policy manifest 表示。

### Conclusion validity

- task-level clustering、重复 rollout 和稀疏 security event 要进入统计模型；
- multiple metrics / subgroup / threat vectors 需要 correction；
- 低 replication 或宽 CI 时只报告不确定性，不用“不显著”替代 equivalence；
- 所有 exploratory mechanism analysis 单独标记。

## 10. Artifact、伦理与可复现性

### 10.1 Artifact package

- `Dockerfile`、lockfile、container digest；
- frozen repository/task manifest 和 commit hash；
- interface adapters、capability manifest、permission policy；
- system/task prompts 的 hash 与公开版本；
- run metadata、raw/redacted trajectory、tool/OS audit；
- test/evaluation/oracle code；
- analysis script、model formula、randomization seed 和 price sheet；
- reproduce README：`audit → pilot → clean → adversarial → stats → figures`。

### 10.2 安全与伦理

研究只在研究者拥有或明确授权的本地环境开展。攻击 fixture 使用 fake credentials、temporary directories、canary endpoints 和 disposable repositories；禁止真实密钥、真实第三方服务、生产仓库和不可逆 side effect。所有 run 应有 kill switch、资源上限、网络 allowlist 和自动 reset。

### 10.3 论文写作与证据记录

每个 literature claim 绑定 source ID；每个实验 claim 绑定 run/result ID。开题阶段的 hypothesis、predictions 和 stopping rule 与最终结果分开保存。AI 生成文字需要由作者核验，不能把模型输出当作证据；最终 author、disclosure、data/code access 由人类作者批准。

## 11. 进度安排与 Go/No-Go

| 时间 | 任务 | 交付物 | Go/No-Go |
|---|---|---|---|
| 第 1–2 周 | 读完 Tier 1、冻结 scope、实现 capability audit | protocol v0、source/claim matrix | 不能通过 capability equivalence 则停止 causal claim |
| 第 3–4 周 | 实现两种 adapters、sandbox、logger、clean task runner | harness v0、replay test | 若 actual tool usage 无法验证则暂停正式实验 |
| 第 5–6 周 | 构造 paired adversarial tasks、双人 threat review | threat manifest、canary tests | 若攻击只能造成全局失败，重写 threat condition |
| 第 7–8 周 | MVS 运行与 precision audit | pilot dataset、diagnostic report | 若安全 oracle 不可信或全是 false denial，停止扩展 |
| 第 9–12 周 | Stage 2 confirmation、双模型复现 | frozen dataset、analysis outputs | 若 effect 只在单 task/adapter，降级为 pilot |
| 第 13–14 周 | robustness、taxonomy、mechanism analysis | figures/tables、validity log | 未预注册的分析只能标 exploratory |
| 第 15–16 周 | 写 FSE/PACMSE 风格论文与 artifact | manuscript draft、artifact package | 由 reviewer-style audit 决定是否投稿 |

### 决策阈值

不预先规定“必须显著”。继续投入的最低条件是：

1. capability audit 通过；
2. primary security outcomes 可由 execution evidence 判定；
3. 至少一个 primary contrast 的 estimate 足够精确，能排除“所有条件都完全相同”或“安全只是失败”的关键解释；
4. 结果在 task block 或第二 model 上不是完全反向；
5. artifact 能够重放一条完整 run。

## 12. 参考文献与核验状态

| 论文 | 作者 / 年份 / venue 状态 | 用途 |
|---|---|---|
| [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793) | John Yang et al., NeurIPS 2024 | agent-computer interface 基础 |
| OpenHands: An Open Platform for AI Software Developers as Generalist Agents | Xingyao Wang et al., 2024, ICLR 2025 | open coding-agent platform |
| [The Devil Is in the Interface: Evaluating How Tool Architecture Shapes Coding Agent Behavior](https://arxiv.org/abs/2608.11386) | Xiangzhe Xu et al., COLM 2026；arXiv:2608.11386 | capability-matched interface collision；BashOnly/Atomic 定义 |
| The Scaffolding Matters More Than the Interface: A Controlled Comparison of MCP and CLI Tool Use Across Seven Agent Scaffoldings, Five Language Models, and One Software Task | Marc Alier Forment et al., 2026, arXiv preprint | scaffold/interface confounding、actual tool verification |
| [Permission Denied: Policy-Graded Evaluation of Coding Agents in Hardened Environments](https://arxiv.org/abs/2608.02670) | Dotan Davidovich et al., 2026, arXiv preprint | policy-grading、utility/cost trade-off；whole-configuration 限制 |
| [AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html) | Edoardo Debenedetti et al., NeurIPS 2024 Datasets and Benchmarks | ASR、benign utility、attack utility 的联合测量 |
| [Agent Security Bench (ASB): Formalizing and Benchmarking Attacks and Defenses in LLM-based Agents](https://proceedings.iclr.cc/paper_files/paper/2025/hash/5750f91d8fb9d5c02bd8ad2c3b44456b-Abstract-Conference.html) | Hanrong Zhang et al., ICLR 2025 | refusal/false-positive-aware 的 security–utility 测量 |
| [RedCode: Risky Code Execution and Generation Benchmark for Code Agents](https://proceedings.neurips.cc/paper_files/paper/2024/hash/bfd082c452dffb450d5a5202b0419205-Abstract-Datasets_and_Benchmarks_Track.html) | Chengquan Guo et al., NeurIPS 2024 Datasets and Benchmarks | risky execution 与 harmful generation 分离；Docker execution oracle |
| [Execution-Grounded Security Testing for Coding Agents in Software Engineering Pipelines](https://arxiv.org/abs/2607.22569) | Yifei Ge et al., 2026, arXiv preprint | tool/runtime/diff evidence与 execution oracle |
| SEC-bench: A Comprehensive Benchmark for Secure Code Generation in Real-World Software Engineering | Hwiwon Lee et al., NeurIPS 2025 | repository-level secure-code evaluation |
| [SecureVibeBench: Benchmarking Secure Vibe Coding of AI Agents via Reconstructing Vulnerability-Introducing Scenarios](https://aclanthology.org/2026.acl-long.1107/) | Junkai Chen et al., ACL 2026；DOI: 10.18653/v1/2026.acl-long.1107 | functional + static/dynamic generated-code security oracles |
| IssueTrojanBench: Benchmarking AI Coding Agents Against Malicious Issue Requests | Ankur Singh, Jinqiu Yang, Tse-Hsun Chen, 2026, arXiv preprint | coding-agent issue/repository attack condition |

关键判断均应在正式投稿前由作者再次打开论文正文和官方 venue 页面核验。本文使用的 URL 是可重复的 discovery/verification entry，不把搜索摘要当作完整实验依据。当前开题草案只把已打开的论文正文/正式 proceedings 页面用于上述窄结论；没有把文献中的总体结果外推成本文尚未运行的实验结果。
