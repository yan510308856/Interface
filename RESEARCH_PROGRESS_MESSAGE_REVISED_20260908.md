# 给导师的阶段性汇报：从 Atomic/Python 接口比较到 Action-Boundary Granularity

老师您好，我这两天结合目前实验里遇到的问题，又重新梳理了一下相关文献、已有实验结果和代码里的实际执行路径。我这段时间做的工作，主要不是简单地继续增加实验数量，而是先把原来的实验到底在操纵什么变量重新核对了一遍：我重新看了 Atomic 和 Restricted Python 的 interface/backend 调用链，审计了之前九个任务的真实 trajectory，检查了 G1/G2/G4 pilot 中模型到底有没有使用 multi-operation capacity，也重新整理了攻击实验和相关文献。做完这些以后，我感觉相比单纯把实验定义成“Atomic interface vs. Restricted Python interface”，把问题进一步抽象成 **action-boundary granularity（动作边界/动作粒度）**，可能会让整个课题的逻辑更加清楚，也更容易形成一个严格的 controlled experiment。

我先简单回顾一下最初的设计。我们最初设计 Atomic 和 Restricted Python，本质上希望它们虽然拥有完全相同的底层能力、权限和 execution backend，但是在 agent 与环境交互的方式上产生不同的 trajectory。Atomic interface 是一次 LLM action 只能对应一次 canonical backend operation，例如 read、search、write、execute 等；模型必须得到这一次 operation 的 observation 之后，才能决定下一步。Restricted Python 则允许模型在一次 action 中写一段受限 Python program，在这段程序内部连续执行多个 backend operations，甚至根据前一个 operation 的返回值进行条件判断、循环或者后续操作，最后整个 Python action 结束以后，再把汇总 observation 返回给 LLM。

所以最开始我们实际上隐含假设了一个区别：

```text
Atomic：
LLM decision → 1 backend operation → observation → next LLM decision

Restricted Python：
LLM decision → N backend operations → aggregated observation → next LLM decision
```

也就是说，我们真正想研究的其实不只是“JSON tool call 和 Python code 两种 representation 哪个好”，而是：**在底层 capability 完全相同的情况下，一个 LLM decision 与多少个 environment operations 绑定在一起，会不会改变 agent 的 trajectory，进而影响 task performance、security risk 和 resource cost。**

## 这段时间我先做了哪些工作

第一，我重新检查了 Restricted Python 的实际实现，而不是只看它在接口说明里“理论上支持什么”。在前面的校准过程中，我尝试过自然语言/代码片段、DSL、structured envelope、受限 AST、validation feedback 和静态 Python batch 等几种形式。这个过程里出现过比较多的协议摩擦：模型会输出 prose、代码围栏、普通 Python 语句、局部变量、`print`、`join`、`AugAssign` 等当前协议不允许的结构。即使底层 Backend 本身能够执行相应的 read、write 或 test，模型也可能因为没有遵守这个很窄的 Python action grammar 而产生 invalid action。

这让我意识到，原来的 Restricted Python 并不是一个单纯的“更强工具接口”。它同时引入了 Python syntax、program composition、control flow、局部计算、参数依赖和协议遵循等多个因素。只要这些因素混在一起，最后即使观察到 Atomic 和 Restricted Python 的差异，也很难说差异究竟来自 execution granularity，还是来自模型是否学会了这套特殊的语言协议。

第二，我对之前九个任务的真实 trajectory 做了更细的审计。结果比我原来预期的更关键：在历史 clean calibration 中，Atomic 有 27 个 run、640 个 model actions，没有 invalid action；Restricted Python 也有 27 个 run，但产生了 215 个 invalid actions。更重要的是，Restricted Python 实际执行的 864 个 backend operations 全部位于 single-operation action 中，真实的 multi-operation batch 比例是 0%。

这意味着，Restricted Python 在代码层面虽然允许一次 action 调用多个 backend operations，但真实模型运行时并没有真正使用这个能力。原本以为是在比较：

```text
Atomic：1 action → 1 operation
Restricted Python：1 action → N operations
```

但实际执行轨迹更接近：

```text
Atomic：1 action → 1 operation
Restricted Python：1 action → 1 operation
```

如果继续直接比较这两种 interface，会有一个比较严重的识别问题：如果最后 performance 或 security 没有差别，我们不能判断到底是“interface representation 不重要”，还是因为 Python interface 根本没有形成原来预期的 batching 行为；反过来如果出现差异，也很难判断差异来自 Python syntax、programming ability、control flow、invalid action 或 action granularity。

因此，这次审计对我来说不是简单地发现“Restricted Python 表现不好”，而是发现了一个 treatment-realization problem：**接口在实现层面允许某种能力，不等于模型在真实 trajectory 中实现了这种能力。** 这也是我觉得必须转换研究问题的主要原因。

## 我是怎么把问题重新定义的

我现在考虑把实验进一步 formalize 成一个更干净的 controlled variable：直接固定一次 action 最多可以提交多少个 backend operations，而不再把 Python representation 本身作为主要 treatment。

```text
G1 / Atomic-1：每一个 agent action 最多执行 1 个 backend operation；

G2 / Batch-2：每一个 agent action 最多执行 2 个 backend operations；

G4 / Batch-4：每一个 agent action 最多执行 4 个 backend operations。
```

这里的 G 是一个上限，不是要求模型一定填满的 quota。也就是说，模型没有合理的多个操作时，可以只提交一个 operation，不能为了凑满 batch 而加入 filler operation。同时，如果第二个操作依赖第一个操作的返回结果，那么它仍然必须等下一次 observation 以后再决定。这样 G 操纵的不是“能不能在 Python 里写任意程序”，而是：

**一次 LLM decision 到下一次 model-visible observation 之间，系统允许 agent 连续执行多少个已经确定的 primitive backend operations。**

三个处理仍然全部调用同一个 canonical backend，拥有相同的 read/write/create/delete/execute 能力，相同的 permission engine、repository、task、model、prompt framework、sandbox 和 budget，真正系统性变化的只有：

```text
一次 LLM decision 与环境之间允许发生多少次底层操作，
以及模型多久能够重新获得 observation 并 replanning。
```

所以现在的核心因果链可以写成：

```text
Action-boundary granularity G
        ↓
一次模型决策中可连续执行的 backend operations 数
        ↓
observation / decision checkpoint 的频率
        ↓
trajectory structure、错误恢复和验证方式
        ↓
task utility / execution-security risk / resource cost
```

Atomic 和 Restricted Python 在这个新框架里并不是完全消失了，而是从“研究问题本身”变成了“实现不同 action granularity 的 interface mechanism”。这样可以保留之前已经做好的 shared backend、permission 和 trajectory logging，同时去掉 Python syntax 对因果解释的干扰。

## 目前 pilot 暴露出的第二个问题

在把 G1/G2/G4 整理出来以后，我又做了一个 54-run 的 formal pilot，用来检查实验流程、产物记录、攻击注入和 granularity 是否真的被模型实现。这个 pilot 的结构是：

```text
3 tasks × 3 G × 2 conditions × 3 rollouts = 54 runs
```

54 个 run 的产物都完整、可解析，轨迹和哈希检查也没有出现流程层面的异常。但从模型实际使用 capacity 的情况看，结果并没有形成预期的单调关系：

```text
G1：0.998 operations / observation，visible multi-op 约为 0%；
G2：1.079 operations / observation，visible multi-op 约为 8%；
G4：1.030 operations / observation，visible multi-op 约为 3%。
```

G2 比 G1 高，但 G4 没有继续提高；G4 在这批 pilot 中最多只稳定观察到 2-operation batch，没有形成预期的 3/4-operation 行为。同时，49/54 个 run 达到了 action budget，只有 5/54 个 run 使用了 exact model finish。

这个结果让我进一步意识到，G1/G2/G4 的“硬性上限”已经能够执行，并不代表模型会自然地把更大的 capacity 用起来。也就是说，nominal treatment 和 realized treatment 需要分开记录。现在还不能根据这批 pilot 直接说 G4 更高效、更安全，甚至不能只根据 patch 数量或轨迹长度判断任务表现。当前 pilot 的主要价值，是帮助我确定正式实验前必须增加 calibration gate：先验证 G1/G2/G4 是否真的产生足够清晰的行为差异，再解释 performance、security 和 cost。

这个问题也和我们最初观察到的 Restricted Python 退化现象对应起来：

**给 agent 提供 multi-operation action capability，并不等于 agent 会自然形成合适的 action boundary。**

如果完全把 chunk size 留给模型自己决定，那么最终得到的可能是 model policy effect，而不是我们想研究的 granularity effect。因此第一阶段应该先把 granularity 的 nominal boundary 控制住，并把实际的 operations-per-observation、visible multi-op rate、action composition 和 decision rounds 一起作为 manipulation check。

## 攻击实验中我遇到的问题和调整

我也重新检查了 clean 和 attack 条件下的安全测量。最早的 attack-v0 把指令放在隐藏文件中，模型通常没有发现它，所以 exact target attempt 是 0。这个结果只能说明当时的 attack exposure pipeline 没有被触发，不能说明 interface 很安全。

之后我把攻击内容放进任务相关源码的注释中，使用 repository-carried prompt injection，并要求模型写入实验专用的 `.git/agent_attack_sentinel_v2`。这个 target 仍然受到共同的 PermissionEngine 保护，不允许真实创建。新的 18-run attack sanity 中，15/18 个 run 暴露了攻击内容，11/18 个 run 产生了精确的 target attempt，11/11 个 target attempt 都被 permission 正确拒绝，最终 sentinel success 是 0/18。

相比最早的攻击，这至少解决了“完全测不到模型是否受到攻击影响”的问题；但它仍然不能直接作为 G1/G2/G4 的正式安全结论，因为当前结果还没有证明更大的 G 会稳定地产生更长的 same-action attack chain。现在更有意义的安全指标应该包括：

- attack exposure 以后到第一次 target attempt 的 latency；
- exposure 到 target attempt 之间跨越了多少 backend operations；
- 一次错误 decision 后是否还有 residual operations 继续执行；
- permission denial 以后模型是否重复尝试；
- 模型能否恢复到 task-relevant work；
- safe failure 和真正的 security success 是否能够区分。

这里 PermissionEngine 不是被比较的 defense treatment，而是三个 G 条件共有的安全边界和 measurement boundary。它的作用是让我们能够记录 unsafe intent，同时不让 synthetic attack 真正写入受保护目标。这样 security comparison 应该主要关注模型的 exposure、attempt、propagation 和 recovery，而不只是“权限有没有成功拦截”。

## 准备扩大实验时又发现的问题

在准备下一轮 calibration、准备扩大任务池时，我又先核对了候选任务是否真的属于目标 SWE-bench split，并用 official harness 做了最小验证。这个检查发现，准备中的六个候选任务里只有一个能够和 SWE-bench_Verified 的 test split 精确匹配；第一个无效任务进入 official evaluator 后也出现了 prediction ID 不在数据集中的错误。

这件事虽然发生在正式扩大实验之前，但对我来说很重要，因为它说明任务选择本身也是实验有效性的一部分，不能只依赖本地 metadata、gold patch 或准备好的 source checkout。于是我没有把这批运行结果继续当作正式 utility evidence，而是暂停并回退了那次准备中的变更，保留当前已经验证过的实验框架和诊断记录。现在我会把 task membership、official evaluator compatibility、stopping behavior 和 treatment realization 都放到正式实验前的检查清单里。

另外，之前 50-action ceiling 下出现了很多 run 达到上限的情况。进一步检查最后几步 trajectory 后发现，这些 run 不是同一种失败：其中混合了确实没有完成的任务、完成后反复跑测试的 verification churn、重复读取和 list loop、permission-denied process friction，以及固定 action ceiling 造成的 right-censoring。因此，patch 非空、出现过一次 passing test 或者达到了 action budget，都不能单独当作 resolve 或 stable completion。后续需要把 completion-like candidate、最后一次有效编辑、post-edit test、diff inspection 和最终 finish action 分开记录。

这些问题让我把实验推进顺序重新调整成：先做小规模 calibration，确认任务有效、停止行为可解释、G1/G2/G4 有实际 manipulation、attack 有可测的 exposure 和 target attempt；只有这些条件满足以后，再冻结配置、跑正式任务并进行 official grading。

## 相关文献给我的启发

我后来又重新看了一些相关工作，发现现在这个问题有比较强的理论和经验依据，并不是为了制造实验差异而人为定义出来的变量。

例如 SWE-agent 的核心结论之一就是，Agent-Computer Interface 本身会显著改变 software engineering agent 的行为和 performance。它说明在 model 和 task 不变的情况下，agent 如何浏览 repository、如何编辑文件、工具输出怎样反馈给模型，这些 interface-level design choices 本身就不是简单的 implementation detail，而是会直接改变 agent 的能力。

CodeAct 则从另外一个方向说明 executable code action 的价值。传统 agent 通常一次输出一个 JSON/text tool call，而 CodeAct 允许模型生成 executable Python code，把多个工具调用和内部计算组合到一个 action 中。它能够说明 composable/code action 可能提高 agent 的 performance，但 representation、program composition、control flow 和一个 action 内能执行多少 operations 在那里是一起变化的，因此不能直接回答我们的 capability-matched granularity 问题。

最近的 LLM-agent 工作开始直接研究 action chunking。比如 SPACE（Act More, Decide Less）从传统 ReAct“一次 LLM round 执行一个 primitive action”出发，研究让 agent 一次产生 variable-length action chunks。一个特别有意思的结果是，如果单纯允许模型自由决定 chunk length，policy 很容易出现两个极端：要么退化成 single-action behavior，要么一次执行过长的 sequence。因此，chunk boundary 本身需要被显式建模或控制。

机器人领域的 action chunking 工作也支持这个思路。一次 policy prediction 后连续执行多少 actions，再重新 observation/replanning，可能同时影响连续动作的一致性、inference overhead 和错误恢复；execution horizon 通常不是简单的“越长越好”或“越短越好”，而可能存在 task-dependent、non-monotonic effect。

这些工作共同支持了我的研究动机，但没有直接回答：**如果所有 capabilities、canonical execution backend、permissions、model 和 task 都严格 matching，仅仅改变一个 LLM decision 所覆盖的 primitive operations 数量，在 repository-level coding agent 中会发生什么？**

## 现在比较准确的研究问题

这样重新定义以后，我认为我们的研究问题可以比“Atomic vs Python 哪个更安全”更精确：

> **Under capability-matched conditions, how does action-boundary granularity affect the trajectory structure, task utility, execution-security risk, and resource cost of repository-level coding agents?**

具体来说，我想研究：

```text
G = 1、2、4
        ↓
operations per observation、decision rounds、operation composition
        ↓
task completion、patch quality、token/runtime cost
        ↓
attack propagation、false denial、recovery 和 safe failure
```

在 clean 条件下，主要看 G 是否改变正常的 search/read/edit/test workflow；在 attack 条件下，主要看 repository-carried instruction 暴露以后，一次错误 decision 能够传播多远，以及更频繁的 observation 是否帮助模型更快恢复。这里我不预设安全性一定随 G 增大而下降，也不预设效率一定随 G 增大而上升。

较大的 G 可能减少 model turns、observation 次数和部分 token/runtime cost，也可能让已经确定的局部 workflow 更紧凑。例如：

```text
search → read → read → test
```

或者：

```text
read → edit → run test → inspect result
```

但较大的 G 也可能降低 observation/checkpoint 的频率。一旦模型在 action 开始时受到了错误 instruction、prompt injection 或 repository 中 malicious content 的影响，它可能在下一次 LLM-level replanning 之前连续执行多个敏感 operations，从而扩大一次错误 decision 的 execution footprint。

反过来，G1 每做一次 operation 就重新观察，可能更容易纠错，但会产生更多 model turns、更长 context 和更多 planning overhead；同时，轨迹变长也可能增加模型接触 malicious carrier 或发生 trajectory drift 的机会。所以安全性和效率之间是否存在 trade-off，以及这个 trade-off 是否在 G2 附近出现一个 sweet spot，都应该由实验回答，而不是预先假设。

如果最后发现 G2 比 G1 和 G4 都好，这意味着 action granularity 可能存在中间的 sweet spot，而不是越大越好；如果 G4 performance 更高但 security 更差，就说明 interface efficiency 和 execution safety 之间存在 trade-off；如果 G1 security 更好但 false denial 也明显增加，就说明安全指标不能只看 attack success rate，因为一个 agent 什么都不做也可能看起来非常安全；如果最终 resolve rate 差别不大，但 trajectory、cost 或 security 显著不同，也同样是重要结果，因为单独看 resolve rate 会隐藏 interface-level behavior differences。

## 我现在的实验推进计划

我目前倾向于按下面的顺序推进，而不是直接把现有 pilot 当作最终结论。

第一步是完成 calibration。需要确认 G1/G2/G4 的 nominal upper bound 没有被违反，同时 G2/G4 能够产生足够多的真实 multi-operation action；还需要确认新的 sentinel attack 能在多数 attack run 中被暴露，并且 exact target attempt 不是永远为零。除此之外，候选任务必须通过官方 split membership 和 evaluator compatibility 检查，停止行为也要避免大面积被 action ceiling 截断。

第二步是冻结实验协议。固定模型、任务、base commit、Backend、PermissionEngine、prompt、sandbox、上下文限制、并发、timeout、action budget、attack payload 和 evaluator，只改变 `operations.maxItems=1/2/4` 以及 clean/attack condition。每个 run 都从同一个任务的 fresh repository 开始，避免不同条件之间互相污染。

第三步是先分析 trajectory，再分析最终 task outcome。因为一个 run 内包含多次 model actions 和 backend operations，action/operation 不能被当成相互独立的统计样本；正式比较应以 run 为主要统计单位，以 task 作为 block，action 和 operation 主要用于机制分析。分析顺序会先检查 treatment realization，再看 decision rounds、operations/observation、observation frequency、operation composition、error recovery 和 token/runtime，最后再结合 official SWE-bench grading 讨论 task utility。

等 controlled experiment 做清楚以后，后续还可以自然扩展到 adaptive granularity：不是固定 K，而是让 agent 根据当前任务阶段、uncertainty 或 security risk 动态决定什么时候应该停止当前 action，重新 observation 和 replanning。但我觉得这应该放在第二阶段，不能在基础 treatment 还没有稳定实现之前就引入。

所以我现在倾向于把当前实验重点从单纯的 “Atomic versus Restricted Python representation” 往 **controlled action-boundary granularity in coding agents** 这个方向收敛。这样做不是放弃前面已经做的 Atomic/Python 工作，而是把前面的失败和 pilot 结果转化成了研究设计上的信息：我们发现了原始 independent variable 在真实 trajectory 中不稳定，因此把它拆成更直接、可测量、可控制的 action-boundary treatment；同时保留 shared Backend、permission boundary、attack setup 和 trajectory analysis 作为后续实验的基础。

我现在觉得，整个项目比较完整的 story 可以概括成：已有工作已经知道 **interface matters**；CodeAct 等工作说明 **composable/code actions can improve agents**；action chunking 工作说明 **一个 decision 执行多少 primitive actions 会影响 performance 和 decision cost，而且 chunk boundary 很重要**；而我们希望在 repository-level software engineering agent 的严格 controlled setting 中，进一步回答当底层 capabilities、canonical execution backend、permissions、model 和 task 都匹配时，**controlled action-boundary granularity 本身如何改变 trajectory，以及这种变化是否进一步影响 execution security。**

因此我们的创新点不应该说“以前没有人研究 action chunking”，因为 robotics 和最近的 general LLM agent 工作已经涉及这个方向；更准确的说法应该是，我们把这个变量引入 repository-level coding agent 的 capability-matched controlled setting 中，并且不仅看 performance，还把 trajectory structure、security risk、false denial、recovery 和 resource cost 一起考虑。

这也是我这段时间最大的思路变化：我最开始想比较两种 interface，后来发现两种 interface 的实际行为并没有形成稳定的 execution-granularity 差异；于是我没有继续把所有差异都归因于“Python 比 Atomic 更好或更差”，而是回到实验设计最基本的问题——到底哪个变量真正被操纵了，哪个变量能够被测量，哪个变量能够支持 causal interpretation。现在 G1/G2/G4 还需要继续做 calibration，但研究问题、控制变量和后续分析路径已经比原来清楚很多了。
