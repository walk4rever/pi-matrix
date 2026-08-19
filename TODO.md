# TODO — 活跃工作队列

> 更新：2026-08-19。本文件只保留**未完成项**；完成项的结论回写 `PRODUCT.md` 后从这里移除（过程见 git 历史）。产品定位、架构、设计决策一律以 `PRODUCT.md` 为准。
>
> **当前主线：任务优先。** 不预设 domain/角色，直接从日常工作中采集带判据的任务，用 pi + 某个模型跑出 baseline，再逐步迭代。判据先行——先知道"合格"是什么，才谈得上造机器去达到它。设计见 `PRODUCT.md`「TokenEconBench — 能力的定义方式」。
>
> **Hermes 线冻结**，不改 `cloud/message`、`cloud/executor` 与飞书通道的任何契约。个人版相关待办已整体降级，见 `PRODUCT.md`「近期技术优先级」P3。

---

## P0 — 任务集与基线

这是护城河本身，也是唯一在所有情景下都保值的资产。

- [x] **task.yaml schema 升级** —— 加 `capabilities`（kebab slug，报告口径）与 `provenance.workflow`，`category` 降级为目录约定。第一个任务已回填标签。

- [ ] **日常任务采集**（Rafael 主导）
  从日常工作中定义经常做的任务，按 `PRODUCT.md`「采集与再合成」六步转成带判据的任务。
  纪律：一个任务 = 一次可验收的交付（人类 20 分钟–4 小时）；**每 3 个 `test` 任务强制配 1 个 `llm_judge` 任务**，否则会只剩好写判据的活；采集要趁热，凉了前态和判据就丢了。
  两个采集源：金融/投资分析（buffett-tribe，判据偏硬）与 AI 应用工程（ai-dive / pi-matrix，判据偏 `test`）——落在判据类型两端，用于验证框架的适应性。
  - [x] `daily-ops/yt-podcast-zh-translation-01` —— 框架已搭好（task.yaml + rubric + README），**真实 URL 待填**，判据材料存放方式待首次采集时定。这也是第一个 `llm_judge` 类型任务、第一个网络依赖型任务（见该任务 README「外部内容依赖型任务」，与出网策略待定决策直接相关）。

- [ ] **baseline 跑批**
  用 pi + 某个模型跑任务集，产出首批 run_record。**不等 pi 实例做好**——先用现成 harness（pi CLI / `--mode rpc` 直连）拿到"这活现在的 AI 干得怎么样"的真实数字，那批数字反过来决定实例该长什么样。
  **验收**：每个任务一条记录，含 tokens / cost / 耗时 / 判据结论。

- [ ] **报告口径**
  按 `capabilities` 聚合的成本-完成率帕累托视图。不出合成分（见 `PRODUCT.md`「为什么不做合成分」）。

- [ ] **runner 适配**
  现 `bench/runner/run.mjs` 把 harness 写死为 `execFileSync("claude", ...)`、只支持 `test` 判据。需要：支持 pi、支持 `structural_check` 与 `llm_judge`、输出统一的 `run_record` schema。
  `yt-podcast-zh-translation-01` 可直接当验收用例——它同时逼出 `llm_judge` 判据执行路径和"任务需要联网"这两个当前 runner 完全没处理过的分支。

---

## P1 — 待定决策

- [ ] **第一批任务的对手方**：任务集和判据由谁定义？自己定（有能力但不是买家）还是找真实从业者？这决定任务集是"我以为的工作"还是"真实的工作"。角色封装的触发条件里，买家指认是必要的一半。
- [ ] **模型档位**：baseline 跑几个模型档位？单一 default 还是矩阵？影响成本结构与后续 virtual key 预算策略。
- [ ] **出网策略松紧**（pi 实例）：确认了 pi **没有工具审批机制**，容器边界是唯一防线，这条权重上升。全开最省事但沙箱形同虚设；只放行 gateway + 包管理源最安全但挡住"让 agent 上网查资料"。
- [ ] **挂起阈值与冷启动预算**（pi 实例）：空闲多久挂起、恢复延迟能接受到几秒。

---

## P2 — pi 实例工程（服务于 P0，不领先于 P0）

设计已定稿见 `PRODUCT.md`「pi Track」，含实例层设计（进程/会话模型、续传边界、provider extension、挂起判据、cwd 约束）。

- [ ] **阶段 0 — 实例镜像**：`pi --mode rpc` + Node supervisor（HTTP/SSE ⇄ JSONL stdio）。
  **验收**：`curl` 发 prompt，SSE 收到 text_delta 与 tool 事件；`agent_end` 能结算出本次运行成本。
  注意：RPC 严格按 `\n` 分帧，不能用 Node `readline`；extension UI 请求必须默认回 cancellation，否则会静默挂死。
- [ ] **阶段 1 — 隔离与凭证**：非 root、资源上限、独立网络、出网白名单、per-instance LiteLLM virtual key（需给 LiteLLM 配 `DATABASE_URL`）。
- [ ] **阶段 2 — Control Plane**：扩展 Orchestrator 做 provision / suspend / resume / destroy，不动 Hermes 现有端点。
- [ ] **阶段 3 — Edge + web 界面**：SSE 中继 + 流式聊天 + 成本视图。
- [ ] **阶段 4 — 遥测落库**：`agent_end` 结算写 `pi_run_records`，与 LiteLLM spend 对账偏差 < 5%。

---

## P3 — 已记录的既有假设（如与设想不符，越早推翻越便宜）

- v1 一个用户一个实例，cwd 钉死 `/workspace`；schema 允许多实例，UI 先不暴露。
- 一会话一 pi 进程，v1 并发上限 1–3。
- v1 的终端就是 RPC `bash` 命令（用户手敲的命令会进 agent 下一轮上下文），不做 PTY。
- pi 包用 `@earendil-works/pi-coding-agent`（最新 0.84.2，Node 22+）。
- desktop = Tauri 包同一套 web UI，可指向本地或云端运行时。
- pi 实例第一版不接飞书工具（`feishu_doc`/`feishu_drive` 是 Hermes 内建的）。
