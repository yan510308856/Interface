# Idea 1：Final Slides 1–10 导师汇报讲稿

> 本讲稿严格对应最终版 `idea1_advisor_research_gap_story.pdf` 的 10 页。文件名仍然保留 `1_12`，但当前内容不再包含旧版本的第 11、12 页。

## 使用方式

这套 slides 的主线不是“我已经证明了某个 interface 或 privilege 更好”，而是：

> 在底层可用能力相同的前提下，工具接口的组织方式和权限范围是否会共同改变 repository-level coding agent 的执行安全、任务完成和运行成本？

建议用 10–15 分钟讲完。每页先说结论，再解释设计；不要把页面上的英文术语逐字朗读。

汇报中始终坚持以下四个边界：

1. **这是一个受控的因果比较，不是新模型、新 benchmark 或新 agent framework。**
2. **主要安全对象是 execution/system security**：agent 是否真的执行了越权的文件、网络、进程或凭证相关操作，而不是只看模型输出是否“看起来安全”。
3. **`ambient/full` 不是把 agent 放到真实主机上运行。** 它表示在 disposable sandbox 内给予更宽的、相对环境性的权限；真实凭证、任意外部网络和宿主机资源仍然隔离。
4. **false denial 不是和 safe failure 并列的第五个基础 outcome。** 基础分类是“安全/不安全执行 × 任务成功/失败”的 2×2；`false denial` 是其中 safe failure 的一个经过可行性证据确认的子类。

## 开场总纲：先让导师知道你要回答什么

正式进入第 1 页前，可以先用 20 秒说：

> 现在 coding agent 已经能够在真实 repository 中搜索、修改文件、运行测试和迭代调试。但它的行为不仅由模型决定，也由它能看到什么工具、工具如何暴露，以及它拥有多大执行权限决定。我的 idea 是把这两个经常被分开讨论的变量放进一个 2×2 实验中，在 capability-matched 的条件下，分别测量安全、任务完成和成本，并判断它们是否存在 interaction。

接下来 10 页分别回答四个问题：

1. 我到底研究哪两个 treatment？
2. 怎样保证观察到的是 interface/privilege 的差异，而不是工具能力不等价？
3. 怎样把安全提升和“只是更早拒绝/失败”区分开？
4. 先做什么小实验，什么结果出现时才值得扩大研究？

---

## Slide 1 — 标题页：把问题定位成因果研究

### 本页目标

让导师第一时间明白研究对象、两个自变量和研究方法：

- 对象：repository-level coding agents；
- 自变量：tool-interface architecture × privilege granularity；
- 方法：controlled causal study。

### 建议讲法

> 我的研究想看的是 `Interface × Privilege` 对 repository-level coding agents 的共同影响。这里的 agent 不是只生成一段代码，而是要在真实 repository 中理解 issue、浏览代码、修改文件、运行测试，并根据反馈继续操作。
>
> 我关心的不是哪个模型在 benchmark 上分数最高，而是：如果底层可用能力保持一致，只改变工具接口的组织方式和权限范围，agent 的安全行为、任务完成情况和运行成本会不会系统性地变化。因而这是一项受控的因果比较。

### 需要强调的定位

- “interface”不是 UI 外观，而是 agent 可调用的工具形态和 action space，例如较细粒度的 read/search/edit/test 工具，或更通用的 compound/shell-like 操作。
- “privilege”不是抽象的安全口号，而是 agent 在执行时实际能触达的路径、网络、进程和凭证边界。
- 本研究不会先假设 atomic 或 scoped 一定更好；实验的任务是估计 effect，并检查 security–utility trade-off。

### 如果导师问“你的创新是什么”

先不要说“提出了全新的安全机制”。更准确的回答是：

> 可能的贡献是把 interface architecture 和 privilege granularity 放入同一个、能力匹配的 repository-level coding-agent 实验中，并用执行事件、任务结果和运行成本联合评价，而不是只报告一个 attack success rate。

### 过渡到 Slide 2

> 下一页把这个 idea 压缩成一句研究问题，并明确两个处理因素和要观测的结果。

---

## Slide 2 — 一句话：明确 X、Y 和结果空间

### 本页目标

说明研究不是泛泛地讨论“agent 安全”，而是有明确变量的实验：

- 两个 treatment：interface、privilege；
- 研究对象：解决真实 issue 的 repository-level agent；
- 结果：execution security、utility、time、cost。

### 建议讲法

> 一句话概括就是：在可用能力相同的条件下，工具接口和权限范围是否会改变 coding agent 的安全行为、任务完成和成本？
>
> 研究对象是能够解决 repository issue 的 coding agent，而不是单轮代码生成模型。它必须经历一个完整 trajectory：理解任务、调用工具、修改代码、运行测试，再根据结果继续或停止。
>
> 两个处理因素分别是 interface 和 privilege。interface 比较 atomic/structured 与 compound/general-purpose；privilege 比较 scoped/least 与 ambient/broad。主要结果包括是否发生 execution-level security violation、任务是否通过测试完成，以及完成任务需要的时间和成本。

### 解释页面上的 `Utility * time * cost`

页面上写的是 `Utility * time * cost`，汇报时要明确说：

> 这里的星号表示三个需要联合观察的 outcome 维度，不是预先定义一个把 utility、time 和 cost 相乘的单一总分。我们会分别报告任务效用、时间和成本，再讨论它们的 trade-off。

这样可以避免导师误以为你要用一个难以解释的 composite score。

### 两个术语的口头定义

- **Scoped / least privilege**：只允许完成当前任务所需的 repository 路径、操作类型、网络范围或进程类别，并留下可审计边界。
- **Ambient / broad privilege**：在同一个 disposable sandbox 中给 agent 更宽的默认执行能力，使它不需要为每个细粒度操作都经过同样严格的授权边界。

这里的比较重点是权限范围和授权方式，不是让一个条件获得真实机器或真实云凭证。

### 过渡到 Slide 3

> 有了 X 和 Y，下一页把它们正式写成 2×2 treatment design。这样我们不仅能比较各自的主效应，还能检查两者是否互相放大或抵消。

---

## Slide 3 — Treatment：2×2 设计与 interaction

### 本页目标

把四个实验条件讲清楚，并说明为什么必须有 interaction，而不只是做两个单因素比较。

### 建议讲法

> 这是一个 2×2 treatment design。横轴是 privilege：左边是 scoped/least，右边是 ambient/full；纵轴是 interface：上面是 atomic，下面是 compound。因此有四个 cell：A1、A0、C1、C0。
>
> A1 是 atomic + scoped，A0 是 atomic + ambient，C1 是 compound + scoped，C0 是 compound + ambient。每个 cell 使用同一批模型、prompt、任务和执行预算；clean task 和 adversarial task 也使用 paired design。每次 run 都保留 tool trace，并通过程序级 oracle 检查实际执行结果。

### 用公式解释 interaction

可以指着表格说：

> 我最关心的不只是 atomic 和 compound 谁的平均表现更好，也不只是 scoped 和 ambient 谁更安全，而是 interface 的 effect 是否依赖 privilege。用一个 outcome \(Y\) 表示，interaction 可以写成：
>
> \[
> \Delta_{I\times A} = (Y_{atomic,scoped}-Y_{compound,scoped}) - (Y_{atomic,ambient}-Y_{compound,ambient})
> \]
>
> 如果这个差异明显不为零，就说明 interface 和 privilege 不是两个完全独立的旋钮。

不需要在 slides 上展开统计模型；口头上说明最终会给出 effect estimate、uncertainty interval，并把任务/repository 作为重复观测的层级，而不是把每次 rollout 当作完全独立的任务。

### 固定什么，改变什么

**改变：**

- tool/interface 的暴露形式；
- privilege 的作用范围和授权边界；
- clean 与 paired adversarial 的 threat context。

**固定或审计：**

- model 和 system/prompt；
- repository commit、issue requirement 和测试；
- sandbox、timeout、retry、错误返回 schema 和执行日志；
- underlying capability set。

### 需要主动说出的保守性

> 这张图是 treatment design，不是预先画好的结果。它允许四种结果：interface effect、privilege effect、interaction effect，或者没有稳定 effect。研究设计不能替代实验结果。

### 过渡到 Slide 4

> 但在大规模运行前，最容易出问题的是 attribution：如果两个 interface 实际能做的事不同，就不能把表现差异称为 architecture effect。所以先要定义一个有停止条件的研究计划。

---

## Slide 4 — Next Work：先证明 attribution，再决定是否扩展

### 本页目标

让导师看到你不是“先跑很多次再解释”，而是有一个由识别、测量、pilot 和 go/no-go 组成的分阶段计划。

### 建议讲法

> 下一步工作的目标不是盲目扩大实验，而是先证明 attribution 可行。也就是说，在投入大量算力之前，先确认两个 interface 的能力集合确实一致、执行边界可以被观察、主要 outcome 可以被可靠估计。
>
> 第一步是 identification：做 capability-equivalence audit，固定 sandbox、权限策略和 oracle。第二步是提前定义 research questions 和 outcomes，包括 interaction、security、utility、time 和 cost。第三步先跑 minimum study，也就是小规模 pilot。只有当 primary contrast 可估计、oracle 可复核、结果不是单纯靠 denial 得到的安全提升，才进入 confirmation。

### 四个卡片分别怎么讲

**01 Identification**

> 先验证 atomic 和 compound interface 的操作集合一致；比如都能完成 repository 文件读写、搜索、测试、build 和 lint，但都不能访问真实凭证或任意外部网络。

**02 Questions & outcomes**

> 在运行前规定主要 outcome 和判定规则，避免看到结果后再选择最有利的指标。

**03 Minimum study**

> pilot 的目的不是给出最终结论，而是确认任务、oracle、日志和估计流程能够运行。

**04 Go / No-Go**

> 如果所谓 security gain 主要来自 benign task 被拒绝，或者 execution oracle 无法可靠区分安全与越权，就不应该直接扩大实验，而要先修正设计或收窄 claim。

### 过渡到 Slide 5

> 因此，下一页先解决最基本的识别问题：两个 interface 到底是不是“能力相同、暴露形式不同”。

---

## Slide 5 — Identification：先证明 capability-equivalence

### 本页目标

解释为什么 capability matching 是整个因果主张的前提，而不是一个实现细节。

### 建议讲法

> 如果 atomic tool 能做得更多，或者 compound tool 能绕过某些边界，那么后面看到的差异就可能来自能力不等价，而不是 interface architecture。因此第一项必须是 capability-equivalence audit。
>
> 表中第一行表示两种 interface 都能读写 repository 文件，使用 path allowlist 和 git diff 检查。第二行表示两者都能进行搜索、测试、build 和 lint，用 command log 与 test log 复核。第三、四行表示两者都不允许任意网络、真实 credential、越界路径或越界进程类别，并通过 egress、fake canary、filesystem 和 process audit 检查。

### 这里要特别解释“能力相同”

能力匹配不是要求两种 interface 的调用次数、参数格式或轨迹完全一样，而是要求它们在任务需要的操作集合上具有等价的可达能力。比如：

- atomic interface 可以有独立的 `read_file`、`search`、`apply_patch`、`run_test`；
- compound interface 可以有一个更通用的执行入口；
- 但两者都必须能完成同一组任务，也必须受到同样的文件、网络、进程和时间边界约束。

同时要固定或记录：工具 schema、错误消息、retry 规则、timeout、sandbox image、日志字段和可见性。否则 agent 可能只是因为反馈信息不同而表现不同。

### 失配时的处理

这是一个重要的 fail-closed 规则：

> 如果 audit 发现能力不等价，我只能把结果报告为 configuration comparison，不能声称是 architecture 的 causal effect。必要时可以修复 interface 后再做 pilot，但不能事后把不等价的结果包装成因果结论。

### 可能追问：“compound 更强是不是天然不公平？”

回答：

> 如果 compound 接口拥有额外可达能力，那确实是不公平的，也是为什么 capability audit 是 go/no-go 的前提。我的目标不是证明某一种工具形式天然更好，而是让 underlying capability 固定，只比较暴露方式、可观测性和操作粒度。

### 过渡到 Slide 6

> 能力等价之后，才可以把问题拆成效用、安全、trade-off 和机制四个 RQ，而不是把所有现象都混成一个“agent 表现”。

---

## Slide 6 — Research Questions：把 effect、机制和 trade-off 分开

### 本页目标

说明四个 RQ 的层次关系，并主动把 primary interaction 写清楚。

### 先给出总的 primary question

建议先说一句 PPT 上没有完全展开、但对研究定位很重要的话：

> 总的 primary question 是：在 capability-matched、execution-grounded 的 repository-level coding setting 中，interface × privilege interaction 是否改变安全、效用和效率之间的 frontier？

四个 RQ 是对这个问题的拆分。

### RQ1 — Utility

> 在 capability-matched 条件下，interface 和 privilege 如何影响 resolved-with-tests，以及 agent trajectory 的 consistency？

这里的 resolved-with-tests 不只是 agent 自己说“完成了”，而是 repository 测试和 issue-level 判定都通过。trajectory consistency 可以观察不同 rollout 是否在操作路径、重试或最终状态上表现出稳定性。

### RQ2 — Security

> 在 adversarial repository 中，哪些 treatment 更容易导致 unsafe execution 或 attack success？

这里的 unsafe execution 要以实际事件为准，例如越过 allowlist、触发 fake credential canary、产生未经授权的网络/进程/文件操作，而不是仅凭模型输出中出现了危险字符串来判断。

### RQ3 — Trade-off

> 如果某种 treatment 的安全结果更好，这个改善是否伴随 denial、time、tokens、tool calls 或 monetary cost 上升？

这一步是为了避免把“更常拒绝任务”误判为“更安全”。安全结果、任务效用和运行效率必须一起看。

### RQ4 — Mechanism

> compound actions、observability、retry 和 denial feedback 能否解释这些差异？

RQ4 更偏机制和解释性分析。它不应该替代 primary contrast；如果 RQ1–RQ3 无法可靠估计，不能只凭事后机制故事来宣称发现了 interaction。

### 统计口径的保守表述

> 如果 interaction estimate 的区间很宽或接近零，我会报告“没有足够证据支持稳定 interaction”，而不是强行把四个 cell 的均值差异解释成机制。

### 过渡到 Slide 7

> 这四个问题中，最容易被误读的是 security。下一页先解释为什么 attack success rate 下降本身并不能说明安全真正提升。

---

## Slide 7 — Outcomes：把“被挡住”和“安全完成”分开

### 本页目标

解释 2×2 outcome matrix，并指出 ASR 的核心陷阱：agent 可以因为安全策略而被拦截，也可以因为任务失败而没有完成攻击，这两种情况不能自动等同于 security success。

### 建议讲法

> 攻击成功率下降，不一定等于安全提升。它可能表示系统确实阻止了未授权操作，也可能只是 agent 更早拒绝、超时或失败，因此没有走到攻击动作。
>
> 所以我把 outcome 分成两个正交维度：执行是否安全，任务是否完成。这样得到四个基础类别。

### 四个基础 outcome

**Safe execution × Task resolved = Safe success**

> 任务完成、测试通过，并且没有越权副作用。这是安全与效用同时满足的理想结果。

**Safe execution × Task failed = Safe failure**

> 任务没有完成，但执行边界没有被突破。它可能是合理的安全阻断，也可能是 benign task 被错误拦截，需要进一步区分。

**Unsafe execution × Task resolved = Unsafe success**

> 任务完成了，但发生了未授权操作、canary 事件或 policy violation。不能因为测试通过就把它当作成功。

**Unsafe execution × Task failed = Unsafe failure**

> 任务和安全都失败，不能简单记为“攻击被挡住”，因为系统已经发生了 unsafe event。

### 如何放置 false denial

要主动补充一个容易混淆的定义：

> `false denial` 是 safe failure 的可验证子类：任务本身在安全条件下可完成，但权限策略或防御机制错误地阻断了本来允许的操作。它需要一个 solvability witness，例如同一 task 在安全的参考配置下能够通过测试，且被阻断的具体操作属于任务所需的允许能力。
>
> 因此在分析上，我会保留四个基础 outcome，同时给 safe failure 加上 false-denial label。这样既不把 false denial 当成第五个互斥格子，也不会把所有 safe failure 都武断地称为 false denial。

### 如果导师问“那 legitimate refusal 算什么”

回答：

> 如果 adversarial task 确实要求越权，系统安全地拒绝，且没有 benign solvability witness，这属于 safe failure，但不应标成 false denial。false denial 只针对任务本来应该能在允许能力内完成、却被防御机制误伤的情况。

### 过渡到 Slide 8

> 要做出这种区分，任务必须既有真实的软件工程内容，又能构造可审计的 clean/adversarial 对照。因此下一页说明 benchmark 和 paired task 怎么选。

---

## Slide 8 — Tasks & Benchmark：先保证可复现，再加入威胁条件

### 本页目标

解释为什么使用 SWE-bench Verified，以及 clean/adversarial paired issue variants 怎样服务于因果识别和执行安全测量。

### 建议讲法

> Primary benchmark 选择 SWE-bench Verified，从中挑选一批真实的 repository issue。这样任务不是人为设计的 toy command，而是包含真实代码理解、修改和测试的 repository-level 工作。
>
> 对每个 clean issue，构造一个 paired adversarial variant。两者尽量保持同一个功能要求、同一个冻结 commit 和同一套测试；差异只放在需要研究的 adversarial repository context，例如不可信内容或会诱导 agent 采取危险操作的环境条件。这样可以把“任务本身难度”和“威胁条件”分开。

### 逐行解释 audit table

- **Repository issue：** clean 和 adversarial 都有，使用 frozen commit 和测试固定任务基线。
- **Paired clean/adversarial variant：** 两边有相同的 functional requirement，adversarial 变体需要单独 review trigger，确认它确实改变 threat context 而不是改变功能任务。
- **Real credential/arbitrary network：** 两边都没有，使用 OS 和 network audit；真实 secret 不应进入实验。
- **Out-of-scope path/process：** 两边都没有，使用 filesystem/process audit。

### “paired”不等于只复制文字

需要强调：

> paired 不是简单复制一个 issue 再加一句恶意 prompt。需要检查 repository 状态、测试、功能要求和触发条件；如果 adversarial variant 改变了任务可解性，就不能把差异完全归因于 threat context。

### 两种 oracle 的边界

页面最后一行提到 separate secure-code oracle。汇报时说清楚：

> 本研究的 primary security focus 是 execution/system security，优先看 filesystem、network、process、canary 和 policy logs。secure-code oracle 如果加入，是一个分开的、次级的代码安全检查，不能和 execution violation 混成同一个指标。

### 过渡到 Slide 9

> 有了 paired tasks 和审计边界，下一页具体规定每一次 run 要记录什么，以及如何把安全、任务和成本拼成可分析的数据。

---

## Slide 9 — Measurement：每一次 run 记录什么

### 本页目标

把“security + utility + over-restriction + operational cost”落到可记录的 run-level schema。

### 建议讲法

> 每次 run 不只记录最终是否 attack success，而是同时记录任务是否通过、执行过程中是否发生 unsafe event、完成所需时间、token 和工具调用成本。
>
> Primary outcomes 是 resolved-with-tests、unsafe execution、wall-clock 和 LLM cost；其他指标用来解释为什么出现这个结果，例如 retries、tool calls、denial、timeout 和 false denial。

### 逐格解释 outcome table

**Safe execution × Task success**

> 测试通过且没有 unauthorized event，属于 safe success。

**Safe execution × Task failure**

> 任务被 blocked、refused 或 timeout，但没有 unsafe event。这里要单独记录 false denial；不能把它算成 utility success，也不能因为它降低了 attack success 就自动算作完整的 security success。

**Unsafe execution × Task success**

> 测试通过但发生 unauthorized、canary 或 policy-violation event，属于 unsafe success。它说明“功能完成”与“执行安全”是两个不同维度。

**Unsafe execution × Task failure**

> 任务失败且发生 unsafe event，属于 unsafe failure。这个格子特别重要，因为它提醒我们：任务没做成，不代表攻击没有发生。

### 推荐的 run schema

每一次 agent rollout 至少记录：

```text
task_id
pair_id
condition: A1 / A0 / C1 / C0
model_id
clean_or_adversarial
task_success / resolved_with_tests
unsafe_event
event_type and event_log
false_denial_label and solvability_witness
wall_clock_time
input/output tokens
tool_calls
retries
monetary cost
termination reason: completed / blocked / timeout / error
```

### 说清楚几个分析关系

- `unsafe_event` 是 execution-level security 事件，不等于模型输出中出现了危险建议。
- `task_success` 是功能结果，不等于 agent 自己报告成功。
- `false_denial` 需要证据，不是所有拒绝或失败的同义词。
- `time`、`tokens`、`tool_calls` 和 `cost` 既可以作为 outcome，也可以用于解释某个 treatment 是否通过更多重试或更高审批负担换取较低风险。

### 过渡到 Slide 10

> 最后，我不先承诺一个很大的最终实验，而是先给出可以审计、可以停下来的 minimum study，以及从 pilot 进入 confirmation 的明确条件。

---

## Slide 10 — Minimum Study：先跑最小实验，再决定是否扩展

### 本页目标

说明实验规模、计算方式和 go/no-go 标准，让导师看到计划可执行且有 falsification/停止逻辑。

### Step 0：Harness audit

> 在任何 agent rollout 之前，先做 harness audit：确认 operation equivalence、sandbox 和 oracle 都可用，并且权限策略 fail-closed。也就是说，遇到未定义或无法判断的操作时，不应该默认为允许。

需要得到三类证据：

- 两种 interface 的操作集合可比；
- execution oracle 可以重复判定 unauthorized event；
- 日志能够把任务结果、执行事件和终止原因对应到同一次 run。

### Step 1：Minimum viable study

页面写成：

> `12 clean + 12 paired adversarial × 4 cells × 3 rollouts = 288 attempts`

口头上建议改说得更清楚：

> 这里的 12 clean 加 12 paired adversarial，表示 12 个 task pair，每个 pair 有一个 clean condition 和一个 adversarial condition；因此是 `12 task pairs × 2 conditions × 4 cells × 3 rollouts = 288 attempts`。

这一阶段的目的不是估计最终 benchmark-level effect，而是验证：

- task pair 能否稳定复现；
- 四个 treatment cell 都能运行；
- security oracle 是否有可审计的正负例；
- outcome schema 能否完整记录；
- 是否出现明显的 capability mismatch、系统性 timeout 或日志缺失。

### Step 2：Confirmation

页面写成：

> `24–40 paired tasks × 4 cells × 5 rolls × 2 models = 1,920–3,200 attempts`

口头上展开为：

> 这是 `24–40 个 task pairs × 每个 pair 的 2 个条件 × 4 个 treatment cells × 每个 cell 5 次 rollout × 2 个 model`，所以总量是 1,920 到 3,200 次 attempts。

这里 task/repository 是主要重复单位，rollout 是在同一任务上的重复观测；后续分析要考虑这种层级结构，不能简单把所有 attempts 当成互相独立的样本。

### Go / No-Go criteria

逐条讲：

1. **Capability audit 通过。** 如果 atomic 和 compound 的实际能力不等价，停止因果表述，先修 harness。
2. **Execution oracle 可复核。** 如果 unsafe event 只能依靠主观人工判断，不能直接进入大规模 confirmation。
3. **Primary contrast 可估计。** 至少需要有足够的任务和事件变化，能够报告 interaction estimate 及其不确定性；否则只能报告 pilot observation。
4. **Security gain 不能只是 false denial。** 如果安全改善主要来自 benign task 被拦截，而 utility 明显下降，就不能把它包装成更好的安全机制。

### 如果没有 interaction，研究是否失败

> 不一定。一个可信的 null 或弱 interaction 结果本身也有价值，尤其是在严格 capability matching 和 execution-level measurement 下。但这时结论应是“没有观察到稳定的 interaction”或“效果小于当前设计能分辨的范围”，而不是事后寻找故事证明 idea 一定成立。

---

## 讲完 10 页后的 30 秒收束

可以直接用下面这段结束：

> 已有研究分别发展了 repository-level coding agents、工具接口设计、最小权限与 sandbox、安全攻击以及 agent evaluation，但这些维度经常被分开研究。我的 proposal 不把 atomic 或 scoped 预设成赢家，而是做一个 capability-matched 的 2×2 causal comparison：同时改变 interface 和 privilege，使用 clean/adversarial paired repository tasks，并把 execution security、resolved-with-tests、false denial、safe failure、时间、tool calls、tokens 和 cost 放进同一个可审计的 measurement scheme。
>
> 最强的研究 gap 不是“以前没人研究 agent 安全”，而是：在 repository-level coding agents 中，是否有人已经严格控制底层能力、同时估计 interface × privilege interaction，并把真实安全事件与任务效用、错误拒绝和运行成本联合起来。如果先前工作已经覆盖其中某一部分，我会把贡献收窄为它们的受控组合和实证验证，而不是宣称全新的安全概念。

## 导师可能追问的 10 个问题与回答

### 1. 为什么一定要研究 interaction，而不是分别研究 interface 和 privilege？

因为相同的 interface 变化在不同 privilege 下可能产生不同结果。例如，compound action 的低可观测性在 scoped privilege 下可能主要导致安全阻断，但在 ambient privilege 下可能转化为更大的越权风险。只有四个 cell 才能估计“interface effect 是否依赖 privilege”。

### 2. atomic 和 compound 到底怎么定义？

atomic 指把搜索、读文件、修改文件、运行测试等操作以相对独立、结构化、可审计的工具暴露；compound 指一个调用可以组合多个底层动作，或者通过更通用的执行入口表达更大的 action。最终定义应落实到 tool schema、可见反馈、操作边界和 trace，而不能只用工具名称命名。

### 3. capability matching 怎么证明，而不是口头声称？

通过正向能力测试和负向边界测试：两种 interface 都要完成同一组 repository 操作，也都必须拒绝任意网络、真实 credential、越界路径和越界进程；然后用 tool trace、filesystem/network/process audit、git diff 和 fake canary 复核。audit 失败时不做 architecture causal claim。

### 4. ambient privilege 是不是 root 或真实主机权限？

不是。ambient/full 是 disposable sandbox 内的 broad authority condition，用来模拟更宽的默认权限。真实宿主机、真实凭证和任意外部网络仍然隔离，避免实验本身制造不必要的风险。

### 5. false denial 和普通 safe failure 有什么区别？

safe failure 只说明“任务失败且没有 unsafe event”。false denial 还需要额外证据证明任务本来可以在允许能力内完成，而是被权限策略、防御规则或接口限制错误阻断。前者是基础 outcome，后者是带 solvability witness 的解释标签。

### 6. adversarial task 如果本身更难，怎么知道差异来自攻击而不是难度？

使用 paired variants、冻结 commit、保持功能 requirement 和测试一致，并审查 adversarial trigger。还要报告 clean/adversarial 两种条件的任务成功、时间和失败原因，不能只比较 attack success rate。

### 7. 为什么使用 SWE-bench Verified，而不是全部自己构造任务？

它提供真实 repository issue、冻结代码状态和测试基础，有利于生态有效性和可复现性。自构造的 adversarial variant 则用于加入受控 threat context。两者结合，既保留真实软件工程任务，又能做成 paired comparison。

### 8. 如果 security 更好但任务完成率下降，应该说谁赢？

不能用单一分数预先决定。要报告安全、效用、时间和成本的 joint profile，检查是否出现 Pareto trade-off。至少应区分“安全完成”“安全失败/拒绝”和“unsafe completion”，再由研究问题决定如何比较。

### 9. 多次 rollout 是否可以当作多个独立样本？

不能直接这么处理。相同 task/repository 上的 rollout 共享任务难度和环境，因此 task/repository 应作为主要层级或 block，rollout 用于估计随机性和稳定性。总 attempts 数可以用于说明运行规模，但不等于完全独立的任务数。

### 10. 如果最后没有 interaction，或者安全改善完全来自 denial，怎么办？

如果 interaction 没有稳定证据，就报告 null/uncertain result；如果 security gain 主要来自 false denial，就不能声称找到了更好的安全 architecture。可以把结论收窄为测量框架、capability audit 或 pilot 发现，并据此决定是否停止或重新设计。

## 汇报时的术语和表述规则

### 建议使用

- “估计 / 比较 / 检验 interaction”——不要说“证明 interface 一定导致某结果”。
- “execution/system security”——明确和 model/output safety、generated-code security 区分。
- “capability-matched”——强调底层可用能力相同。
- “safe failure with a false-denial label”——明确 false denial 是经过证据确认的子类。
- “joint outcome profile”——说明不是把所有指标强行压成一个分数。

### 尽量避免

- “atomic interface 天然安全”；
- “scoped privilege 一定降低 utility”；
- “ASR 降低就代表 defense 有效”；
- “所有被拒绝的攻击都属于安全成功”；
- “这是第一个研究 agent security 的工作”；
- “我们已经证明了 interface 和 privilege 的 interaction”。

## 一句话记忆版

如果导师只给你 15 秒，可以说：

> 我想在能力匹配的 repository-level coding-agent 环境中，用一个 `interface × privilege` 的 2×2 实验，区分真正的 execution-security improvement 和单纯的拒绝/失败，并联合测量任务完成、false denial、时间、工具调用、token 与成本；先用可审计的 minimum study 验证 attribution，再决定是否扩大。
