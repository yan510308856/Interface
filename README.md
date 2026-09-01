# Atomic vs. Restricted Python Interface Demo

这是一个面向 repository-level coding agent 的最小实证研究 Demo。它在底层能力、权限、模型、任务、sandbox 和预算一致的前提下，比较两种动作接口表征：

- **Atomic**：一次模型动作执行一个结构化 backend operation；
- **Restricted Python**：一次模型动作可组合零到多个相同的 backend operations。

实验同时交叉 `Clean` 与 `Adversarial` 环境，形成四个配对条件。项目不预设哪种接口更好，也不会用改变权限或测试的方式“修复”失败条件。

## 当前状态

**R0 — Documentation and workspace baseline** 与 **R1 — Qwen / ModelScope /
A100 feasibility** 已通过。R1 的冻结配置在两个独立 A100 worker 中完成三个
固定 prompt、语法解析和 16,384-token context probe，模型 revision、snapshot
digest、输入 token IDs 与 runtime identity 一致。正式实验仍停在 **R2**：状态保持
`incomplete`，决策为 `pilot_only`。

项目当前选择独立的 **Implementation Pilot** 路线。R6-P runner 与 Colab Qwen pipeline smoke 已完成：
两个真实 Qwen bundle 均通过完整性与 metrics 重算校验，但两个接口都产生 6/6 invalid actions、
0 backend operations、空 patch 和 functional FAIL。该结果是开发性模型/interface adherence outcome，
不解锁正式 R6–R8，也不产生四-cell 比较结论。下一 pilot stage 由 human review 决定。
现有 D0 代码和 artifacts 仅是 v28 provenance，不代表 v29 实验结果。

## 先读什么

1. [`docs/interface29.md`](docs/interface29.md)：研究问题、变量和威胁模型。
2. [`docs/aug29experiment.md`](docs/aug29experiment.md)：R0→R8 实现与验收协议。
3. [`AGENTS.md`](AGENTS.md)：编码代理和协作者的工作规则。

## 目录

```text
docs/          规范文档与历史材料
experiment/    按 R0 inventory 分阶段迁移的实验代码
notebooks/     数据集与任务探索，不作为正式 runner
scripts/       不依赖第三方包的仓库检查
artifacts/     小型 stage decision/audit 可提交；大型构建与运行产物不提交 Git
```

## 本地检查

以下命令验证 v29 仓库入口、R0 inventory/decision，以及保留的 v28 D0
证据仍可复查：

```bash
python3 scripts/check_repository.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s experiment/tests -p 'test_*.py'
```

R1 本地预检（不下载模型、不需要 GPU）：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest experiment.tests.test_model_config
python3 scripts/smoke_model_colab.py \
  --config experiment/configs/model.yaml \
  --dry-run \
  --process-count 2
```

如需重放 R1，CPU Colab 可先把固定 ModelScope snapshot 下载到 Google Drive；
cache 只用于加速，不构成独立的通过证据：

```bash
python3 -m pip install -r requirements.txt

python3 scripts/prefetch_model_colab.py \
  --config experiment/configs/model.yaml \
  --cache-dir /content/drive/MyDrive/Interface-R1/modelscope-cache
```

`requirements.txt` 固定 R1 的用户空间依赖；不要重装 Colab 自带的 PyTorch，
正式运行会记录并冻结实际 Torch/CUDA runtime。

R1 的命令、冻结依赖、模型身份与正式通过证据摘要见
[`artifacts/r1/R1_DECISION.md`](artifacts/r1/R1_DECISION.md)。脚本拒绝覆盖已有
attempt；每次重跑必须使用新的 run directory。

R2 本地先验证冻结的候选顺序、task manifest、patch digest 和命令边界：

```bash
python3 scripts/validate_task.py --manifest-only
python3 -m unittest experiment.tests.test_task_manifest
```

Apple Silicon Mac 上可通过固定 `linux/amd64` 镜像各运行一次 baseline/reference：

```bash
python3 scripts/validate_task.py --pilot --candidate-index 0 --mode baseline \
  --run-id r2-pilot-baseline-my-run --output-dir artifacts/r2/pilot
python3 scripts/validate_task.py --pilot --candidate-index 0 --mode reference \
  --run-id r2-pilot-reference-my-run --output-dir artifacts/r2/pilot
```

这些结果只用于展示实现链路，明确属于 development evidence；它们不证明 R2
正式通过、任务在原生环境稳定复现，也不解锁正式 R3 或严格受控的四-cell 实验。

R3 的本地 pilot 已实现 paired workspace、episode fake canary、差异 allowlist，以及
Present/Exposure/Attempt/Block/Effect/Goal 安全 oracle。可用同一个 episode ID 各运行一次：

```bash
python3 scripts/validate_pair.py --condition clean \
  --run-id r3-pilot-clean-my-run --episode-id r3-pilot-pair-my-run
python3 scripts/validate_pair.py --condition adversarial \
  --run-id r3-pilot-adversarial-my-run --episode-id r3-pilot-pair-my-run
```

两次都是固定 `linux/amd64` 镜像中的 direct pytest smoke。结果只属于开发证据；正式 R3
仍被正式 R2 门禁阻塞。

R4 的本地 pilot 已实现唯一 canonical backend、default-deny permission engine 和 append-only
audit。它使用 tiny disposable repository，不运行模型：

```bash
python3 -m unittest experiment.tests.test_backend experiment.tests.test_permission
python3 scripts/smoke_backend.py --output artifacts/r4/backend_smoke.json
```

本地 process runner 使用 exact argv 和 `shell=false`，但尚无 OS 级网络隔离或 hardened process
sandbox，因此仍是开发能力验证，不是正式安全边界。

R5 的本地 pilot 已实现严格 Atomic JSON adapter 和不使用 `eval`/`exec` 的
Restricted Python AST interpreter。两个接口在 fresh disposable fixtures 上运行同一组
read→replace→test→diff、permission denial 和 timeout 操作：

```bash
python3 -m unittest \
  experiment.tests.test_atomic \
  experiment.tests.test_restricted_python \
  experiment.tests.test_interface_equivalence
python3 scripts/validate_interfaces.py --output artifacts/r5
```

验证报告比较规范化 backend events、权限、状态、错误、result digest、最终 tree hash 和 diff；
`open`、`import os`、`subprocess` 三类最小绕过必须在产生 backend event 前被拒绝。报告的
`PASS` 表示 R5 Implementation Pilot 的预定范围已完成；正式 R5 仍被正式 R2–R4 门禁阻塞。

R6-P 已实现接口无关的 episode runner：合并并冻结 effective config，调用 fake/scripted model 或
R1 frozen Qwen，经 R5 adapter 和共享 backend 执行动作，追加 observation，始终运行 oracle，并输出
可校验的完整 result bundle。malformed output、model timeout、task failure 和空 patch 均作为受控
episode outcome 出包；metrics 从 JSONL raw events 重算。所有 R6-P bundle 都声明
`development_evidence_only` 与 `formal_r6_eligible: false`；synthetic fixture 成功或 Qwen 行为都不是
正式 SWE-bench 结果。

本地 fake smoke：

```bash
python3 -m unittest experiment.tests.test_runner experiment.tests.test_metrics
python3 scripts/run_episode.py \
  --model fake --interface atomic \
  --output-root /tmp/r6p-local --episode-id local-atomic
python3 scripts/run_episode.py \
  --model fake --interface restricted_python \
  --output-root /tmp/r6p-local --episode-id local-python
python3 scripts/validate_result_bundle.py /tmp/r6p-local/local-atomic
```

冻结的 Astropy SWE-bench task 也可在一次 A100 session 中运行完整 paired pilot。入口只加载一次
Qwen，并按 `Atomic/Clean → Atomic/Adversarial → Restricted Python/Clean → Restricted
Python/Adversarial` 生成四个独立 bundle 和 prediction。每个 interface 的 Clean/Adversarial
workspace 来自同一 base commit；只有冻结 carrier 与 episode fake canary 是 adversarial 增量。
工作副本放在 Colab local scratch，基础 Git checkout、模型 cache 和不可覆盖的结果保留在 Drive。
Drive checkout 即使有本地未跟踪文件也不会被清理或直接用于实验；入口会从冻结 commit 创建一个
不包含这些文件的临时 pristine checkout：

```bash
python3 scripts/run_r6p_astropy_paired_colab.py \
  --workspace /content/drive/MyDrive/Agents_Research/workspaces/astropy-12907-base \
  --model-cache /content/drive/MyDrive/Interface-R1/modelscope-cache \
  --output-root /content/drive/MyDrive/Agents_Research/runs/r6p-astropy-paired \
  --run-id r6p-astropy-paired-001 \
  --allow-colab-release-drift
```

四个 `*.prediction.json` 必须随后分别交给固定的 x86_64 SWE-bench harness；Colab bundle 中的
functional status 保持 `DEFERRED`，不能把 patch 生成成功当作 Verified task 已解决。paired
安全 oracle 会记录 carrier 是否出现/暴露、受限操作尝试是否被共享权限层阻止，以及 fake canary
是否真正到达本地 sink。

Colab A100 smoke 在同一进程只加载一次 Qwen，然后依次运行两个 Clean 接口。先在 Colab notebook
挂载 Drive；再 clone 本次 handoff 给出的精确 commit（不要运行浮动的最新分支），安装 R1 固定的
用户空间依赖，最后运行：

```python
from google.colab import drive
drive.mount("/content/drive")
```

```bash
git clone https://github.com/yan510308856/Interface.git /content/Agents_Research
cd /content/Agents_Research
git checkout <R6P_COMMIT_SHA>
python3 -m pip install -r requirements.txt
python3 scripts/run_r6p_colab.py \
  --model-cache /content/drive/MyDrive/Interface-R1/modelscope-cache \
  --output-root /content/drive/MyDrive/Agents_Research/runs/r6p-qwen-smoke \
  --run-id r6p-qwen-001 \
  --allow-colab-release-drift
```

入口会拒绝 dirty clone、非唯一 GPU、包版本或 Colab/Python/Torch/CUDA/driver/GPU identity 与 R1
freeze 不一致、重复 episode directory，以及 bundle digest/metrics 校验失败。Drive 仅由 runner 外层
用于模型 cache 与 immutable bundle 输出，不会挂进 synthetic agent workspace，也不会出现在 prompt。
`--allow-colab-release-drift` 仅供 R6-P 开发性 smoke：只允许 Colab release 标签变化并把差异写入
bundle；Python、包版本、Torch、CUDA、driver、GPU 型号或显存任一变化仍会 fail closed。正式运行
不得使用该参数。

正式 R2 必须在具有至少 120 GiB Docker 数据盘的原生 x86_64 Linux Docker
host 上运行。安装固定 harness 后先执行 preflight：

```bash
python3 -m pip install -r requirements-r2.txt
python3 scripts/validate_task.py --preflight --output-dir artifacts/r2/runtime
```

正式 baseline/reference 的重复要求与当前 `pilot_only` 限制见
[`artifacts/r2/R2_DECISION.md`](artifacts/r2/R2_DECISION.md)。A100 和 Qwen
不参与 R2。

R0 的机器清单与结论见
[`artifacts/r0/MIGRATION_AUDIT.md`](artifacts/r0/MIGRATION_AUDIT.md)。历史 D0
证据保留在 `artifacts/d0/`，其原始复查命令仍可按归档的
[`aug28experiment.md`](docs/archive/aug28experiment.md) 运行；它不是当前 stage gate。

如需重新运行历史 SWE-bench 基线和参考补丁 oracle（需要 Docker 和冻结的
`linux/amd64` 镜像）：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_d0.py --run-task-validation
```

该历史验证器在旧 live-model smoke 未完成时会以退出码 `1` 和
`D0: REVISE` 结束；这不会改变 R0 decision。

## Demo 完成路径

当前 Implementation Pilot 已完成 R6-P；human review 决定继续 R7-P 或等待 formal R2。正式路径仍要求
R2 在原生 x86_64 Docker host 通过后，才可将 R3–R8 的结果称为受控实验阶段证据。两条路线共享代码
和安全边界，但 artifacts、decision 与研究声明保持分离。

## 安全与复现

- 只使用隔离环境和 synthetic canary，不接触真实 secret。
- `artifacts/`、模型权重、benchmark clone 与 `experiment/results/` 默认不进 Git。
- 每次正式运行必须记录准确 Git commit、配置/模式 digest、模型与数据集 revision、容器 digest 和 seed。
