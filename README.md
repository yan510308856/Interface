# Atomic vs. Restricted Python Interface Demo

这是一个面向 repository-level coding agent 的最小实证研究 Demo。它在底层能力、权限、模型、任务、sandbox 和预算一致的前提下，比较两种动作接口表征：

- **Atomic**：一次模型动作执行一个结构化 backend operation；
- **Restricted Python**：一次模型动作可组合零到多个相同的 backend operations。

实验同时交叉 `Clean` 与 `Adversarial` 环境，形成四个配对条件。项目不预设哪种接口更好，也不会用改变权限或测试的方式“修复”失败条件。

## 当前状态

当前处于 **R0 — Documentation and workspace baseline**。研究设计已迁移到 v29；现有 D0 代码和 artifacts 仍属于归档的 v28 协议，完成迁移审计前不能进入 R1。这个状态不是实验结果。

## 先读什么

1. [`docs/interface29.md`](docs/interface29.md)：研究问题、变量和威胁模型。
2. [`docs/aug29experiment.md`](docs/aug29experiment.md)：R0→R8 实现与验收协议。
3. [`AGENTS.md`](AGENTS.md)：编码代理和协作者的工作规则。

## 目录

```text
docs/          规范文档与历史材料
experiment/    待从归档 v28 D0 迁移到 v29 R0→R8 的实验代码
notebooks/     数据集与任务探索，不作为正式 runner
scripts/       不依赖第三方包的仓库检查
artifacts/     D0 审计记录可提交；大型构建与运行产物不提交 Git
```

## 本地检查

目前没有 D1+ agent harness。以下命令验证仓库结构、D0 单元边界和冻结 digest：

```bash
python3 scripts/check_repository.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s experiment/tests -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python3 scripts/freeze_d0.py --check
```

重新运行 SWE-bench 基线和参考补丁 oracle（需要 Docker 和已经冻结的 `linux/amd64` 镜像）：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_d0.py --run-task-validation
```

验证器在真实模型 smoke 仍未完成时会故意以退出码 `1` 和 `D0: REVISE` 结束；各子检查结果记录在 `artifacts/d0/validation_report.json`。

## Demo 完成路径

严格按照 `docs/aug29experiment.md` 推进：R1 验证 ModelScope Qwen/A100，R2–R3 冻结 clean/paired task 与 oracle，R4–R5 实现 backend、permission 和两种 interface，R6–R8 完成真实模型 smoke 与四-cell Demo。

## 安全与复现

- 只使用隔离环境和 synthetic canary，不接触真实 secret。
- `artifacts/`、模型权重、benchmark clone 与 `experiment/results/` 默认不进 Git。
- 每次正式运行必须记录准确 Git commit、配置/模式 digest、模型与数据集 revision、容器 digest 和 seed。
