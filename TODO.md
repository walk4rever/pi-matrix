# TODO — 活跃工作队列

> 更新：2026-08-18。本文件只保留**未完成项**；完成项的结论回写 `PRODUCT.md` 后从这里移除（过程见 git 历史）。产品定位、架构、设计决策一律以 `PRODUCT.md` 为准。
>
> 当前主线：pi Track 云端实例（设计见 `PRODUCT.md`「pi Track — 云端实例（web/desktop）」）。**Hermes 线冻结**，不改 `cloud/message`、`cloud/executor` 与飞书通道的任何契约。
>
> Hermes 线的待办目前仍列在 `PRODUCT.md`「近期技术优先级」P0–P3 表里，尚未迁到本文件。其中「容器 sleep/wake」「按用户 Gateway Key」两项与 pi 线设计重叠——pi 线会先把这两件事做对，Hermes 线要不要跟进另行决定。

---

## P0 — pi Track 落地路径

按阶段推进，每阶段独立可用，不依赖后续阶段才产生价值。

- [ ] **阶段 0 — 实例镜像跑通**
  容器内 `pi --mode rpc` + Node supervisor（HTTP/SSE ⇄ JSONL stdio），本地 docker 起来。
  **验收**：`curl` 发一条 prompt，SSE 收到 text_delta 与 tool 事件；`get_session_stats` 返回 tokens 与 cost。
  注意：RPC 严格按 `\n` 分帧，不能用 Node `readline`（它会在 `U+2028/U+2029` 额外断行）。

- [ ] **阶段 1 — 隔离与凭证**
  非 root、`mem_limit`/`nano_cpus`/`pids_limit`/`cap-drop ALL`、根文件系统只读、独立 docker 网络、出网白名单；LiteLLM 接 `DATABASE_URL` 并按实例签发 virtual key。
  **验收**：容器内拿不到 master key；超预算的 key 被 gateway 拒绝；`docker stats` 显示上限生效。

- [ ] **阶段 2 — Control Plane**
  扩展 Orchestrator：provision / suspend / resume / destroy，新增端点，不动 Hermes 现有端点。
  **验收**：挂起后容器消失、卷还在；恢复后同一会话可继续。

- [ ] **阶段 3 — Edge + web 聊天界面**
  SSE 中继（鉴权、归属校验、事件旁路遥测）+ Dashboard 内的流式界面（工具调用渲染、中断）。
  **验收**：关掉标签页再打开，进行中的任务事件不丢（`Last-Event-ID` 续播）。

- [ ] **阶段 4 — 遥测落库**
  每轮 `get_session_stats` 差分写 `pi_run_records` + Dashboard 成本视图。
  **验收**：每轮一条记录；与 LiteLLM spend 对账偏差 < 5%。

- [ ] **阶段 5 — TokenEconBench 接上实例**
  代码已在 `bench/`（原独立仓库已删除，方法论沉淀在 `PRODUCT.md`）。runner 从 `execFileSync("claude", ...)` 改为通过 Edge 公开协议驱动真实实例；生产与基准共用 `run_record` schema。
  **验收**：同一任务集在 pi 实例与 Hermes 实例上各出一份 Pareto 数据。
  附带：任务集目前只有 1 个（`coding/ts-ticker-format-01`），六个类别目录为空——按 `PRODUCT.md`「采集与再合成」的流程随真实工作增量积累。

- [ ] **阶段 6 — 工作区 UI / desktop / PTY**
  文件树与 diff、Tauri 壳、终端 WebSocket。未排期。

---

## P1 — 待定决策（阻塞上面某些阶段）

- [ ] **模型档位**：单一 default 模型，还是给用户开放档位选择？直接影响成本结构与 virtual key 预算策略。（阻塞阶段 1）
- [ ] **挂起阈值与冷启动预算**：空闲多久挂起、恢复延迟能接受到几秒。（阻塞阶段 2）
- [ ] **出网策略松紧**：全开最省事但沙箱形同虚设；只放行 gateway + 包管理源最安全但挡住"让 agent 上网查资料"。（阻塞阶段 1）

---

## P2 — 已记录的既有假设（如与设想不符，越早推翻越便宜）

- v1 一个用户一个实例；schema 允许多实例，UI 先不暴露。
- desktop = Tauri 包同一套 web UI；额外价值是可指向 Mac mini 上的本地运行时，而不只是云端容器。
- pi 包用 `@earendil-works/pi-coding-agent`（最新 0.84.2，Node 22+），与 buffett-tribe 的 pi-gateway 一致。
- pi 实例第一版不接飞书工具（`feishu_doc`/`feishu_drive` 是 Hermes 内建的，web 端场景优先级低）。

---

## P3 — 杂项

- [ ] `PRODUCT.md`「当前版本」停在 `v0.7.1`，实际 tag 已到 `v0.8.2`，需要对齐。
