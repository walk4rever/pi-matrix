# PRODUCT.md

内部产品设计与开发路线文档。对外介绍见 README.md。

---

## 当前版本

- `v0.9.0`

---

## 产品定位

**为企业提供某个领域/角色的 AI 员工——能力可验证，成本可预期。**

AI 员工 = **通用办公能力（底座）+ 领域技能（可插拔层）**。不同垂直领域需要不同的领域技能，因此交付单位是 **领域 × 角色**（如"金融投研 × 投研分析员"），不是一个通用聊天机器人。

参照 Harvey 在律所/法务行业的位置：垂直、深度、面向机构。差异在证明方式——

> Harvey 靠品牌和客户名单建立信任；我们靠**可复核、可回归的任务基准**。

### 核心命题：任务 = 能力

"能做合同审查"是不可证伪的形容词；"在这 N 个任务上完成率 X%、单任务成本 ¥Y"才是能力本身。**带判据的任务是能力的操作化定义**——离开判据，"能力"这个词没有内容。

由此推出：整个产品的原子不是角色、不是模型，而是**任务**。

- **任务集定义角色** —— 角色 = 一组被判据定义的任务。"投研分析员"不是人格设定，就是那 20–40 个任务。
- **任务集证明胜任** —— 交付物不是"一个 agent"，是一份可复核的胜任证明：完成率、单任务成本、升级前后的回归对比。
- **任务集是护城河** —— 它是行业 know-how 的结构化，比模型、比 prompt 都难复制。模型会换，判据是自己攒的。

配套效果：拆任务的过程本身就是销售动作——客户第一次被迫说清楚"我到底要它干什么、什么算做对了"，而那套验收标准只有我们在对着优化。

### 核心原则

1. **稳定性 > 性价比**。企业买垂直 AI 买的是免责和确定性，不是便宜（Harvey 贵得离谱照样有人买）。性价比是防守位——要能算清 ROI、不能贵到离谱；**可验证的稳定性才是主打**。这个排序决定了优先做判据与回归，而不是先做模型路由省钱。
2. **能力靠数据证明，不靠形容词**。每个能力主张背后必须有任务和判据，否则不写进材料。
3. **数据不出客户的网、不训练、全程可审计**。这是 B2B 语境下的数据主权，替代个人版"锁在你桌上的盒子里"的讲法。
4. **用户的选择/运维 → 0**。继承自个人版，仍然成立。

### 组织记忆 ≠ 个人记忆

护城河从"它懂你"变成"它懂你们公司"——合同模板库、内部制度、历史案例、客户档案。更值钱也更黏，但技术上是另一件事：多人共享、权限分级、审计留痕。现有的 `SOUL.md` + `USER.md`/`MEMORY.md` 个人记忆模型撑不起来，需要重做。
---

## 产品形态

### 两条线的关系

| | 个人版（现有） | 企业垂直版（新方向） |
|---|---|---|
| 状态 | 已上线，种子用户在用 | 设计中，从任务集起步 |
| 买家 | 个人专业人士 | 企业：用户是专员，付钱的是总监/CIO，验收可能是第三个人 |
| 渠道 | 飞书 | 飞书/企微=干活的地方，web=管理与审计的地方 |
| 运行时 | Hermes（冻结，不再演进） | pi 实例（沙箱、可跑真东西） |
| 护城河 | 个人记忆 | 任务集 + 组织记忆 |
| 投入 | 养着，不新增投入 | 新增投入都在这里 |

个人版的资产全部复用：容器生命周期管理、LiteLLM 网关、飞书通道、Supabase 多租户。换掉的是定位、买家和护城河。

**渠道分工的修正**：早期判断过"web 取代飞书"，在 B2B 垂直场景下这个判断不成立——合同审查员不需要看 agent 的文件树，企业本来就整天泡在飞书/企微里。**飞书线不冻结，它可能是干活的主渠道**；web 端承担管理者要的东西：用量、成本、质量报告、审计日志、角色配置。

**硬件 SKU 的位置也变了**：不再是"寄一台 Mac mini 到用户家"，而是"部署在客户机房/私有云"。对律所、医院、金融机构，数据不出内网是刚需而非卖点包装。但冷启动阶段做私有部署每单都是定制工程，先 SaaS 跑通一个角色拿到可复核数据，再用数据去谈私有部署的单。
### Mac mini 版（个人版主力，企业版形态见上）

预配置 Mac mini 邮寄给用户。Agent 运行时在本地，数据在本地。配套云服务提供 LLM 网关、记忆服务、数据备份——类似 iPhone + iCloud 的关系。

**核心卖点**：你的 AI 不住在硅谷的服务器上，它住在你桌上的盒子里。断网也能用，记忆永远属于你，一个 U 盘就能带走。

### 云端版（个人版体验入口）

无需硬件，开通即用。Agent 运行时在云端容器。功能与 Mac mini 版完全一致，但受限于云端成本，提供 30 天免费体验或低价订阅。

**核心目的**：让用户体验"被 AI 记住"的感觉。试用期积累的记忆和人格，购买 Mac mini 后无缝迁移。

**转化驱动**：不是功能限制，是记忆留存——30 天后你的 AI 已记住你 200 件事，这些记忆只在 Mac mini 版中永久保留。

### 端云协同模型（Cloud = iCloud）

无论 Agent 跑在 Mac mini 还是云端容器，用户获得统一的云服务层：

| 层 | 服务 | 说明 | 用户价值 |
|---|---|---|---|
| **Layer 3** | LLM 网关 | LiteLLM 代理，按用户配额，模型智能路由 | 无需管理 API key，自动选最优模型 |
| **Layer 2** | 记忆服务 | 自托管 mem0 + pgvector 语义检索 | AI 越用越懂你，跨设备记忆同步 |
| **Layer 1** | 备份与同步 | `/root/.hermes/` 增量同步到 S3/R2 | 设备损坏/更换一键恢复，多设备数据一致 |

Mac mini 版三层全享。云端版享 Layer 2+3，Layer 1 限于试用期数据。

```
  ┌──────────────────────────────────────────────────────┐
  │  用户视角：飞书/微信 ── 对话 ──→ 我的 AI 员工        │
  │  不关心 AI 住哪里，只关心"懂我"                      │
  └──────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────┐
  │  端侧                        云端                    │
  │                                                      │
  │  [Mac mini]                  [云服务层]              │
  │   Agent 运行时 ←── API ──→  LLM 网关 (Layer 3)      │
  │   本地数据     ←── 同步 ──→ 记忆服务 (Layer 2)       │
  │   完整 home    ←── 备份 ──→ 备份服务 (Layer 1)       │
  │                                                      │
  │  [云端容器]                  同一套云服务层           │
  │   Agent 运行时 ←── 同上 ──→  同上                    │
  └──────────────────────────────────────────────────────┘
```

### 用户交互方式

- **飞书**（MVP 首选，API 完善，开发友好）
- **企业微信**（Phase 2 接入）
- **微信个人版**（Phase 3，面向 C 端个人用户）

### 飞书 Bot 接入策略

我们统一建一个 Bot，用户无需接触飞书开放平台。

| 阶段 | 方式 | 说明 |
|---|---|---|
| MVP | 飞书自建应用 | 快速验证，用于种子用户测试 |
| 商业化 | 飞书 ISV 应用市场 | 任何用户/企业可授权，标准 SaaS 模式 |
| 海外 | Lark 国际版 | 独立平台，后续申请 |

**ISV 申请条件**：公司主体已注册（已具备），需提交营业执照 + 隐私政策 + 用户协议，审核约 1-4 周。MVP 阶段同步准备材料，不阻塞开发。

**用户身份绑定**：用户飞书 `open_id` 在注册时绑定到 pi-matrix 账号，后续所有消息按此路由。

### 数据归属原则

- 用户数据完全属于用户——包括记忆、人格、技能、工作产物
- 记忆可导出（标准格式），可迁移到其他平台
- Mac mini 版数据完整保留在本地，断网可用
- 云端数据可随时导出或删除
- 我们不使用用户数据训练模型

### 凭证与密钥管理原则（Credential Strategy）

目标：在不增加用户配置负担的前提下，做到最小权限、可审计、可轮换、可撤销。

#### 当前实现

容器内只有三个环境变量：

| 变量 | 用途 |
|---|---|
| `GATEWAY_KEY` | 调用 LiteLLM Gateway 的 API Key（当前所有容器共享同一个） |
| `GATEWAY_URL` | LiteLLM Gateway 内网地址 |
| `ROUTER_REPLY_URL` | 回复消息的 endpoint |

飞书 App Secret、Supabase key、Anthropic key 等平台核心凭证均未下发到容器。

#### 待实现：三层凭证模型

1. **平台凭证（Platform-owned）**
   - 例如：Feishu 应用密钥、Supabase service key、Gateway 主密钥、邮件服务密钥。
   - 仅允许在平台服务（Router/API/Orchestrator/Gateway）使用，不下发到用户容器。

2. **用户凭证（User-scoped）**
   - 例如：用户绑定的第三方 API Token（未来如 GitHub/Notion/企业内部系统）。
   - 按用户隔离存储，支持查看状态、轮换、撤销。

3. **会话临时凭证（Ephemeral）**
   - 按任务签发短期、最小权限凭证（TTL 分钟级），用于高风险调用场景。

#### 近期待做

- 将共享 `GATEWAY_KEY` 改为按用户/实例签发的受限子密钥，支持按用户计量和限速。

---

## 系统架构

```
[用户]
  └── 飞书/微信发消息

        ↓ 长连接（飞书 WebSocket / 企微回调）

[云端平台 — air7]
  └── Message Service（单入口，Hermes 原生飞书 Adapter）
      ├── 消息类型/附件下载/发送，原生语义
      ├── 会话管理（transcript 压缩、重置、命令拦截）
      ├── open_id → user_id → endpoint 路由
      ├── SOUL 注入（从 DB 加载人格设定，注入 executor 请求）
      ├── 记忆同步触发（执行后 fire-and-forget 拉取记忆文件 → DB）
      └── 执行日志落库
  └── API（FastAPI）
      ├── 设备注册、配置同步
      ├── Dashboard 后端（概览、记忆 CRUD、SOUL 编辑、执行日志查询）
      └── 用户凭证管理
  └── LiteLLM Gateway
      ├── 按用户虚拟 Key（配额 + 计量）
      ├── 模型智能路由（haiku/sonnet 分层）
      └── prompt caching
  └── Orchestrator
      ├── 云端版容器生命周期（provision / deprovision / sleep / wake）
      └── Mac mini 设备注册与心跳
  └── Memory Service（待建）
      ├── mem0 开源版内核（自托管，数据在 Supabase）
      ├── pgvector 语义检索
      └── Agent 通过 API 读写（非直接操作文件）
  └── Backup Service（待建）
      ├── /root/.hermes/ 增量同步到 S3/R2
      └── 设备更换时一键恢复
  └── 数据库 — Supabase（PostgreSQL + RLS 多租户隔离）

[Dashboard — Vercel]
  └── Next.js 用户控制台
      ├── 设备状态、在线/离线
      ├── 人格设定（SOUL.md 编辑）
      ├── 记忆管理（查看、搜索、编辑、导出）
      ├── 执行日志
      ├── 用量与配额
      └── 订阅管理

        ↓ 规范化执行请求

[Agent 实例]
  ├── 云端版：每用户独立容器（pi-matrix-{user_id}）
  │   └── 数据持久化：pi-matrix-home-{user_id} 卷 → /root
  │       ├── /root/.hermes/  （state DB、sessions、memories、skills、workspace）
  │       └── /root/（用户创建的任意文件，如 wiki/、项目目录等）
  └── Mac mini 版：本地运行 hermes-agent（launchd 自启）
      ├── 本地 /root/.hermes/ 完整数据
      ├── 通过云端 API 调用 LLM 网关
      ├── 通过云端 API 读写记忆服务
      └── 断网降级：本地缓存 + 小模型 fallback
```

**关键设计**：
1. **单 Bot 单入口消费**：共享飞书 Bot 只在 Message Service 入口消费，避免多容器重复消费冲突。
2. **语义归 Hermes**：飞书消息细节由 Hermes Feishu Adapter 处理，平台不手写消息语义分支。
3. **平台做治理 + 服务**：路由、凭证边界、审计、生命周期、计量，加上记忆服务和备份服务。
4. **端侧透明**：Agent 无论跑在 Mac mini 还是云端容器，通过统一 API 消费云服务层。
5. **记忆是服务，不是文件**：mem0 自托管版提供结构化记忆 + 语义检索，hermes-agent 通过 tool API 读写，而非直接操作 Markdown 文件。
6. **hermes 双记忆兼容**：hermes-agent 同时支持内置 memory（文件级）和 mem0（服务级），pi-matrix 优先走 mem0 服务，内置 memory 作为 fallback。

---

## 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| Agent 运行时 | hermes-agent | 版本锁定，非 fork，按版本号更新 |
| 结构化记忆 | mem0 开源版（自托管） | 增量记忆、语义检索、去重遗忘，数据在 Supabase |
| 向量存储 | Supabase pgvector | 与主数据库同实例，零额外运维 |
| 数据库 + Auth | Supabase | PostgreSQL + RLS 多租户，Auth 开箱即用 |
| 后端 API | FastAPI (Python) | 与 hermes 同语言，AI 生态兼容 |
| LLM Gateway | LiteLLM Proxy | 按用户虚拟 Key、模型路由、计量、限流 |
| Dashboard | Next.js | 部署在 Vercel |
| Mac mini 自启 | launchd | 开机自动运行，断电自恢复 |
| 云端实例 | Docker | 每用户独立容器，air7 托管 |
| 备份存储 | Cloudflare R2 | 增量备份，S3 兼容，无出站费 |
| 后端部署 | air7（自托管） | Docker Compose |
| 前端部署 | Vercel | Next.js 最优 |

---

## 项目结构

```
agent/                   # hermes 实例运行相关
  container/             # 云端版 Dockerfile、inbox.py、hermes_wrapper_runner.py
  installer/             # Mac mini 安装脚本 + 版本锁定
  launchd/               # Mac mini 开机自启配置
  config-template/       # hermes 配置模板

cloud/                   # 云端平台
  api/                   # FastAPI 主服务（设备注册、配置同步）
  router/                # 消息路由（/ingress/hermes-event、/reply）
  gateway/               # LiteLLM 配置
  orchestrator/          # 云端实例生命周期管理
  dashboard/             # Next.js 用户控制台（Vercel 部署）
  supabase/              # DB schema 与 migrations

deploy/                  # air7 部署配置
  docker-compose.yml     # gateway、router、hermes_wrapper、api、orchestrator
  .env.example           # 环境变量模板
```

---

## Hermes 版本管理策略

- hermes-agent 作为**依赖**，不 fork，不修改源码
- 版本号锁定在 `agent/installer/hermes.version`
- 云端容器版本锁定到 Hermes release tag，例如 `v2026.4.30`
- 升级流程：构建不可变镜像 → 更新 `EXECUTOR_IMAGE` / `HERMES_VERSION` → Orchestrator 灰度重建用户容器
- Mac mini 版通过 `agent/updater/update.sh` 执行
- 云端版通过 Orchestrator 滚动更新容器，保留 `pi-matrix-home-<user_id>` 持久卷，并在升级前创建 volume 快照

---

## pi Track — 云端实例（web/desktop）

> 与 Hermes 线并行的第二条产品线。**Hermes 线（`cloud/message`、`cloud/executor`、飞书通道）冻结，本节不改动它的任何契约。**
> 形态：用户自助开通属于自己的沙箱实例，实例里跑 [pi-coding-agent](https://github.com/badlogic/pi-mono)，通过 web/desktop 直接使用；每一轮执行留下可比较的成本与结果记录，平台据此评估自己提供的实例。

### 第一性原理

从"这个产品是什么"往下推，不从"现有代码怎么改"往下推。

1. **用户买的是一台随时可用的机器，不是一次问答。** → 单位是**实例**（持久工作区 + 会话历史 + 资源配额），可停可起，停了不花钱，起来还是原样。
2. **代理在替用户跑任意命令。** → 隔离是平台责任。pi 官方明确不提供沙箱（`docs/security.md`: *"Real isolation needs to come from the operating system or a virtualization/container boundary"*）。
3. **交互是连续的，不是原子的。** 飞书那套「一条进、一整段回」是 IM 逼出来的，web 端没有这个约束。→ 协议原语是**事件流**：文本增量、工具调用、队列变更、中断。（注意：**不含审批**——pi 没有工具审批机制，见下文实例层设计。）
4. **一份事件日志，三个消费者**：客户端渲染、会话持久化、计量统计。→ 计量必须是协议副产品，不是额外埋点。埋点会漂移，副产品不会。
5. **运行时的能力归运行时。** pi 自带会话树、fork/clone、compaction、steering、token/成本统计。→ **平台不实现任何会话逻辑**，只存元数据（有哪些会话、标题、最后活跃）用于不启动容器也能列表。这与 Hermes 线（平台自写 JSONL 存储 + LLM 压缩）是相反选择，因为那是被飞书逼的。
6. **能被度量的实例才敢卖。** → 生产遥测与离线基准产出**同一套记录 schema**，否则两边数字进不了同一张图。

### 明确不复用 Hermes 线的什么

| 不复用 | 原因 |
|---|---|
| `POST /execute` 一进一出契约 | 无法表达流式、审批、中断 |
| `message` 的 JSONL 会话存储 + LLM 压缩 | pi 自带会话树与 compaction，重复实现只会分叉 |
| `/files/{SOUL,USER,MEMORY}` 镜像 | 那是为"容器离线时 dashboard 也要显示"设计的；实例模型下用户看到的就是实例本身 |
| `PROGRESS_NOTIFY_URL` 推进度消息 | 那是在飞书里假装流式 |
| 容器常驻（`restart_policy: always`） | 编码会话是突发的，常驻是纯浪费 |

复用：Orchestrator 的容器生命周期思路（快照 → 替换 → 健康检查 → 失败回滚）、LiteLLM Gateway、Supabase auth + RLS、nginx 边缘、Dashboard 登录与外壳。

### 架构

```
[Web (Next.js) / Desktop (Tauri 壳同一套 UI)]
        │  HTTPS：POST 指令 / SSE 事件流（Last-Event-ID 断线续传）
        ▼
[Edge — 流中继]  鉴权(JWT→短时效 stream token) / 归属校验 / 转发 / 事件旁路写遥测
        ▼
[Instance — 每用户容器]
  ├── supervisor（Node，薄）：HTTP/SSE ⇄ pi RPC 的 JSONL stdio
  ├── pi --mode rpc            ← 运行时本体，不 fork、不改源码
  └── /workspace + ~/.pi/agent/sessions（持久卷）
        │  仅允许出网到 ↓
        ▼
[LLM Gateway — LiteLLM]  按实例发放 virtual key（额度 + 计量）

[Control Plane]  provision / suspend / resume / destroy / 配额 / key 签发
  └── 扩展现有 Orchestrator，新增端点，不动 Hermes 现有端点
```

**为什么实例里用 RPC mode 而不是 SDK 嵌入**：buffett-tribe 的 `pi-gateway` 用 SDK（`createAgentSession` + customTools）是因为要禁掉内建工具、注入业务工具；我们这里相反——要的就是完整的 pi。RPC mode 是官方为进程集成设计的模式，命令面覆盖 prompt / steer / follow_up / abort / new_session / get_state / get_messages / set_model / compact / bash / fork / clone / switch_session / get_session_stats / export_html；supervisor 只做搬运，升级 pi = 改一个 npm 版本号。自定义工具走 pi 的 extensions/skills 机制，不焊死在我们进程里。

> RPC 是严格 JSONL，只能按 `\n` 分帧——Node 的 `readline` 会额外在 `U+2028/U+2029` 断行，**不合规**，supervisor 必须自己分帧。

**客户端 ⇄ Edge 协议**：事件走 `GET /instances/:id/stream`（SSE，事件带单调 id，重连带 `Last-Event-ID`）；指令走 `POST /instances/:id/command`，body 即 RPC 命令对象，Edge 校验白名单后透传。**关掉标签页再打开，进行中的长任务必须还在**——这是飞书线从不需要面对、web 端必须做对的一件事（边界见下文「续传边界」）。

客户端在 agent 流式输出中再次发送时，pi 要求指定 `streamingBehavior`：默认 `follow_up`（排队），UI 提供 `steer`（打断并改向）开关；`queue_update` 事件直接渲染成待办队列。

### 实例层设计（读过 pi 的 RPC/session/provider/security 文档后定稿）

三个上游事实直接决定了下面的设计：

**1. pi 没有工具审批机制。** `--approve` 只管 *project trust*（要不要加载项目里的 `.pi/settings.json`、extensions、skills），与"执行 bash 前问一句"无关。RPC 模式下 agent 直接跑工具。

→ 协议里**不存在审批往返**，**容器就是唯一的边界，没有第二道闸**。隔离（阶段 1）不能往后排。
→ 唯一的阻塞式往返是 extension UI protocol（`confirm`/`select`/`input`/`editor`，stdout 发请求、stdin 等回应）。v1 不装自定义 extension，但 **supervisor 必须默认回 cancellation**，否则将来装了会问的 extension，agent 会静默挂死。

**2. 事件不带 id，但 `agent_end` 自带全部消息和逐条成本。** 序号与续传是 supervisor 的活；计量在 `agent_end` 结算（见 TokenEconBench 节）。

**3. RPC 有独立的 `bash` 命令，结果会进 agent 的下一轮上下文。** 同步返回 output/exitCode/truncated，内部生成 `BashExecutionMessage`，下次 `prompt` 时转成 UserMessage 一并发给模型。

→ **v1 的终端就是这条命令**，不需要 PTY/WebSocket，5% 的成本拿 80% 的价值。白送一个好性质：**用户手敲的命令，agent 下一轮就看得见**，人和 agent 共享同一个工作现场。真 PTY（交互式程序、流式输出）等真有人要再说。

#### 进程与会话模型

一个 `pi --mode rpc` 进程 = 一个活动会话；`switch_session` 能换但**串行**，一个进程伺候不了两个并发会话。

**定：supervisor 维护按 session id 索引的进程池，一会话一进程。** 不做"单进程 + switch_session 调度"——那是给本质不可共享的资源（agent loop 每会话单线程）写调度器。空闲会话进程 M 分钟后回收，会话文件在卷上，恢复时 `--session <path>` 重新拉起。v1 并发上限设小（1–3）。

已知副作用：同容器内并发会话共享文件系统，两个 agent 同时改同一文件会互相踩。等同于"一台机器上开两个终端"，可接受；真要隔离就是多实例。

#### 续传边界

| 故障 | 真相在哪 |
|---|---|
| 标签页关掉/网络断 | pi 进程还在跑，事件必须缓冲到重连 |
| supervisor 重启 | pi 进程也没了，进行中的运行本来就丢了 |
| 容器重启/恢复 | 唯一真相是 pi 的 session JSONL |

→ 事件日志**不需要活过容器重启**。内存环形缓冲 + 当前会话落一份有上限的文件，按运行边界截断。`Last-Event-ID` 落在窗口内则重放，落在窗口外或未知则客户端走 `get_messages` 拉全量状态再开新流。**有界重放 + 全量兜底**，不假装能无限回放。

#### LLM 接线：用 extension，不用 models.json

pi 支持 `pi.registerProvider("pi-matrix", { baseUrl, apiKey: "$GATEWAY_KEY", api: "openai-completions", models: [{ id, cost{...}, contextWindow, maxTokens }] })`。用 extension 而非 models.json，是为了显式声明两样东西：

- **`cost` 表** —— 否则 pi 算出的 cost 为 0 或错，run_record 直接失真。**这张表必须与 LiteLLM 实际计费同源**（镜像构建时从平台模型目录生成），否则两个成本数字对不上账。
- **`contextWindow`** —— 压缩阈值靠它，配错要么早压要么爆上下文。

#### 挂起判据

不能是"没客户端连着 N 分钟"——agent 可能正在无人值守地跑长任务。

**判据 = 没有运行在途（收到 `agent_start` 未收到对应 `agent_end`）且没有客户端连接且超过 N 分钟。**

#### cwd 约束与卷布局

session 文件路径是 `~/.pi/agent/sessions/--<cwd 路径>--/<ts>_<uuid>.jsonl`，**按 cwd 分目录**——cwd 一变，历史会话列表就"消失"。**v1 把 cwd 钉死为 `/workspace`**；多项目不是"换 cwd"，是多实例或带 session 目录处理的显式工作区切换。

```
/workspace              用户项目文件
/home/pi/.pi/agent/     sessions/、settings、models、trust.json
```

单卷两子路径，保证快照/恢复原子性（沿用 Hermes 线的教训）。非 root 用户 `pi`，home 在 `/home/pi`。

### 隔离与凭证

Hermes 线的现状作为反面基线记录在此（该线冻结，不改）：容器与 `gateway`/`orchestrator` 同在 `pi-matrix` docker 网络，容器内 root，**无 `mem_limit`/`nano_cpus`/`pids_limit`**（`cloud/orchestrator/containers.py:89`），注入的 `GATEWAY_KEY` 就是 LiteLLM 的 master key。飞书场景每轮有界还能忍；浏览器里随时开终端的沙箱不能这样。

pi 实例的硬性要求：

1. 非 root 运行；`mem_limit` / `nano_cpus` / `pids_limit` / `cap-drop ALL`；根文件系统只读，仅 `/workspace` 与会话目录可写。
2. 独立 docker 网络，**不与 orchestrator / api 同网**；出网只允许 LLM gateway 与显式放行的包管理源。
3. **容器内绝不放 master key。** 每实例签发 LiteLLM virtual key，带预算上限与模型白名单；泄露只影响一个实例，且天然按实例计量。需给 LiteLLM 配 `DATABASE_URL`（直接用 Supabase Postgres），现在的 `cloud/gateway/config.yaml` 只有 master_key，没有发 key 的能力。
4. 用户卷与镜像分离，沿用 Hermes 线已验证的快照/回滚流程。

### 生命周期

```
创建：点「开通实例」→ 分配卷 + 签发 virtual key + 起容器
挂起：空闲 N 分钟 → 停容器，保留卷（存储照付，算力不付）
恢复：下一条消息 → 起容器，pi 从会话文件继续
销毁：停容器 + 快照留存 X 天 + 回收 key
```

pi 镜像只有 Node + git + ripgrep（官方 `containerization.md` 的 Dockerfile 就这么点），比 Hermes 那个装了 playwright/chromium/CJK 字体的镜像轻一个量级，冷启动秒级——挂起/恢复才成立。

### 数据模型（新增，不动现有表）

```
pi_instances    id, user_id, status(provisioning|running|suspended|destroyed),
                image, runtime_version, volume, virtual_key_id, limits, last_active_at
pi_sessions     id, instance_id, pi_session_id, title, cwd, last_active_at, message_count
                ← 仅元数据，正文在实例卷里
pi_run_records  见下
```

沿用现有约定：`pi_` 前缀（共享 Supabase 实例）、RLS `auth.uid() = user_id`、服务端 service key 绕过。

### TokenEconBench — 能力的定义方式

原独立仓库 `walk4rever/token-econ-bench` 已并入本项目（代码在 `bench/`，方法论沉淀在本节，原仓库本地与远程均已删除）。

它在产品里的位置已经变了：**不只是度量工具，而是能力的定义方式**。见「核心命题：任务 = 能力」。所以它不是"做完产品再来测"，而是**先于产品**——你得先知道"合格"是什么，才谈得上造什么机器去达到它。

#### 任务优先：不预设分类学

**不先定义 domain/角色，直接从具体任务出发。** 理由：

1. 自上而下的分类学几乎必错。没有数据之前定义的领域和角色是猜的；真实聚类应该从任务里长出来。（现状即证据：`bench/` 里 7 个 category 是猜的、空的，任务是真的。）
2. 任务是唯一在所有情景下都保值的资产。无论最后落到哪个垂直、哪个买家，任务集都值钱——把"选哪个垂直"这个最缺信息的决定往后推。
3. 采集必须发生在工作刚做完的时候。凉了就采不成了——前态、判据、上下文都会丢。

**将来的 domain/角色 = 任务的组合。** 但要限定：任务组合出的是**能力证明**，不是**交付物**。一个可交付的角色还需要三样任务堆里长不出来的东西——多步骤流程（SOP）、客户的组织资料层、接入客户系统的工具。40 个通过的任务是很强的能力证明和销售材料，**但还不是一个能顶岗的员工**，别误判进度。

#### 替代分类学的两个标注

没有分类学就必须有别的纪律，否则采集会散成一堆互不相干的轶事。用两个**事实性标注**（采集时真知道的，不需要猜）：

**1. `capabilities: [...]` —— 能力标签。** 这个任务考的是什么能力，抽到跨领域可复用的层面：

```
extract-structured-data-from-documents   # 从非结构化文档提取结构化数据
localized-change-without-regression      # 在既有代码中做局部修改且不破坏既有行为
cross-verify-fact-with-citation          # 从多源资料交叉验证一个事实并保留溯源
generate-document-from-template          # 按既定模板生成合规文档
validate-untrusted-input-at-boundary     # 识别数据边界处的异常输入
```

标签用 kebab slug（报告按它聚合），后面跟中文注释。

这才是**可组合的真原子**，也是**唯一可迁移的部分**——将来第一个客户若在制造业，fixture 一个都用不上，能力标签全都用得上。"任务抽象出适配性"不会自动发生，它就发生在写这个标签的那一刻；不写，攒下的就是 40 个轶事。

**2. `provenance.workflow` —— 工作流出处。** 这个任务在真实工作里是哪条流程的哪一步。纯事实，将来聚类靠它，不靠回忆。

**`category` 降级**为目录组织方式，不进报告口径——报告按 `capabilities` 切才有意义。

#### 采集纪律

- **粒度**：一个任务 = 一次可验收的交付，大致对应人类 20 分钟–4 小时的工作量。超过的拆开，不到的合并或不收。否则能力主张不可比。
- **判据偏置**：会不自觉地专挑好写判据的任务（代码有测试），跳过商业上最值钱的判断型工作。**每采 3 个 `test` 任务，强制配 1 个 `llm_judge` 任务**——难写判据的那类才是护城河。置信度分级管的是报告，管不了采集偏好。
- **两个采集源**：金融/投资分析（源自 buffett-tribe 的真实工作，判据偏硬：数字对不对、能否溯源到原文）与 AI 应用工程（源自 ai-dive / pi-matrix 自己的工作，判据偏 `test`）。这两个源恰好落在判据类型的两端——同时能正确处理两端的基准框架，才扩得到第三个领域。**这不是"选两个格子做产品"，只是两个采集源**，承诺成本接近于零。

#### 从任务升级到角色的触发条件

不靠感觉，给硬条件：

> 某一组能力标签上累计 **≥15 个任务**，**且**有一个真实买家指着这组说"这就是我要的那个岗位"。

买家指认那一半是关键——没有它，封装出来的仍然是自己的猜测，只是换了个自下而上的姿势。

#### 出处与核心结论

方法论改编自 [Databricks 的内部编码代理基准](https://www.databricks.com/blog/benchmarking-coding-agents-databricks-multi-million-line-codebase)。他们的两个结论直接决定了这里的设计：

1. **token 单价是任务成本的糟糕代理**——要按真实用量 × 当前价格算，不能看 list price。
2. **harness 选择本身能在同等质量下让成本差 2 倍以上**——所以比较单位必须是 **(model × harness) 对**，不是模型单独。

对 pi-matrix 的直接含义：同一个模型跑在 pi 实例和 Hermes 实例上，成本可以差出一倍。这就是"默认给新用户哪套"必须用数据回答、不能靠感觉的原因。

#### 与 Databricks 做法的差异

| Databricks | 本项目 |
|---|---|
| 从网关日志批量挖掘已合并 PR | **一次一个**，在真实工作发生时手工采集——刻意的质量闸门，不是批量导入 |
| 筛选：近期、人写、有好测试、自包含 | 同样的筛选，在采集时施加 |
| 把 PR 描述改写成任务提示，剥掉解法 | 同 |
| held-out 测试作为唯一正确性判据，不用 LLM 裁判 | `test` / `structural_check` 同；`llm_judge` 只用于**不可能有确定性判据**的场景（设计创意、研究质量、系统品味），且每条结果强制标 `confidence: low` |
| 封存 git 历史，防止 agent 用 `git log` 走到答案 | fixture 根本不带 `.git`——没有历史可走。（一旦 fixture 需要包含提交历史作为素材，就得做真正的封存步骤，**目前记为未解决的缺口**） |
| 报成本-质量帕累托前沿与能力档位，不报单一排行分 | 同，刻意为之 |
| 公开基准会逐渐泄进训练数据 | 同样动机，且多一层：源材料还不能泄**机密**——见下文再合成 |

#### 为什么不做合成分

一个任务 60% 完成花 $0.10，另一个 95% 完成花 $2——在你说出成本与完成度之间的偏好之前，这两者不可比。塌缩成一个数字等于在数据还不够时就把偏好焊死。

主产物固定为：每任务/每类别的完成率（或带置信度标签的裁判分）、tokens（输入/输出/缓存）、墙钟时长、按真实用量算的 $ 成本、以及 (model × harness) 矩阵上的**成本-完成度帕累托图**。

可调权重的合成分只能作为**次级视图**，等真实数据多到足以支撑权重时再加——永远不做主产物。

#### 采集与再合成（privacy boundary）

一件真实工作变成任务的流程：

1. **发现候选**：自包含、有真实判据、有代表性（会反复出现，不是一次性边角）、够新（反映当前约定）。
2. **取前态**：工作开始前的工作区状态 → `fixture/`。
3. **写提示、剥解法**：保留功能规格与验收标准（缺了任务就欠定义）和真实约束；删掉"为什么这个解法对"的解释和任何实现形状的暗示。
4. **抽判据**：真实测试文件 / 结构检查脚本 / 裁判 rubric → `oracle/`。`test` 类判据必须确认 fixture 里没有该测试文件的残留副本。
5. **再合成**：把真实业务名、公司特定逻辑、财务数字、个人内容换成保留任务形状与难度的虚构等价物。**这一步每次都由人过一遍，不自动化——它就是隐私边界本身。** `provenance.source` 只写领域的泛化描述，绝不写私有仓库名、路径或 commit hash。
6. **落位并验证**：判据对着未修改的 fixture 必须**失败**（否则它什么都没测），正确解法必须让它通过。

#### 判据三档

| 类型 | 置信度 | 说明 |
|---|---|---|
| `test` | high | held-out 自动化测试集，二元通过/失败。唯一允许给出高置信二元结论的类型 |
| `structural_check` | medium | 确定性脚本检查产出形状/属性（如必需字段存在、diff 限定在 N 个文件内）。不含判断，但不验证行为。**如果你想亲眼看一下输出，那它就不属于这一类** |
| `llm_judge` | low | 裁判模型按书面 rubric 打分。多次采样暴露方差，理想情况由与被测模型不同且更强的模型来判，以减少自我偏好。每一行报告都带 low 标签，**绝不与前两类并排无标签呈现** |

#### 任务 schema

```
tasks/<category>/<task-id>/
  task.yaml      # id, category(降级为目录约定), title, prompt,
                 # capabilities: [...]                    ← 能力标签，报告口径
                 # oracle{type, confidence, ...}
                 # fixture.entry_files
                 # provenance{source, workflow, resynthesized}   ← workflow 为新增
                 # metadata{language, difficulty, est_human_time_minutes}
  fixture/       # agent 看到的起始工作区，原样拷进沙箱
  oracle/        # 对 agent 隐藏，仅在它报告完成后拷入
  README.md      # 出处说明与非显然的评分注意事项
```

类别：`coding` · `daily-ops` · `design-creative` · `research-engineering` · `system-taste` · `devops` · `long-horizon`。类别随真实工作浮现需求再加，不预先穷举。`system-taste` 覆盖"解法是否体现好的架构/系统判断"，与单纯的正确性区分开。

判据契约：`test` 把 held-out 路径并入工作区后跑 `test_command`，退出码 0 为通过；`structural_check` 直接对最终工作区跑 `check_command`，脚本本身永不离开 `oracle/`；`llm_judge` 跑 `judge_runs` 次，**报分布不报均值**。

#### 护栏

- fixture 每次拷进隔离的一次性临时工作区运行，绝不对着真实项目 checkout 跑。
- fixture 不带 `.git`。
- 判据不出现在 agent 看得到的工作区里，只在它报告完成后拷入。

#### 一份 schema，两个来源

```
run_record {
  source: "production" | "bench"
  instance_id, runtime, runtime_version, model
  tokens{input, output, cache_read, cache_write}, cost_usd, duration_ms, turns, tool_calls
  outcome: pass | fail | unknown
  outcome_kind: oracle_test | oracle_structural | llm_judge | user_rating | implicit
  task_id?, oracle_confidence?          ← 仅 bench
}
```

- **生产来源**：在 `agent_end` 事件处结算。该事件带回本次运行产生的全部消息，而每条 `AssistantMessage.usage` 自带 `cost{input, output, cacheRead, cacheWrite, total}`——**对本次运行的消息求和即得**，不需要埋点，也不需要对会话累计值做差分（差分会被并发会话污染）。turns 数 `turn_end`，tool_calls 数 `tool_execution_end`，model/provider 消息里带。
- **基准来源**：固定任务集跑真实实例，三类判据给结论。

#### 关键决策：bench runner 驱动的是实例，不是 CLI

原 `runner/run.mjs` 是 `execFileSync("claude", ...)`，harness 写死为 claude-code。改为通过 Edge 的公开协议驱动真实实例——**跑分对象就是我们卖的东西本身**，不是实验室里的另一套装置。副作用是 bench 天然成为镜像升级的准入门槛：pass 率或成本回归拦不住就不许上线。

原设计里的 harness 矩阵（Claude Code / Codex CLI / Gemini CLI / Pi / 开源模型自有工具）在并入后收敛为：**我们真正提供的实例形态** + 少量外部参照物（用于回答"我们的实例比用户自己开 Claude Code 贵还是便宜"）。

#### 生产环境没有 oracle

可用信号按可信度排序：用户显式评价（👍/👎）> 工作区测试命令的前后状态 > 隐式信号（短时间内重述同一诉求 ≈ 上一轮失败）。

**硬判定（bench）与软信号（生产）分开报，永远不合成一个分数**——与上文"不做合成分"是同一条原则的两个面。

#### 计量口径

两个成本数字并存，用途不同：LiteLLM 按 virtual key 的 spend 是**计费真相**；pi 的 `get_session_stats.cost` 是**按会话归因**（依赖 models.json 的价格配置，走自定义 provider 时要显式配价）。定期对账，偏差进监控。

#### 能回答的问题

- 真实用户一轮花多少钱？p50/p95 是多少？定价能不能覆盖？
- runtime 新版本是更好，还是只是更贵？（镜像升级的准入门槛）
- 哪类任务处在成本-完成率帕累托前沿的坏侧？该换模型档位还是该改提示？
- 同一批任务上 pi 实例 vs Hermes 实例——"默认给新用户哪套"的依据。

#### 现状

`bench/` 已有：一个采集好的任务（`tasks/coding/ts-ticker-format-01`，已再合成，出处为某金融数据管线的真实生产 bugfix，已回填 `capabilities` 与 `provenance.workflow`）、六个空类别目录、v0 runner、一次真实运行记录（haiku + claude-code，pass，$0.0593，43.6s）。

**下一步不是造实例，是攒任务。** 从日常工作中定义经常做的任务 → 用 pi + 某个模型跑 → 产出 baseline 数据 → 迭代。基线阶段用现成 harness 即可，不必等 pi 实例做好；那批数字反过来会告诉你实例该长什么样。

成本要说在前面：按「采集与再合成」那套流程，**一个任务少则半天多则两天**，走到一个角色的 20–40 个任务是几周的实打实工作。没法外包、没法批量——它就是护城河本身。


### 仓库结构增量

```
cloud/pi/instance/     实例镜像：pi --mode rpc + supervisor（Node）
cloud/pi/edge/         SSE 中继 + 鉴权 + 遥测分流
cloud/orchestrator/    扩展：新增 pi 实例端点，不动现有端点
cloud/gateway/         扩展：接 DATABASE_URL，启用 virtual key
bench/                 TokenEconBench：tasks/ + runner/ + reports/
```

---

## MVP 实施路线

### Phase 1 — 核心闭环 ✅ 完成

- [x] 飞书自建应用创建，获取 App ID / App Secret / Verification Token
- [x] `cloud/router/` 实现飞书消息接收 + 路由
- [x] hermes-agent 云端容器化运行
- [x] Router 将消息投递到 hermes，hermes 回复经 Router 发回飞书
- [x] Supabase 项目创建，设备注册
- [x] 用户 open_id 绑定到 pi-matrix 账号

### Phase 2 — 云端 SKU 可交付 ✅ 基本完成

- [x] Orchestrator：用户开通账号自动拉起独立容器
- [x] LiteLLM Gateway 部署，hermes 通过网关调用 LLM
- [x] Dashboard：Next.js 用户控制台（Vercel 部署，含设备状态、记忆管理、配置页面）
- [ ] 记忆服务（mem0 自托管 + pgvector）
- [ ] 记忆同步到云端（当前仅 USER.md/MEMORY.md 两文件 → 需升级为 Memory Service）

### Phase 3 — Mac mini 版可交付（未开始）

- [ ] 一键安装脚本打磨（install.sh 完整测试）
- [ ] launchd 自启动验证（断电重启场景）
- [ ] 出厂配置流程：用户账号 token 如何写入设备
- [ ] OTA 更新流程端到端验证

**交付标准**：Mac mini 开箱，连 WiFi，飞书发消息，爱马仕员工响应。

### Phase 4 — Hermes Gateway Wrapper 架构收敛 ✅ 完成

- [x] 平台单入口切到 Hermes Feishu Adapter（hermes_wrapper 服务）
- [x] `cloud/router` 切换为规范化事件投递模式（`/ingress/hermes-event`）
- [x] 平台停止手写飞书消息类型分支逻辑
- [x] 文件/附件链路：hermes_wrapper 下载后随消息传递，落盘到用户容器
- [x] 会话文件 manifest 持久化（session_uploads），跨轮对话可持续引用
- [x] 用户容器完整 home 持久化（`/root` 整体挂载为 named volume）

---

## 核心能力与差异化优势

### 核心能力

| 能力 | 说明 | 竞品现状 |
|---|---|---|
| **结构化记忆** | mem0 自托管，每条记忆独立实体，语义检索，越用越懂你 | ChatGPT/Claude 记忆是黑箱，不可导出/迁移 |
| **数据主权** | Mac mini 本地运行，记忆可导出（标准格式），断网可用 | 纯云服务商结构上做不到 |
| **人格可定制** | SOUL.md 定义 AI 行为准则与语气，用户完全掌控 | ChatGPT custom instructions 功能有限 |
| **端云协同** | 本地算力 + 云端 LLM + 云端记忆，互补而非互斥 | 多数产品要么纯云要么纯本地 |
| **零配置** | Mac mini 开箱连 WiFi 即用，云端扫码即用 | 竞品需要用户自部署/自维护 |

### 护城河

| 维度 | 壁垒 | 竞品难复制的原因 |
|---|---|---|
| **记忆图谱** | 用户 2000 条记忆在 pi-matrix，转到 ChatGPT 从零开始 | 网络效应：用得越久越离不开 |
| **数据主权架构** | Mac mini 端侧 + 云服务协同 | 纯云服务商结构上做不到端侧运行 |
| **飞书/微信原生** | open_id 绑定 + 消息路由 + 交互卡片 | 生态整合成本高，但可被复制 |
| **独立实例** | 每用户独立容器/进程，完整数据隔离 | 多租户共享实例体验差、隐私问题 |

**最强壁垒是记忆图谱**。技术架构可以被复制，但用户 6 个月积累的记忆和 AI 人格调教，迁移成本极高。这是 ChatGPT/Claude 结构性无法提供的——它们的记忆在云端、不可导出、不可迁移。

---

## 备选战略方向：Agent Runtime SaaS

> **状态：已被"企业垂直 AI 员工"取代为主方向，本节保留为备选记录，不实现。**
>
> 两者的关系：Runtime SaaS 是**平台路线**（做基础设施，让别人在上面发布 skill 并分成）；企业垂直是**产品路线**（自己做深一个领域的岗位并交付）。平台路线要求先有大量创作者和需求密度，冷启动难度高得多；垂直路线用任务集积累可验证的能力，路径清晰得多。若垂直路线跑通并积累出足够多的领域任务集与技能，再回头做平台不迟——**那时的冷启动素材就是自己攒的任务集**。

### 核心类比：Agent = OS，长任务 Skill = App

hermes-agent 是 Agent 的运行时，类似 macOS。
pi-matrix 现在做的事是：给普通用户提供一台"预装好系统、配好云服务"的 AI 设备。

但还有一层尚未开发的价值：

> **能在 Agent 上稳定长期运行的 Skill，是新型的 App。**

现在 hermes 的 skill 是 prompt 文件，任何人都能写，但没有：
- 安装 / 发布 / 版本管理
- 独立状态与持久化
- 外部用户调用与计费
- 创作者收益分成

一旦 Skill 获得上述能力，pi-matrix 就从"AI 员工产品"升级为 **Agent Runtime 平台**。

---

### 平台愿景：Vercel for Agents

**Vercel 解决的问题**：我写了一个 Next.js 应用，不想管服务器、不想管扩容、不想管 CDN。
**pi-matrix 对应解决的问题**：我有一个很好的 agent workflow（法律文书审查、采购合规检查、代码安全扫描……），不想管服务器、不想管 LLM key、不想管多租户、不想管计费——**我只想发布它，让别人付费用它。**

pi-matrix 现在已经有的基础：

| 已有 | 对应 Vercel 的什么 |
|---|---|
| 容器隔离 + 生命周期管理 | 部署环境隔离 |
| LiteLLM Gateway（计量/配额） | 带宽计量与账单 |
| 消息路由 | 请求路由 |
| 记忆服务 | 持久化存储 |

**缺的部分（未来实现）：**

1. **Skill 注册表**：发布、版本、描述、定价
2. **调用方认证**：谁在调用这个 skill，按量计费
3. **收益分成**：skill 创作者收多少，平台收多少

---

### 与现有竞品的真正差异

| 平台 | 做什么 | 缺什么 |
|---|---|---|
| Vercel / Railway | 部署 web 服务 | 不懂 agent，没有 LLM 网关，没有记忆层 |
| Zapier / Make | 连接 SaaS | 不是 agent，没有推理能力 |
| E2B / Modal | 代码执行沙箱 | 面向开发者工具，没有产品层 |
| **pi-matrix** | 已有 agent 运行时 + 记忆 + 路由 | 缺 skill 市场 + 创作者货币化 |

---

### 多 Runtime 支持（想法 1 的定位）

原计划：等第一个非 hermes 的需求出现再抽象 `AgentRuntime` 接口，避免过早设计。

**该触发条件已到**——见上文「pi Track — 云端实例（web/desktop）」。但结论不是"抽象一个共用接口让两条线都实现"：pi 线的交互形态（流式事件、web/desktop、实例可挂起）与 Hermes 线（飞书、原子消息、常驻容器）差异大到共用契约只会两头将就。两条线各自成立，共用的是下层设施（容器生命周期、LLM Gateway、Supabase、计量），不是上层契约。

Skill 创作者视角：短期仍只面向 hermes-compatible skill；pi 线的扩展走 pi 自己的 extensions/skills 机制。

---

### 实现节奏

```
现在        → 跑通种子用户 hermes 体验（Memory Service、SOUL 模板）
下一阶段    → 自己作为第一个 skill 创作者，在 pi-matrix 上发布内部 skill，验证机制
再下一阶段  → 开放 skill 发布给外部创作者，加入计费和分成
```

冷启动策略：Vercel 靠 Next.js 社区冷启动；pi-matrix 靠自己先跑通，再开放。

---

## 商业模式

### 企业垂直版（新方向，未验证）

- **定价单位是"岗位"，不是 token、不是座席。** 客户买的是"一个投研分析员"，按月/年订阅，包含约定的任务量。
- **定价的前提是知道成本。** 按岗位定价意味着**成本风险在我们这边**——必须先知道一个岗位一个月真实烧多少，这正是 TokenEconBench 的商业意义，不只是技术度量。
- **胜任证明是合同的技术载体**：任务集 + 完成率阈值 + 单任务成本上限，可以直接写进 SLA，也是续约谈判的依据。
- 私有部署另计（客户机房/私有云），冷启动阶段不主动接。

### 个人版（现有，养着）

- **Mac mini 版**：硬件一次性费用 + 云服务订阅
- **云端版**：30 天免费体验，或低价订阅
- 计量单位：LiteLLM Gateway 按 token 统计，套餐封顶

---

## 定价框架

### Mac mini 版

| 项目 | 定价 | 说明 |
|---|---|---|
| 设备一次性费用 | ¥4,800 | Mac mini 成本 + 出厂配置 + 物流 |
| 云服务订阅 | ¥149-299/月 | LLM 网关 + 记忆服务 + 备份同步 |

Mac mini 版经济模型优势：算力在用户本地，你几乎不承担边际 LLM 外的计算成本。每多一个用户，云成本增长可忽略不计（路由 + 记忆 + 备份，~¥5-10/用户/月）。

目标用户：对数据隐私有刚需的专业人士（律师、医生、金融从业者、高管），以及想要"AI 完全属于我"的个人用户。

### 云端版

| 套餐 | 月价 | 说明 |
|---|---|---|
| **体验版** | 免费 | 30 天体验，功能完整，积累的记忆可迁移到 Mac mini |
| **轻量版** | ¥49/月 | 长期云端使用，较低配额 |
| **专业版** | ¥199/月 | 完整配额，适合无硬件需求的用户 |

云端版经济模型约束：每用户独立容器 + LLM token 成本，毛利 40-60%。核心价值是引流和体验——让用户体验"被 AI 记住"，然后转化到 Mac mini。

### 企业版（未来）

| 项目 | 定价 | 说明 |
|---|---|---|
| 企业版 | ¥599/人/月 | SSO + 团队管理 + 审计日志 + 多员工编排 |
| Mac mini 企业版 | ¥4,800 + ¥399/人/月 | AI 数据不出公司 |

从 C 端个人版转化：当某个律师用了觉得好，律所 20 个律师都要——C 端用户是最好的销售员。

---

## GTM 路径

### 阶段 1：种子用户验证（当前）

- 免费邀请 20-50 人使用云端体验版
- 核心验证指标：
  - 每日使用频次（>3 次/天 = 有粘性）
  - 记忆积累速度（30 天后平均多少条记忆）
  - 7 天/30 天留存率
  - 用户自发描述 AI 的方式（"我的 AI" vs "一个 AI 工具"）
- 不定价，专注验证"被 AI 记住"是否是真实需求

### 阶段 2：Mac mini 早鸟（记忆服务上线后）

- Mac mini 首批 50 台，定向邀请种子用户中重度使用者
- 早鸟价：硬件 ¥3,999 + 服务 ¥99/月（锁定 1 年）
- 核心验证：云端用户 → Mac mini 转化率
- 关键钩子："你在云端积累的 XXX 条记忆，一键迁移到你的设备"

### 阶段 3：飞书 ISV + 公开销售

- 飞书 ISV 应用市场上线，获得自然流量
- 企业采购走对公流程
- C 端口碑带动 B 端转化（个人律师 → 律所团队）
- ISV 申请材料在 MVP 阶段同步准备，不阻塞开发

### 阶段 4：企业版扩展

- 基于 C 端积累的产品经验和用户数据，推出企业版
- 团队管理、SSO、审计日志、多员工编排
- 同样的 Mac mini 硬件方案："AI 数据不出公司"

---

## 近期技术优先级

> 顺序按新方向重排：**判据先行**。先知道"合格"是什么，才谈得上造机器去达到它。pi 实例的工程阶段整体后移——第一批任务用现成 harness 跑基线即可。

### P0 — 任务集与基线（护城河本身）

| 项目 | 说明 | 状态 |
|---|---|---|
| task.yaml schema 升级 | 加 `capabilities` 与 `provenance.workflow`，`category` 降级 | 已完成 |
| 日常任务采集 | 从真实工作中定义常做任务，按「采集与再合成」流程转成带判据的任务 | 进行中 |
| baseline 跑批 | pi + 某个模型跑任务集，产出首批 run_record | 待做 |
| 报告口径 | 按 `capabilities` 切的成本-完成率帕累托视图 | 待做 |

### P1 — pi 实例（服务于上面，不领先于上面）

| 项目 | 说明 | 状态 |
|---|---|---|
| 实例镜像 | `pi --mode rpc` + supervisor（HTTP/SSE ⇄ JSONL） | 待做 |
| 隔离与凭证 | 资源上限、独立网络、非 root、per-instance virtual key | 待做 |
| Control Plane | provision / suspend / resume / destroy | 待做 |
| Edge + web 界面 | SSE 中继 + 流式聊天 + 成本视图 | 待做 |

### P2 — 企业化能力（有买家指认后再做）

| 项目 | 说明 | 状态 |
|---|---|---|
| 组织记忆 | 多人共享的资料层 + 权限分级 + 审计留痕 | 待设计 |
| 领域工具接入 | 接客户系统（合同库/ERP/工单） | 待设计 |
| 多步骤流程（SOP） | 角色的工作流编排，不是一问一答 | 待设计 |
| 管理者视图 | 用量、成本、质量报告、审计日志 | 待做 |

### P3 — 个人版（养着，不新增投入）

原 P0–P3 中属于个人版的项目（容器 sleep/wake、deprovision 软删除、Memory Service、SOUL 模板、Backup Service、Mac mini 一键安装、转化流程等）整体降级。其中「按用户 Gateway Key」与「容器 sleep/wake」由 pi 线以更严格的形式先做（per-instance virtual key、挂起/恢复），个人版是否跟进另行决定。
---

## 成本结构与风险

### Mac mini 版成本（主力 SKU）

| 项目 | 成本/用户/月 |
|---|---|
| LLM（通过网关） | ~¥50-90（取决于用量和模型路由） |
| 记忆服务（pgvector） | ~¥2-5 |
| 备份存储（R2） | ~¥0.5-2 |
| 路由 + API + 杂项 | ~¥3-5 |
| **合计** | **~¥55-102** |

订阅 ¥149-299/月，毛利 **60-73%**。随着 prompt caching 和模型路由优化，LLM 成本有下降空间。

### 云端版成本（体验入口）

| 项目 | 成本/用户/月 |
|---|---|
| 容器（sleep/wake 优化后） | ~¥20-40 |
| LLM | ~¥50-90 |
| 记忆 + 备份 + 杂项 | ~¥5-10 |
| **合计** | **~¥75-140** |

订阅 ¥0-199/月，云端版毛利较低，核心价值是引流而非利润。

### LLM 成本优化方向

1. 模型智能路由：简单问答 → haiku（3x 成本节省），复杂任务 → sonnet
2. prompt caching：降低重复上下文成本
3. 按套餐配额封顶，超出需充值

### 关键风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| hermes-agent 方向不可控 | 核心体验依赖第三方 | 版本锁定 + 逐步建立自有记忆/技能层减少依赖 |
| 飞书 API 政策变化 | 渠道断线 | 多渠道策略（飞书→微信→Web），不依赖单一渠道 |
| Mac mini 硬件供应链 | 交付延迟 | 预备库存 + 探索其他硬件方案 |
| 云端版成本失控 | 毛利为负 | sleep/wake + 配额封顶 + 限时体验版 |
| 飞书 ISV 审核不通过 | 无法公开销售 | MVP 用自建应用，同步准备 ISV 材料（1-4 周） |
