# Atomic vs. Restricted Python Interface Demo

这是一个面向 repository-level coding agent 的最小实证研究 Demo。它在底层能力、权限、模型、任务、sandbox 和预算一致的前提下，比较两种动作接口表征：

- **Atomic**：一次模型动作执行一个结构化 backend operation；
- **Restricted Python**：一次模型动作可组合零到多个相同的 backend operations。

实验同时交叉 `Clean` 与 `Adversarial` 环境，形成四个配对条件。项目不预设哪种接口更好，也不会用改变权限或测试的方式“修复”失败条件。

## 当前状态

当前处于 **D0 — Freeze Demo Spec**，尚未运行实验，也没有研究结果。D0 中的模型、数据集、任务、容器和配置版本尚未全部冻结，因此当前结论是 `revise`，不能进入 D1。

## 先读什么

1. [`docs/interface28.md`](docs/interface28.md)：研究问题、变量和威胁模型。
2. [`docs/aug28experiment.md`](docs/aug28experiment.md)：D0→D11 实现与验收协议。
3. [`AGENTS.md`](AGENTS.md)：编码代理和协作者的工作规则。

## 目录

```text
docs/          规范文档与历史材料
experiment/    按 D0→D11 逐步实现的实验代码
notebooks/     数据集与任务探索，不作为正式 runner
scripts/       不依赖第三方包的仓库检查
artifacts/     本地生成的演示文稿与构建产物，不提交 Git
```

## 本地检查

目前没有可运行的 agent harness。可以先验证仓库入口、规范文件和安全忽略规则：

```bash
python3 scripts/check_repository.py
```

成功时会输出 `Repository structure check passed.`。

## Demo 完成路径

严格按照 `docs/aug28experiment.md` 推进：D0 冻结配置，D1–D5 建立并验证共享 backend、权限、两个 adapter 与能力等价性，D6–D9 接入 task、adversarial pair、模型和安全 oracle，D10 跑四个 cells，D11 决定是否 `READY FOR PILOT`。

## 安全与复现

- 只使用隔离环境和 synthetic canary，不接触真实 secret。
- `artifacts/`、模型权重、benchmark clone 与 `experiment/results/` 默认不进 Git。
- 每次正式运行必须记录准确 Git commit、配置/模式 digest、模型与数据集 revision、容器 digest 和 seed。
