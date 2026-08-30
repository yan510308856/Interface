# Atomic vs. Restricted Python Interface Demo

这是一个面向 repository-level coding agent 的最小实证研究 Demo。它在底层能力、权限、模型、任务、sandbox 和预算一致的前提下，比较两种动作接口表征：

- **Atomic**：一次模型动作执行一个结构化 backend operation；
- **Restricted Python**：一次模型动作可组合零到多个相同的 backend operations。

实验同时交叉 `Clean` 与 `Adversarial` 环境，形成四个配对条件。项目不预设哪种接口更好，也不会用改变权限或测试的方式“修复”失败条件。

## 当前状态

**R0 — Documentation and workspace baseline** 与 **R1 — Qwen / ModelScope /
A100 feasibility** 已通过。R1 的冻结配置在两个独立 A100 worker 中完成三个
固定 prompt、语法解析和 16,384-token context probe，模型 revision、snapshot
digest、输入 token IDs 与 runtime identity 一致。当前进入 **R2 — Clean task
feasibility and task manifest freeze**。现有 D0 代码和 artifacts 仅是 v28
provenance，不代表 v29 实验结果。

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

R2 本地只验证冻结的候选顺序、task manifest、patch digest 和官方 harness
命令边界，不启动 Docker：

```bash
python3 scripts/validate_task.py --manifest-only
python3 -m unittest experiment.tests.test_task_manifest
```

正式 R2 必须在具有至少 120 GiB Docker 数据盘的原生 x86_64 Linux Docker
host 上运行。安装固定 harness 后先执行 preflight：

```bash
python3 -m pip install -r requirements-r2.txt
python3 scripts/validate_task.py --preflight --output-dir artifacts/r2/runtime
```

正式 baseline/reference 的两次重放命令与当前 `REVISE` 原因见
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

严格按照 `docs/aug29experiment.md` 推进：R1 验证 ModelScope Qwen/A100，R2–R3 冻结 clean/paired task 与 oracle，R4–R5 实现 backend、permission 和两种 interface，R6–R8 完成真实模型 smoke 与四-cell Demo。

## 安全与复现

- 只使用隔离环境和 synthetic canary，不接触真实 secret。
- `artifacts/`、模型权重、benchmark clone 与 `experiment/results/` 默认不进 Git。
- 每次正式运行必须记录准确 Git commit、配置/模式 digest、模型与数据集 revision、容器 digest 和 seed。
