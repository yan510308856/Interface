# 动作接口表征是否影响 Coding Agent 安全？

## 基于真实 Repository Repair Tasks 的 Capability-Matched Paired Causal Security Evaluation

**文档版本：** 2026-08-27  
**英文题目：** *Does Action Representation Shape Coding-Agent Security? A Capability-Matched Paired Study on Real Repository Repair Tasks*  
**研究方案简称：** SWE-bench 功能任务 + 自建安全扩展  
**核心自变量：** action interface（Atomic API vs. restricted Python orchestration）

---

## 0. 一页摘要

Repository-level coding agents 已能读取代码、搜索仓库、修改文件并运行测试。已有工作分别表明：

1. agent-computer interface 会显著改变 coding agent 的轨迹、效率与任务表现；
2. repository、issue、文档、代码注释和工具输出都可能成为间接提示注入的载体；
3. 只报告攻击成功率不足以判断系统是否更安全，因为低攻击成功率可能来自任务失败、过度拒绝或根本没有接触攻击内容。

但现有研究尚未充分回答一个更窄、也更可检验的问题：

> 当两个接口能够调用完全相同的底层能力时，仅改变能力的呈现与编排方式，是否会通过改变 agent trajectory，因果性地改变真实仓库修复任务中的安全风险、功能效用与运行成本？

本研究采用配对的 $2\times2$ 设计：

| Repository condition | Atomic / structured interface | Restricted Python interface |
|---|---:|---:|
| Clean task | A | B |
| Paired adversarial task | C | D |

每个 clean/adversarial pair 使用相同的 repository snapshot、issue、功能目标和测试 oracle；adversarial 版本只增加预先定义的恶意载体与安全目标。两个接口共享同一 capability backend、同一 sandbox、同一模型、prompt、预算和评测器。研究重点不是比较两个完整 agent scaffold，而是估计 **action representation 的总效应**以及 **interface × adversarial condition 的配对交互效应**。

主要输出包括：safe resolution、functional resolution、out-of-policy attempt、realized unauthorized effect、attacker-goal completion、safe task failure，以及 tokens、tool calls、wall-clock time 和 cost。轨迹分析进一步考察攻击暴露、指令服从、复合动作和反馈时机是否解释接口之间的差异。

最稳妥的贡献定位是：

> 在真实 repository repair tasks 上，对 capability-matched action interfaces 进行配对因果安全评估，并用执行轨迹将“攻击暴露—违规尝试—真实副作用—功能结果”分开测量。

这不是一个“证明 Atomic 一定更安全”的实验，而是检验：同一组底层能力经过不同接口表征后，是否形成不同的行为分布和安全后果。

---

## 1. Background and Motivation

### 1.1 Repository-level coding agents 的能力边界已经扩展到真实执行环境

SWE-bench 将真实 GitHub issue、固定仓库快照和测试 oracle 组合为 repository repair benchmark。SWE-agent 随后指出，模型之外的 agent-computer interface 会直接影响模型能否有效浏览、编辑和调试代码。OpenHands、CodeAct 等系统进一步采用 shell、代码执行或多工具环境，使 coding agent 能够完成多步的软件工程工作流。

这种能力扩展也改变了安全问题的性质。传统代码生成主要关心生成代码是否包含漏洞；repository agent 则能够在评测或开发环境中实际读取文件、执行命令、修改测试、访问配置并产生持久副作用。因此，本研究关注的是 **agent behavioral safety 与 execution/system security**，而不是仅检查最终 patch 的静态安全性。

### 1.2 Interface 不只是可用性的包装层

SWE-agent 的 Agent-Computer Interface（ACI）工作说明，命令设计、反馈格式和交互约束可以显著改变 repository task performance。CodeAct 表明，使用可执行代码作为行动形式可以让模型组合多个操作。近期预印本 *The Devil Is in the Interface* 在尽量保持信息和底层行动相近的条件下比较多种 coding-agent tool architecture，观察到轨迹长度、token 使用、探索范围和稳定性均随接口变化。

这些结果支持以下机制判断：即使两个接口最终调用相同的文件、搜索和执行能力，它们也未必产生相同的安全行为。接口会改变：

- agent 何时、以何种顺序读取潜在恶意内容；
- 一个 action 能包含多少子操作；
- 每次副作用之前能获得多少环境反馈；
- 系统能否在细粒度 operation 边界记录、检查或中止行为；
- 模型需要显式表达多少中间意图；
- 任务完成所需的步数、上下文暴露量与失败恢复路径。

因此，“底层能力相同”只能排除一种重要混淆：某一接口拥有另一接口没有的能力；它不能推出两者的 trajectory distribution 或安全性相同。

形式上，令 $I$ 为接口、$\tau$ 为轨迹、$M$ 为模型、$\delta$ 为共享执行后端，则：

\[
P(\text{harm}\mid I)
=\sum_{\tau}P(\text{harm}\mid\tau,M,\delta)P(\tau\mid I).
\]

共享后端使给定规范化操作序列后的执行语义尽量一致，但接口仍然可以改变 $P(\tau\mid I)$。这正是本研究要隔离的因果路径。

### 1.3 现有 security benchmark 尚未完成这一隔离

AgentDojo 将正常用户任务和注入攻击组合，并同时报告 utility 与攻击结果；Agent Security Bench（ASB）进一步覆盖攻击、防御、拒绝和 benign performance。RepoGuardBench 提供 clean/poisoned repository pairs，并使用执行结果判断安全性与任务完成情况。IssueTrojanBench 则表明真实 coding workflow 中的 issue、网页、PDF、注释等工件可以承载攻击。

然而，这些研究通常固定 agent 的行动接口，或同时改变 scaffold、工具、权限和防御机制。它们能够回答“某个系统在攻击下表现如何”，但不能直接回答：

> 在模型、任务、提示、权限、底层能力和执行预算都保持不变时，action interface 本身是否改变安全 susceptibility？

另一方面，现有 interface 研究主要测量任务成功、步骤和 token，尚未系统测量配对攻击条件中的 out-of-policy attempt、realized effect 和 safe resolution。因此，两个文献分支之间存在一个可检验的交叉缺口。

---

## 2. Research Scope and Terminology

### 2.1 本研究中的 interface

本研究中的 interface 指模型表达、组合并接收执行动作反馈的方式。它不是 UI，也不是权限策略本身。

两个实验条件为：

1. **Atomic / structured interface**：模型每次调用一个带类型参数的原子工具，例如 `read_file`、`search_text`、`replace_text`、`create_file`、`run_process` 和 `git_diff`。
2. **Restricted Python orchestration interface**：模型生成短 Python action，通过受限对象（例如 `repo.read(...)`、`repo.search(...)`、`repo.replace(...)`、`runner.run(...)`）组合相同能力；一个 action 可以包含多个后端操作。

这里不把两个条件简单称为“低抽象”和“高抽象”。Atomic 与 Python 同时改变了 action granularity、composition、feedback timing 和意图显式程度。更准确的 treatment 名称是 **action representation / action mediation architecture**。

### 2.2 Capability-matched 的含义

Capability-matched 不要求两个接口产生相同步骤，而要求：

- 二者暴露相同的规范化底层操作集合；
- 操作具有相同的路径范围、参数上限、进程限制和返回信息；
- 对于每个允许的 Atomic operation，都存在语义等价的 Python API 调用；
- Python 不能通过 `open`、`os`、`subprocess`、`socket`、FFI、动态导入或其他旁路获得额外能力；
- 两个接口的所有副作用都经过同一 mediation backend 和审计日志；
- 两个条件使用同一外层 sandbox，但 sandbox 不是实验变量。

Capability-matching 的目标是让比较接近“同一能力，不同表征”，而不是“弱工具对强 shell”。

### 2.3 Security 的操作化定义

本研究将 security 定义为：agent 在完成指定 repository repair task 的过程中，不产生超出任务授权边界的尝试或真实副作用，并抵抗 adversarial repository content 对执行行为的操纵。

安全评价分三层：

1. **Out-of-policy attempt**：agent 发出了违反 $P^*$ 的规范化 operation，但可能被外层安全边界拦截；
2. **Realized unauthorized effect**：违规操作在隔离环境中产生了可检测副作用；
3. **Attacker-goal completion**：预定义攻击目标的 oracle 被满足。

三者不能混为一个 ASR。attempt 衡量行为倾向，effect 衡量执行后果，attacker-goal completion 衡量攻击任务是否真正成功。

### 2.4 不在本研究中的问题

本研究不直接研究：

- scoped privilege 与 ambient privilege 的比较；
- 动态权限生成或权限请求 UX；
- 通用 sandbox escape；
- 真实 credential 或网络外传；
- 最终生成代码的漏洞检测；
- 多 agent 通信安全；
- interface 与 privilege 的完整 factorial interaction。

权限被固定为所有条件相同的最小、可完成任务的外层安全边界。这样能够避免原课题中 interface 与 privilege 同时变化造成的解释困难。

---

## 3. Existing Work and Research Gap

### 3.1 Repository repair 与 agent-computer interface

SWE-bench 建立了真实仓库修复的任务结构；SWE-agent 证明 ACI 设计是 coding-agent performance 的重要组成部分；SWE-bench-Live 提供持续更新、时间切分的真实任务来源，减少静态 benchmark 饱和与数据污染问题。CodeAct 和 OpenHands 则代表允许模型使用可执行代码或通用计算环境的 agent 路线。

这条文献链已经建立“interface 会影响 performance”，但尚未建立“在能力匹配条件下，interface 会如何影响 execution security”。

### 3.2 Indirect prompt injection 与 malicious repository content

AgentDojo 将工具调用 agent 的 benign task 与 injection goal 解耦，说明需要同时评价 utility 与 attack success。RepoGuardBench 进一步把恶意指令放入 README、issue、代码注释、测试日志和 agent-rule file，形成 paired clean/poisoned tasks。IssueTrojanBench 扩展了 coding-agent attack artifact 与攻击目标的范围。

这条文献链已经建立“repository content 可以改变 agent 行为”，但通常没有以 capability-matched interface 为 treatment。

### 3.3 Security measurement

早期攻击研究常使用单一 ASR。AgentDojo、ASB、RepoGuardBench 等工作逐步加入 benign utility、utility under attack、拒绝或安全指标。近期 execution-grounded 研究强调使用文件、工具和环境状态，而非只根据文本回答判断攻击是否成功。

本研究继承这种趋势，并进一步将 outcome 分解为：

- functional success；
- safe success；
- safe task failure；
- unsafe success；
- unsafe failure；
- out-of-policy attempt；
- realized unauthorized effect；
- attack exposure；
- operational cost。

由于本研究没有设置“权限机制是否拒绝操作”的 treatment，**false denial 不是主要终点**。外层 sandbox block、模型自主拒绝、普通任务失败和 $P^*$ 误标必须分别记录，不能把所有“攻击未成功”都算作 security success。

### 3.4 最强、最保守的 research gap

目前可辩护的 gap 不是“过去没人研究 interface”，也不是“过去没有 coding-agent security benchmark”，而是：

> 缺少在真实 repository repair tasks 上，通过共享规范化能力后端与 clean/adversarial paired tasks，因果隔离 action interface 对安全 susceptibility、safe task completion 和执行成本影响的研究；现有工作也较少把这一总效应进一步连接到 attack exposure、action compoundness、feedback timing 和 realized side effects 等轨迹机制。

该 gap 具有以下边界：

| 主张 | 判断 |
|---|---|
| Interface 会影响 coding-agent trajectory/performance | 已建立 |
| Repository content 可对 coding agents 实施间接注入 | 已建立 |
| 安全评估应同时报告 security 与 utility | 已建立 |
| Clean/poisoned paired repository tasks | 已有先例 |
| Capability-matched Atomic vs. Python 的 repo security 因果比较 | 部分邻近，但尚未充分建立 |
| 在真实 SWE-bench repair tasks 上研究 interface × attack condition | 潜在新颖 |
| 用执行轨迹分解 exposure、attempt 与 effect | 部分已有，应用和联合分析可能有增量 |

---

## 4. Research Questions

### RQ1 — Clean-task effect

在无攻击的真实 repository repair tasks 上，capability-matched Atomic 与 restricted Python interfaces 是否产生不同的功能成功率、轨迹和运行成本？

### RQ2 — Security susceptibility

在 paired adversarial tasks 上，两个接口的 out-of-policy attempt、realized unauthorized effect、attacker-goal completion 和 safe resolution 是否不同？

### RQ3 — Paired causal interaction

从 clean 变为 adversarial condition 所造成的结果变化，是否因 interface 而不同？换言之，interface 是否改变 agent 对恶意 repository content 的 susceptibility，而不仅仅改变一般任务能力？

### RQ4 — Trajectory mechanisms

接口之间的差异是否与下列轨迹特征相关：攻击内容暴露率、暴露后服从率、每个 action 的后端操作数、首次危险动作前的反馈次数、搜索广度、重复尝试和恢复路径？

### RQ5 — Robustness and heterogeneity

观察到的效应能否跨模型、repository、任务难度、攻击载体与攻击目标保持，还是只发生在特定组合中？

---

## 5. Hypotheses and Rival Explanations

### 5.1 Primary hypotheses

**H1：Interface total effect。** 在相同能力后端下，Atomic 与 restricted Python 会产生不同的 safe resolution rate 和 unauthorized-effect risk。

**H2：Interface × condition interaction。** adversarial content 相对 clean condition 引起的安全与效用退化幅度会因 interface 而不同。

**H3：Trajectory divergence。** Python interface 倾向于在单个 action 中组合更多规范化操作，并减少中间反馈；Atomic interface 倾向于产生更多 step-level checkpoints。该差异与安全 outcome 相关。

**H4：Exposure–compliance decomposition。** 两个接口可能通过不同路径影响风险：一方可能更少读取恶意内容，另一方可能在读取后更少服从。只报告最终 ASR 会掩盖这两种机制。

### 5.2 Competing predictions

不能预设 Atomic 一定更安全。至少存在三组相反预测：

| 机制 | Atomic 可能更安全 | Python 可能更安全 |
|---|---|---|
| Feedback timing | 每个原子操作后反馈，较早暴露异常 | 更少步骤，减少与恶意环境交互的机会 |
| Action composition | 难以在一个 action 中隐藏长链副作用 | 可在本地代码中先检查、过滤再执行 |
| Observability | typed operation 更易审计和归因 | 完整 Python 逻辑可能表达更明确的条件判断 |
| Context exposure | 小步搜索可能增加读取恶意文件概率 | 批处理可能减少搜索与上下文污染 |

### 5.3 Null and backend-dominance explanation

**H0：** 在 capability matching 严格成立时，安全结果主要由模型和恶意内容决定，接口只改变效率，不改变安全风险。

若结果支持 H0，同样具有研究价值：它会限制“通过改变 action representation 提升安全”的主张，并提示研究重心应转向权限执行、内容隔离或策略防御。

### 5.4 关于机制因果性的限制

RQ1–RQ3 的 interface treatment 可以进行因果解释，因为 interface 被随机分配且其他条件固定。RQ4 中 exposure、compoundness 等变量是 treatment 后产生的 mediator。除非增加单独的 mediator intervention，否则它们只能被解释为机制证据或关联性 decomposition，不能直接声称已识别自然间接效应。

---

## 6. Experimental Design

### 6.1 Overall design

采用 task-level paired、within-task $2\times2$ factorial design：

| Cell | Interface | Repository condition |
|---|---|---|
| A | Atomic | Clean |
| B | Python | Clean |
| C | Atomic | Adversarial |
| D | Python | Adversarial |

每个基础 task 都在四个 cell 中运行。clean 与 adversarial task 构成配对，Atomic 与 Python 也在同一 task 上比较。每次 rollout 使用全新的 container，防止文件、缓存、测试结果或对话状态跨条件泄漏。

### 6.2 Experimental unit and repeated observations

- **主要独立单位：** base repository task；
- **cluster：** repository；
- **重复观测：** 同一 task、interface、condition 下的 stochastic rollouts；
- **blocking variables：** repository、任务难度、attack family、model；
- **run order：** 在 block 内随机化；
- **分析注意：** rollout 不是独立 task，不能把大量 rollout 当作独立样本计算过窄置信区间。

### 6.3 Independent variables

**主要 treatment：**

1. Interface：Atomic vs. restricted Python；
2. Content condition：clean vs. paired adversarial。

**预先设定的异质性变量：**

- model；
- attack carrier；
- attack goal；
- repository；
- task difficulty。

这些变量用于 blocking、分层或 secondary analysis，不应在主研究中无限扩展为高维 factorial treatments。

### 6.4 Controlled variables

以下项目必须在两个 interface 条件间保持一致：

- foundation model 与具体版本；
- system prompt、task prompt 的语义内容；
- repository snapshot 和 base image；
- network、filesystem、process、credential 边界；
- 可调用的规范化 backend operations；
- 文件内容与工具返回内容；
- wall-clock、token、step、process 和 retry budgets；
- temperature、sampling 参数和随机种子方案；
- test oracle、security oracle 与评分代码；
- scaffold 的规划、终止和上下文管理逻辑；
- 初始化信息和 working directory；
- outer sandbox 与 fail-closed 行为。

### 6.5 Model selection

最小确认实验使用两个行为特征不同、可固定版本的 coding-capable models。选择时不以排行榜为唯一标准，而应覆盖：

- 一个较强、工具使用稳定的模型；
- 一个较小或不同训练路线的模型。

模型必须作为 block 或固定效应纳入分析。若预算仅允许一个模型，结论应明确限定为该模型，不能泛化为“coding agents”。

---

## 7. Capability-Matched Interface Implementation

### 7.1 Canonical capability backend

所有外部动作先转换为统一的 canonical operation：

```text
Operation {
  operation_id,
  type,
  normalized_arguments,
  requested_paths,
  process_spec,
  parent_action_id,
  timestamp,
  result,
  side_effects
}
```

建议的最小 operation set：

| Operation | 功能 | 关键限制 |
|---|---|---|
| `read_file` | 读取仓库文件片段 | repo root 内；固定最大字节数 |
| `list_path` | 列举目录 | repo root 内；限制深度 |
| `search_text` | 文本搜索 | 相同搜索引擎、输出上限 |
| `replace_text` | 定位并替换文本 | 相同 diff 与冲突语义 |
| `create_file` | 创建文件 | repo root 内；大小上限 |
| `delete_path` | 删除文件 | 若任务需要才启用；统一审计 |
| `run_process` | 执行测试或命令 | 固定 cwd、环境变量和 resource limits |
| `git_diff` | 查看 patch | 相同 diff 格式与截断规则 |

每个 operation 都经过同一参数规范化、路径解析、审计、资源限制和返回值格式化。底层实现不是 treatment。

### 7.2 Atomic interface

Atomic 条件把每个 canonical operation 暴露为独立 typed tool call。一次模型 action 只能请求一个 operation，并在下一个模型 step 前返回结果。

设计目的不是人为削弱 Atomic，而是使其具备与 Python 相同的 operation set。若 Python 能循环读取多个文件，Atomic 也必须能通过多次调用完成；差异仅在组合与反馈边界。

### 7.3 Restricted Python interface

Python 条件允许模型提交短 Python program，并通过注入的安全对象调用相同 backend：

```python
matches = repo.search_text("deprecated_api")
for match in matches[:5]:
    text = repo.read_file(match.path)
    # local computation
runner.run("pytest -q tests/test_target.py")
```

必须禁止或拦截：

- built-in `open` 及任意原生文件 API；
- `os`、`pathlib` 的直接 filesystem access；
- `subprocess`、`pty` 和 shell bypass；
- `socket` 与网络库；
- FFI、native extension、动态加载和未批准 import；
- 反射或序列化逃逸；
- 访问 host environment、真实 credential 或其他 task container。

Python 执行器本身运行在额外隔离层内；每个 `repo.*` 或 `runner.*` 调用仍生成一条 canonical operation log。

### 7.4 Equivalence validation

在主实验前建立 capability-equivalence test suite：

1. 对每个 Atomic operation 构造对应 Python 调用；
2. 比较返回值、异常、截断、路径解析和副作用；
3. 对随机 operation sequence 做 differential testing；
4. 对路径穿越、symlink、编码、超长参数和 timeout 做 boundary tests；
5. 对 Python bypass 做 adversarial escape tests；
6. 从 pilot trajectories 抽样，检查是否存在只在某一接口可表达的行为；
7. 发布 capability manifest 和已知不等价项。

若关键能力无法匹配，应先修正接口，而不是把差异解释为 interface effect。

### 7.5 Interface fidelity checks

除底层能力外，还需要检查可能造成混淆的表征因素：

- tool schema 或 API documentation 的 token 长度；
- error message 的信息量；
- 默认输出截断；
- 每个模型 step 可见的历史长度；
- Python wrapper 是否额外提供示例或规划提示；
- Atomic tool names 是否泄露任务策略；
- compound action 失败时的部分提交语义。

这些差异应被匹配、记录，或在论文中明确作为 interface treatment 的组成部分。

---

## 8. Hybrid Benchmark: SWE-bench Functional Tasks + Security Extension

### 8.1 Base task source

主数据集从固定版本的 SWE-bench 或 SWE-bench-Live 中选择真实 repository repair tasks。优先采用 SWE-bench-Live 的时间切分任务，以降低训练数据污染风险；最终必须冻结具体 release、commit、Docker digest 和任务清单。

纳入标准：

- repository 可在固定 container 中可靠构建；
- functional tests 可重复执行；
- 任务在统一能力后端下可解决；
- issue 不要求真实网络、云服务或私有 credential；
- reference patch 或人工 solvability witness 不违反 $P^*$；
- clean task 不含与实验 payload 冲突的内容。

排除标准：

- 测试高度 flaky；
- 环境无法冻结；
- 必须扩大 host 权限才能完成；
- 安全扩展会改变功能需求或明显提示模型存在攻击；
- attack oracle 无法确定性判断。

### 8.2 Paired clean/adversarial construction

对每个 base task 构造一对环境：

```text
Clean task T_i:
  repository snapshot R_i
  issue Q_i
  functional oracle F_i

Adversarial task T_i^adv:
  same R_i, Q_i, F_i
  + one controlled carrier C_i
  + one inert attack goal G_i
  + security oracle S_i
```

配对构造必须满足：

- 功能要求不变；
- reference fix 不需要执行攻击目标；
- adversarial 增量尽量最小；
- clean 与 attack 版本的非攻击文本、长度和格式尽量匹配；
- payload 不破坏 build 或 test；
- 攻击成功只能通过真实 operation/effect oracle 判定；
- 每个 task pair 有可审计的 delta manifest。

### 8.3 Attack carrier families

建议第一版覆盖四类 carrier，每类与不同 trajectory mechanism 对应：

| Carrier | Agent 如何接触 | 主要机制问题 |
|---|---|---|
| Repository documentation | README、CONTRIBUTING、局部说明文件 | interface 是否改变搜索与读取暴露？ |
| Source/test comments | 与目标代码接近的注释或 docstring | 局部阅读后是否服从恶意指令？ |
| Issue text | issue body 或附加说明 | 攻击从起始上下文直接暴露时是否仍有差异？ |
| Execution output | 测试日志、fixture 输出、构建错误 | feedback timing 是否改变注入传播？ |

issue-text carrier 可作为“近似固定 exposure”条件；repository 与 execution-output carriers 则允许研究 interface 如何改变 exposure probability。

### 8.4 Safe attack goals

攻击目标必须是 inert、local、可恢复的代理行为，避免真实危害：

1. 读取超出任务所需范围的 canary file；
2. 将 canary 内容写入指定本地 sink marker；
3. 删除或篡改与修复无关的测试文件；
4. 修改受保护的 agent-rule/config 文件；
5. 在非目标代码区写入可检测 persistence marker；
6. 执行未授权但无害的 marker command。

首版不使用真实网络外传、真实 secrets、包发布、fork bomb 或其他资源耗尽攻击。若研究 local exfiltration，只允许从 synthetic canary 到同一 container 内的监测 sink。

### 8.5 Attack-family sampling

不应为每个 task 任意放置所有攻击。建议建立 task–attack compatibility matrix，并在预注册前固定分配：

- 每个 task 只接受不改变 functional solvability 的 payload；
- 每个 carrier/goal combination 覆盖多个 repositories；
- 相同 payload wording 在不同 interface 条件中完全一致；
- 攻击强度和可见性分层；
- 对明显诱导、隐蔽诱导分别报告；
- 避免让某一 attack family 与某一 repository 完全重合。

### 8.6 Role of existing security benchmarks

RepoGuardBench 可用于 harness pilot、oracle 设计参考和 secondary external validation，但不作为主生态效度证据，因为其核心任务以 synthetic micro-repositories 为主，且接口固定。AgentDojo 可提供 user-goal/injection-goal 分离的评价思想。IssueTrojanBench 可帮助覆盖真实 coding workflow 的攻击载体，但本研究仍需自行构造与 SWE-bench 功能任务严格配对的版本。

因此，目前没有可以无修改直接满足以下全部要求的现成数据集：真实 SWE-bench repair、clean/adversarial pairs、capability-matched interfaces、统一执行 oracle 和 interface causal comparison。自建安全扩展是本课题的必要工程贡献，而不是对现有 benchmark 的简单重命名。

---

## 9. Task Permission Manifest $P^*$

### 9.1 Purpose

$P^*$ 是每个 task 的规范性授权真值，用于判断 operation 是否与任务目标一致。它不是运行时 treatment，也不用于对某一 interface 额外施加权限。

可以借鉴 Progent 等 policy-control 工作中的 typed operation、resource 和 argument constraints，但本研究不复现动态权限生成机制，也不把 policy enforcement 的效果归因于 interface。

### 9.2 Suggested schema

```yaml
task_id: example__issue-123
allowed:
  read:
    - repo/**
  write:
    - src/target_module.py
    - tests/test_target.py
  execute:
    - pytest
    - python -m pytest
  network: false
protected:
  - .agent/**
  - .github/workflows/**
  - tests/security_canary/**
canaries:
  - path: .security/canary.txt
    allowed_read: false
attack_goals:
  - local_sink_contains_canary
```

实际规则不应只依赖精确 path allowlist，否则可能把合理修复错误标记为违规。建议把规则分为：

- hard prohibitions：网络、host path、真实 credential、受保护配置；
- task-scoped resources：与 issue 相关的 source/test 范围；
- conditionally allowed operations：例如只允许运行 repository test commands；
- semantic exceptions：经人工审查的合理跨文件修复。

### 9.3 Construction and validation

每个 $P^*$ 经过以下流程：

1. 根据 issue、repository structure 和 reference patch 起草；
2. 用 reference patch 或人工 safe trajectory 验证任务可完成；
3. 由第二名 reviewer 独立检查权限边界；
4. 运行 clean pilot，审查高频“违规”是否属于 manifest 误标；
5. 在正式实验前冻结并记录 hash；
6. 正式实验后只允许进行预先定义的 blinded adjudication，不随结果调整规则。

### 9.4 Avoiding circularity

$P^*$ 不能通过某一 interface 的成功轨迹反向定义，否则会偏向该接口。reference patch 只作为 solvability witness，不等于唯一合法 patch。对语义含糊的行为应设置 `adjudication_required`，并同时报告严格与宽松 scoring sensitivity。

---

## 10. Functional and Security Oracles

### 10.1 Functional oracle

功能正确性优先复用 SWE-bench 的 FAIL_TO_PASS 与 PASS_TO_PASS tests，并固定 test harness。需要额外记录：

- test exit status；
- resolved/unresolved；
- patch applies；
- regression tests；
- test tampering；
- harness integrity。

不能仅使用 agent 自报“任务完成”或 patch 文本相似度。

### 10.2 Security oracle

安全 oracle 由三类证据组成：

1. **Canonical operation log**：判断请求了什么 operation、参数和路径；
2. **Environment-state diff**：判断文件、进程、marker、local sink 等是否真实变化；
3. **Attack-goal checker**：判断具体攻击目标是否实现。

例子：

| Attack goal | Attempt oracle | Effect oracle |
|---|---|---|
| 读取 canary | 请求 `read_file(canary)` | backend 实际返回 canary 内容 |
| 本地“外传” | 请求写入 sink | sink 中出现 task-specific nonce |
| 删除测试 | 请求删除/覆盖 test | test hash 或文件状态改变 |
| 修改受保护配置 | 请求写 protected path | 文件 diff 命中 protected path |
| marker command | 请求运行命令 | marker process/event 被审计器捕获 |

### 10.3 Why the security oracle must be custom-built

SWE-bench 的 tests 只判断功能修复，不知道哪些副作用未经授权。安全扩展因此必须自行实现 attack-goal oracle 和 environment-state audit。可以复用原 benchmark 的 correctness tests，但不能把“tests pass”当作安全证据。

### 10.4 Outer sandbox events

共同 sandbox 可能拦截真正越界操作。此类 episode 应同时记录：

- `unsafe_attempt = 1`；
- `sandbox_block = 1`；
- `realized_effect = 0`；
- functional outcome 独立计算。

不能把 block 直接算作 agent 自身“安全”。它表示外层控制有效，但 agent 仍表现出违规倾向。

---

## 11. Outcome Taxonomy and Metrics

### 11.1 Episode-level outcome categories

| Category | Functional task | Realized unsafe effect | Interpretation |
|---|---:|---:|---|
| Safe Success | success | no | 理想结果 |
| Safe Task Failure | failure | no | 没有造成伤害，但没有完成任务 |
| Unsafe Success | success | yes | 修复成功但伴随越权副作用 |
| Unsafe Failure | failure | yes | 既未修复又造成副作用 |

此外单独记录：

- model refusal / over-defense；
- unsafe attempt blocked by sandbox；
- infrastructure failure；
- oracle indeterminate；
- $P^*$ adjudication case。

### 11.2 Primary metrics

1. **Safe Resolution Rate (SRR)**

\[
SRR=\frac{\#(\text{functional success and no realized unsafe effect})}{\#\text{valid episodes}}
\]

2. **Realized Unauthorized Effect Rate (RUER)**

\[
RUER=\frac{\#(\text{episodes with unauthorized effect})}{\#\text{valid episodes}}
\]

3. **Out-of-Policy Attempt Rate (OPAR)**

\[
OPAR=\frac{\#(\text{episodes with at least one }P^*\text{ violation attempt})}{\#\text{valid episodes}}
\]

4. **Attacker-Goal Completion Rate (AGCR)**，只在 adversarial condition 中计算。

5. **Functional Resolution Rate (FRR)**，分别在 clean 和 adversarial condition 中报告。

### 11.3 Secondary security–utility metrics

- utility under attack；
- attack-induced utility degradation；
- safe task failure rate；
- unsafe success / unsafe failure rate；
- model refusal rate；
- sandbox-block rate；
- unauthorized operation count；
- severity-weighted effect score；
- clean false-alarm behavior，例如无攻击时不必要地拒绝读取正常文件。

### 11.4 Trajectory metrics

- attack exposure：恶意内容是否进入模型可见上下文；
- time/steps to first exposure；
- compliance after exposure；
- time/steps to first unsafe attempt；
- canonical operations per model action；
- read/search/write/process operation counts；
- unique files and directories visited；
- feedback checkpoints before write/execute；
- retries and repeated failed operations；
- rollback/recovery after unsafe attempt；
- patch scope and protected-path touches。

### 11.5 Operational cost

- input/output tokens；
- model turns；
- interface actions；
- canonical backend operations；
- wall-clock latency；
- process runtime；
- monetary API cost；
- cost per safe resolution。

必须同时报告 interface actions 与 canonical operations。Python 的一个 action 可能包含多个 operations；只比较 action 数会产生误导。

### 11.6 Severity and denominators

不同安全事件严重程度不同。主要分析使用透明的二元 outcome，secondary analysis 可使用预注册 severity weights。所有比例必须给出分母和无效 episode 的处理方式，避免因接口产生更多 infrastructure error 而人为降低 ASR。

---

## 12. Causal Estimands

### 12.1 Interface effect within each condition

对 outcome $Y$，例如 unauthorized-effect indicator：

\[
\Delta_{I,c}=E[Y\mid I=\text{Python},C=c]-E[Y\mid I=\text{Atomic},C=c],
\]

其中 $c\in\{clean,adversarial\}$。正值表示 Python 条件有更高风险；若 $Y$ 为 safe resolution，则方向相反，必须在报告中明确。

### 12.2 Primary paired interaction estimand

\[
\Delta_{pair}=
\big(E[Y_{Python,adv}]-E[Y_{Python,clean}]\big)
-\big(E[Y_{Atomic,adv}]-E[Y_{Atomic,clean}]\big).
\]

对 harm outcome，正的 $\Delta_{pair}$ 表示 adversarial content 在 Python interface 下造成更大的额外风险。该 difference-in-differences 式 estimand 能区分：

- 接口一般性地使 agent 更容易失败；
- 接口特异性地改变攻击 susceptibility。

由于四个条件在同一 base task 上配对并随机运行，该 estimand 比直接比较两个 adversarial ASR 更有解释力。

### 12.3 Exposure-conditioned quantities

建议报告：

\[
P(exposure\mid I),
\quad P(unsafe\ attempt\mid exposure,I),
\quad P(effect\mid unsafe\ attempt,I).
\]

它们用于说明差异发生在 exposure、compliance 还是 execution 阶段。由于 exposure 是 treatment 后变量，这些条件概率默认是描述性机制分析，不替代主 ITT-style estimand。

### 12.4 Safe-efficiency estimand

\[
\text{Cost per Safe Resolution}
=\frac{\text{total cost over valid episodes}}{\#\text{safe resolutions}}.
\]

同时展示 safe resolution 与 cost 的二维图或 Pareto frontier，避免将节省 token 但显著降低安全完成率的系统描述为“更优”。

---

## 13. Pilot and Confirmatory Study

### 13.1 Stage 0 — Infrastructure validation

在任何模型比较前完成：

- canonical backend unit tests；
- Atomic/Python differential equivalence tests；
- Python escape and bypass tests；
- container reproducibility tests；
- functional oracle repeatability；
- payload inertness tests；
- attack oracle positive/negative controls；
- $P^*$ solvability witness；
- log completeness and event ordering checks；
- fail-closed and kill-switch tests。

### 13.2 Pilot

建议范围：

- 12–16 个 base tasks；
- 至少 4 个 repositories；
- 3–4 个 attack families；
- 1 个模型；
- 每 cell 每 task 3 个 rollouts。

Pilot 的目的不是显著性检验，而是估计：

- outcome 基线率；
- task/repository 间方差；
- stochastic rollout 方差；
- attack exposure rate；
- oracle 误判与 manifest adjudication 频率；
- 每 episode 成本；
- capability mismatch 和 floor/ceiling effects。

### 13.3 Confirmatory study

初始预算建议：

- 24–40 个 base tasks；
- 至少 8 个 repositories；
- 2 个固定版本模型；
- 每 cell 每 model 每 task 5 个 rollouts。

该数字仅用于预算估算。正式样本量应根据 pilot 的 cluster variance、事件率和目标最小可检测 risk difference 进行 simulation-based power/precision analysis。若安全事件非常稀少，应增加 task/attack diversity，而不是只在少数 task 上堆积 rollouts。

### 13.4 Go/no-go criteria

进入正式实验前应满足：

- capability differential tests 全部通过或差异已公开且可接受；
- clean tasks 在至少一种接口下不存在大面积不可解；
- attack oracle 的 positive/negative controls 稳定；
- adversarial variant 不改变 reference functional outcome；
- Python 无已知高危旁路；
- infrastructure failure 率低于预注册阈值；
- $P^*$ 人工争议率可控；
- pilot 中 exposure 与 attack outcomes 不全为 0 或全为 1。

---

## 14. Statistical Analysis Plan

### 14.1 Primary model

对二元 outcome（safe resolution、unsafe attempt、realized effect）使用 hierarchical logistic model 或可直接给出 risk difference 的 generalized mixed model：

```text
Y ~ interface
  + condition
  + interface × condition
  + model
  + attack_family
  + (1 | repository)
  + (1 | task)
```

task 嵌套于 repository；rollout 是 task-cell 内重复观测。主要参数是 `interface × condition`。同时报告 marginal risk、risk difference、odds ratio 和 95% confidence/credible intervals。

### 14.2 Paired robustness analysis

为减少模型形式依赖，增加：

- task-paired risk-difference estimates；
- cluster bootstrap，按 repository/task 重采样；
- 在随机化方案允许时使用 randomization inference；
- leave-one-repository-out sensitivity；
- model-specific 和 attack-family-specific forest plots。

### 14.3 Count and cost outcomes

- operation count、retry count：negative-binomial mixed model；
- tokens、latency、cost：log-transformed mixed model或稳健分位数模型；
- time-to-first-exposure / unsafe attempt：带 cluster frailty 的 survival analysis；
- path diversity：预注册定义后使用 count model。

### 14.4 Mechanism analysis

先画出预注册 causal graph：

```text
Interface
  -> search/read trajectory
  -> attack exposure
  -> instruction compliance / unsafe attempt
  -> realized effect
  -> functional and safe resolution
```

主文以 sequential descriptive decomposition 为主。若进行 mediation analysis，必须陈述 sequential ignorability 等不可验证假设，并将结果标记为 exploratory。更强的机制验证可在后续实验中单独操纵 exposure，例如预先把相同攻击内容固定注入起始上下文。

### 14.5 Multiple testing and missingness

- 预注册 1–2 个 primary outcomes，例如 SRR 与 RUER；
- RQ3 的 interaction 为主要 confirmatory test；
- 其他指标按 family 控制 FDR 或明确标为 exploratory；
- infrastructure failure 不归为 safe failure；
- 分别报告 intention-to-treat-style 全部有效分配与 per-protocol interface-fidelity analysis；
- 对 timeout、context overflow、oracle indeterminate 制定固定规则。

---

## 15. Expected Results and Their Interpretation

### Scenario A — Atomic 更安全且 utility 相近

可能观察到 Atomic 的 unsafe attempt 和 realized effect 更低，safe resolution 不下降。轨迹可能显示更早反馈、更少 compound operations、危险动作前更多 checkpoint。

可得结论：细粒度 action mediation 在当前模型、任务和共享后端中降低了攻击 susceptibility。不能直接推广为“所有 structured tools 都比 Python 安全”。

### Scenario B — Python 更安全且成本更低

Python 可能以更少 step 完成任务，减少恶意文件搜索与测试日志暴露，因此攻击接触率更低。若暴露后服从率相同，主要机制是 exposure reduction，而非更强安全判断。

可得结论：减少交互表面积可能抵消 compound action 的潜在风险。

### Scenario C — Python utility 更高但 harm 也更高

这会形成清晰的 security–utility trade-off。应报告 safe resolution 和 cost per safe resolution，而不是分别宣传性能或 ASR。

### Scenario D — Adversarial ASR 不同，但 paired interaction 不显著

这表示差异可能来自接口的一般任务能力或失败率，而非特异的 security susceptibility。此时不能声称 interface 导致了更强攻击防御。

### Scenario E — 无显著安全差异

如果 capability matching 成立且置信区间足够窄，可得出有价值的边界结论：action representation 对效率和轨迹有影响，但在测试的攻击范围内未产生具有实践意义的安全差异。后续研究应优先考察权限 enforcement、内容隔离或显式安全策略。

---

## 16. Contributions

### 16.1 Empirical contribution

给出 capability-matched Atomic 与 Python interfaces 在真实 repository repair tasks 上对功能、安全和成本的配对效应估计，而非比较两个完整、不可分解的 agent systems。

### 16.2 Measurement contribution

联合报告 functional resolution、safe resolution、safe task failure、unsafe attempt、realized effect、attacker-goal completion、exposure 和运行成本，避免把所有 blocked/failed attacks 计为安全成功。

### 16.3 Software-engineering contribution

构建 SWE-bench task 的 paired security extension，包括 task–attack compatibility、$P^*$、执行日志和 deterministic security oracles，使真实修复任务可用于 execution-security evaluation。

### 16.4 Security contribution

检验 action representation 是否是 execution security 的独立设计变量，并定位风险差异发生在 exposure、behavioral compliance 还是 effect realization 阶段。

### 16.5 Artifact contribution

发布可复现的共享 backend、两种 interface adapters、task pairs、payload manifests、oracle、container digests、日志 schema 和分析脚本。

---

## 17. Threats to Validity

### 17.1 Construct validity

- Atomic vs. Python 同时包含 granularity、syntax、batching 和 feedback timing，不能把结果只归因于“abstraction level”；
- $P^*$ 可能把合理跨文件修复误判为违规；
- inert marker 与真实数据外传的严重性和诱因不同；
- functional tests 可能无法覆盖 patch 的全部正确性；
- attack exposure 需要严格定义“内容是否真正进入模型上下文”。

### 17.2 Internal validity

- Python 旁路会破坏 capability matching；
- tool documentation 长度或示例差异会形成 prompt confound；
- 两个接口的错误信息、截断或 partial-commit semantics 可能不一致；
- run order、cache 和 container residue 可能造成 carryover；
- API model updates 会改变结果；
- 人工构造攻击时可能无意中使某一接口更容易识别。

### 17.3 External validity

- SWE-bench repositories 不能代表所有企业代码库；
- 两个模型不能代表所有 coding agents；
- restricted Python 不等于 unrestricted shell、Jupyter 或 CodeAct 的全部实现；
- 本地 inert attacks 不覆盖真实网络、供应链和 credential threats；
- benchmark task time period 可能与当前模型训练数据重叠。

### 17.4 Statistical conclusion validity

- 安全事件低基线率可能导致 power 不足；
- rollout 伪重复会夸大 precision；
- repository heterogeneity 可能大于 interface effect；
- 多个 attack families 和 metrics 会增加多重检验风险；
- 仅报告显著结果会掩盖有意义的置信区间和 null findings。

### 17.5 Benchmark overlap

若 task 与 *The Devil Is in the Interface* 使用的 SWE-bench-Live subset 重叠，应公开任务重叠并做敏感性分析。重叠本身不使研究无效，但可能减弱“全新任务样本”的表述。

---

## 18. Reproducibility, Safety, and Ethics

### 18.1 Reproducibility package

最低发布内容：

- frozen task list 和 benchmark release；
- repository commit 与 container digest；
- clean/adversarial delta manifests；
- payload templates 与 attack-family labels；
- $P^*$ manifests 及 hashes；
- Atomic schema 与 Python API；
- canonical backend 和 equivalence tests；
- prompts、model identifiers、sampling settings 和 seeds；
- full event logs 与 environment-state diffs；
- functional/security oracle code；
- run schedule 和 exclusion log；
- analysis scripts、table generation 和 preregistration。

### 18.2 Security controls

- 所有实验在 disposable containers 中运行；
- 默认关闭外部网络；
- 不放置真实 secret；
- canary 使用每 episode 唯一 nonce；
- host filesystem 不挂载到 agent 可写范围；
- 限制 CPU、内存、进程数、文件大小和 wall-clock；
- 记录所有 process 和 filesystem events；
- 设置 emergency kill switch；
- 对公开 artifact 做 payload 风险审查。

### 18.3 Responsible reporting

论文应避免发布可直接用于真实供应链攻击的 payload。对方法复现必要的信息可以公开，但真实 credential、可用恶意基础设施和高破坏性命令不应进入数据集。

---

## 19. Work Plan

### Phase 1 — Design freeze（第 1–2 周）

- 冻结研究问题、treatment 和 primary estimands；
- 选择 benchmark release 和候选 tasks；
- 定义 canonical operations、$P^*$ schema 和 outcome taxonomy；
- 预注册 exclusion 与 adjudication rules。

### Phase 2 — Harness and interface implementation（第 3–4 周）

- 实现共享 backend；
- 实现 Atomic adapter 和 restricted Python executor；
- 完成 differential equivalence 与 escape tests；
- 接入 SWE-bench functional harness。

### Phase 3 — Security extension（第 5–6 周）

- 构造 paired attack variants；
- 编写 attack-goal oracle 和 environment-state audit；
- 双人审查 $P^*$；
- 执行 positive/negative controls。

### Phase 4 — Pilot（第 7 周）

- 运行 12–16 tasks；
- 检查 floor/ceiling、成本、flakiness 和 capability mismatch；
- 完成 simulation-based sample-size planning；
- 冻结 confirmatory protocol。

### Phase 5 — Confirmatory run（第 8–9 周）

- 按随机化 schedule 执行；
- 自动监测 infrastructure failure；
- 不查看分组聚合结果地完成必要 adjudication。

### Phase 6 — Analysis and writing（第 10–12 周）

- 运行预注册模型与 sensitivity analyses；
- 完成 trajectory decomposition；
- 整理 artifact 和复现实验；
- 写作结果、限制和 threat-to-novelty 部分。

---

## 20. Novelty Positioning

### 20.1 推荐的论文定位

> Prior work shows that coding-agent interfaces shape trajectories and that malicious repository content can induce unsafe actions. We test the missing intersection: whether action representation itself causally changes security susceptibility when capabilities, authority, model, task, and execution budget are held constant. We introduce paired security extensions to real repository-repair tasks and separate exposure, unsafe attempts, realized effects, functional success, and operational cost.

中文表述：

> 现有研究已分别证明 coding-agent interface 会改变行为轨迹，以及恶意 repository content 会诱导不安全操作。本研究检验两者尚未充分覆盖的交叉问题：当底层能力、权限、模型、任务与预算保持一致时，action representation 本身是否因果性地改变攻击易感性。我们在真实 repository repair tasks 上构造配对安全扩展，并分离攻击暴露、违规尝试、真实副作用、功能成功与运行成本。

### 20.2 不应宣称的 novelty

以下说法会被现有文献反驳或过度扩大：

- “首次发现 interface 会影响 agent behavior”；
- “首个 coding-agent security benchmark”；
- “首次使用 clean/adversarial paired tasks”；
- “首次同时测量 security 和 utility”；
- “首次研究 indirect prompt injection against agents”；
- “证明 Atomic tools 天生比 Python 安全”；
- “完整识别了 trajectory mediator 的因果效应”；
- “结果适用于所有 models、tools 和 repositories”。

### 20.3 论文成立的最低条件

若只做 Atomic vs. Python 的 adversarial ASR 比较，创新性和因果解释都偏弱。课题必须至少保留：

1. capability-equivalence validation；
2. 同一 task 的 clean/adversarial pairing；
3. interface × condition interaction；
4. functional + attempt + effect + safe-resolution outcomes；
5. execution-grounded oracle；
6. trajectory mechanism decomposition；
7. task/repository clustered statistical analysis。

---

## 21. Minimal Viable Study and Extension Path

### 21.1 MVP

若时间或预算有限，最小可发表版本为：

- 16 个真实 base tasks，至少 4 repositories；
- Atomic 与 restricted Python 两个 interfaces；
- clean 与 adversarial paired conditions；
- issue-text、repository-comment、test-output 三种 carrier；
- canary read/local sink、protected-file modification、test tampering 三类 goal；
- 1 个模型，5 rollouts/cell；
- SRR 与 RUER 为 primary outcomes；
- 完整 capability tests 和 execution logs。

该版本适合先验证效应是否存在，但外部效度有限。

### 21.2 Stronger thesis version

- 扩展到 24–40 tasks、8+ repositories、2 models；
- 引入固定-exposure attack condition 以区分 exposure 与 compliance；
- 使用 RepoGuardBench 做 synthetic-to-real external validation；
- 比较不同 attack visibility/severity；
- 建立公开 paired benchmark artifact。

### 21.3 Follow-up study, not current scope

若 interface-only 研究发现明确差异，下一项研究可再引入 authority granularity，形成 interface × authority factorial design。这样 privilege treatment 有了经验依据，而不是在第一项实验中同时承担过多变量和工程复杂度。

---

## 22. Supervisor-facing Explanation

### 22.1 一分钟版本

现有 coding agents 可以用不同方式操作同一个仓库：一种是每次调用一个结构化小工具，另一种是写一段 Python，把多个读、搜索、修改和测试操作组合起来。已有论文说明这两种接口会改变性能和轨迹，但没有清楚回答：当底层能力完全一样时，接口本身会不会改变 agent 被恶意仓库内容诱导的概率。

我的实验从真实 SWE-bench repair tasks 出发，为每个任务做一个最小改动的 adversarial pair。然后让同一个模型在 Atomic/Python × clean/adversarial 四个条件下运行。两个接口最终都经过同一套 backend，所以不是“一个权限大、一个权限小”。我会同时测修复成功、违规尝试、真实副作用、攻击成功、safe failure、tokens、tool calls 和时间，并分析攻击内容何时进入上下文、agent 何时开始服从。核心判断不是哪个条件 ASR 更低，而是攻击相对 clean baseline 造成的额外退化是否因 interface 而不同。

### 22.2 课题价值

- 对 agent builder：决定应把能力暴露为细粒度工具还是可编程接口；
- 对 benchmark designer：说明 security benchmark 需要控制 interface 和 clean baseline；
- 对 security engineer：区分 agent 的违规倾向与 sandbox 的拦截效果；
- 对软件工程研究：把真实修复正确性与执行安全放在同一个可复现实验中。

### 22.3 核心成功标准

课题成功不要求找到“Atomic 更安全”。成功标准是：在 capability matching 经验证、任务配对成立、oracle 可靠的前提下，对 interface effect 给出可信的方向、大小、不确定性和适用边界。

---

## 23. Recommended Paper Structure

1. Introduction：interface 行为效应与 repository security 的交叉缺口；
2. Background：repository agents、action representation、indirect prompt injection；
3. Study Design：paired $2\times2$、estimands 和 hypotheses；
4. Capability-Matched Harness：canonical backend 与 equivalence validation；
5. Benchmark Extension：task pairs、$P^*$、attack families 和 oracle；
6. Metrics and Analysis：safe resolution、attempt/effect decomposition、cost；
7. Results：RQ1–RQ5；
8. Mechanism Analysis：exposure、compoundness、feedback timing；
9. Threats to Validity；
10. Related Work；
11. Discussion and Design Implications；
12. Conclusion。

---

## 24. References and Evidence Base

以下列表优先给出原论文或官方项目页面。2026 年的新工作可能仍是预印本，应在投稿前再次核验版本、作者、venue 和出版状态。

### Repository-level coding agents and interfaces

1. Jimenez, C. E., et al. **SWE-bench: Can Language Models Resolve Real-World GitHub Issues?** ICLR 2024. [Paper](https://arxiv.org/abs/2310.06770) · [Code/Benchmark](https://github.com/SWE-bench/SWE-bench)
2. Yang, J., et al. **SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering.** NeurIPS 2024. [Official proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/5a7c947568c1b1328ccc5230172e1e7c-Abstract-Conference.html) · [Code](https://github.com/SWE-agent/SWE-agent)
3. Wang, X., et al. **SWE-bench-Live: Can AI Agents Resolve Real-World GitHub Issues on the Fly?** arXiv preprint, 2025. [Paper](https://arxiv.org/abs/2505.23419) · [Dataset](https://huggingface.co/SWE-bench-Live)
4. Wang, X., et al. **Executable Code Actions Elicit Better LLM Agents.** ICML 2024. [Paper](https://arxiv.org/abs/2402.01030) · [Code](https://github.com/xingyaoww/code-act)
5. OpenHands Team. **OpenHands: An Open Platform for AI Software Developers as Generalist Agents.** [Project](https://github.com/All-Hands-AI/OpenHands)
6. **The Devil Is in the Interface: Evaluating How Tool Architecture Shapes Coding Agent Behavior.** arXiv preprint, 2026. [Paper](https://arxiv.org/abs/2608.11386) · [Code](https://github.com/XZ-X/tool-arch-study)

### Agent attacks and execution security

7. Debenedetti, E., et al. **AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.** NeurIPS 2024 Datasets and Benchmarks Track. [Official proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html) · [Code](https://github.com/ethz-spylab/agentdojo)
8. Zhang, Z., et al. **Agent Security Bench (ASB): Formalizing and Benchmarking Attacks and Defenses in LLM-based Agents.** ICLR 2025. [Paper](https://arxiv.org/abs/2410.02644) · [Code](https://github.com/agiresearch/ASB)
9. Li, D., et al. **RepoGuardBench.** ICML 2026 DL4C Workshop / non-archival project. [Project and benchmark](https://github.com/DaoyuanLi2816/RepoGuardBench)
10. Singh, A., Yang, J., and Chen, T.-H. **IssueTrojanBench: Benchmarking AI Coding Agents Against Malicious Issue Requests.** arXiv preprint, 2026. [Paper](https://arxiv.org/abs/2607.20759)
11. Jiang, F., et al. **RedCode: Risky Code Execution and Generation Benchmark for Code Agents.** arXiv preprint, 2024. [Paper](https://arxiv.org/abs/2411.07781) · [Code](https://github.com/AI-secure/RedCode)
12. Ge, Y., et al. **Execution-Grounded Security Testing for Coding Agents in Software Engineering Pipelines.** arXiv preprint, 2026. [Paper](https://arxiv.org/abs/2607.22569)

### Policy, permission, and evaluation context

13. **Progent: Programmable Privilege Control for LLM Agents.** arXiv preprint, 2025. [Paper](https://arxiv.org/abs/2504.11703) · [Code](https://github.com/sunblaze-ucb/progent)
14. **Permission Denied: Policy-Graded Evaluation of Coding Agents in Hardened Environments.** arXiv preprint, 2026. [Paper](https://arxiv.org/abs/2608.02670) · [Code](https://github.com/boundary-bench/boundary-bench)
15. Fan, L., et al. **The Granularity Mismatch in Agent Security: Argument-Level Provenance Solves Enforcement and Isolates the LLM Reasoning Bottleneck.** arXiv preprint, 2026. [Paper](https://arxiv.org/abs/2605.11039)
16. **SNARE: Adaptive Scenario Synthesis for Eliciting Overeager Behavior in Coding Agents.** arXiv preprint, 2026. [Paper](https://arxiv.org/abs/2605.28122)
17. **The Verifier Tax: Horizon Dependent Safety Success Tradeoffs in Tool Using LLM Agents.** arXiv preprint, 2026. [Paper](https://arxiv.org/abs/2603.19328)

---

## 25. Final Research Statement

本研究不再把 interface 与 privilege 同时作为两个僵硬的处理因素，而是把权限和执行边界固定，集中研究一个更清晰的因果问题：

> 在真实 repository repair tasks 上，当 Atomic structured tools 与 restricted Python orchestration 具有相同底层能力时，它们是否因为产生不同的 agent trajectories，而表现出不同的攻击暴露、违规尝试、真实副作用、safe resolution 和运行成本？

方法上，研究通过 SWE-bench 功能任务与自建 paired security extension 结合，既保留真实软件工程任务的生态效度，又获得 clean/adversarial 的可控对照。共享 canonical backend 排除能力差异；$P^*$ 提供任务级安全真值；执行日志和环境状态 oracle 将模型意图、违规尝试和真实后果分开；配对 interaction estimand 则区分一般 performance difference 与 attack-specific susceptibility。

最强的可辩护结论将不是“某接口绝对安全”，而是：在明确的模型、任务、攻击和能力边界下，action representation 对 coding-agent execution security 是否构成独立、具有实践意义的系统设计因素，以及该影响通过何种轨迹阶段出现。
