# PRODUCT.md

内部产品设计与开发路线文档。对外介绍见 README.md。

---

## 产品定位

基于 [hermes-agent](https://github.com/nousresearch/hermes-agent)，打造可交付给用户的数字智能员工/助手。

**核心原则：用户的选择/运维 → 0**

用户无需任何技术背景，无需做任何配置决策，无需运维。

---

## 产品形态

### 两个 SKU

| SKU | 运行环境 | 适合场景 |
|---|---|---|
| **Mac mini 版** | 预配置 Mac mini，邮寄给用户 | 对隐私要求高，数据不离本地 |
| **云端版** | 我们托管的独立云实例 | 无需硬件，开通即用 |

两个版本用户体验完全一致，通过飞书或微信与爱马仕员工对话。

### 用户交互方式

- **飞书**（MVP 首选，API 完善，开发友好）
- **企业微信**（后续接入）

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

- 用户数据完全属于用户
- 云端数据可随时导出或删除
- Mac mini 版数据完全保留在本地

### 凭证与密钥管理原则（Credential Strategy）

目标：在不增加用户配置负担的前提下，做到最小权限、可审计、可轮换、可撤销。

#### 三层凭证模型

1. **平台凭证（Platform-owned）**
   - 例如：Feishu 应用密钥、Supabase service key、Gateway 主密钥、邮件服务密钥。
   - 仅允许在平台服务（Router/API/Orchestrator/Gateway）使用，不下发到用户容器。

2. **用户凭证（User-scoped）**
   - 例如：用户绑定的第三方 API Token（未来如 GitHub/Notion/企业内部系统）。
   - 按用户隔离存储，支持查看状态、轮换、撤销。

3. **会话临时凭证（Ephemeral）**
   - 按任务签发短期、最小权限凭证（TTL 分钟级），用于高风险调用场景。
   - 过期自动失效，降低泄漏影响。

#### 强制安全规则

- **最小权限**：默认只给完成当前任务所需的最小 scope。
- **禁止明文落盘**：凭证不得写入日志、对话消息、错误堆栈；统一做脱敏处理。
- **按层隔离**：平台主密钥与用户密钥完全隔离，权限边界清晰。
- **可审计**：记录谁在何时使用了哪类凭证访问了哪项能力。
- **可轮换**：支持平台凭证与用户凭证定期轮换，且不中断服务。

#### 当前实施优先级

1. 将容器内网关调用凭证从平台主密钥改为**受限子密钥**（按用户/实例授权）。
2. 建立统一 secrets 元数据管理（provider、scope、状态、最后使用时间、轮换时间）。
3. 为高风险外部调用引入短期凭证机制（ephemeral token）。

---

## 系统架构

```
[用户]
  └── 飞书发消息

        ↓ webhook（飞书回调我们的云端）

[云端平台]
  └── Router           — 接收飞书 webhook，按 open_id 识别用户，路由消息
  └── API（FastAPI）    — 设备注册、配置同步、记忆存储
  └── LLM Gateway      — 模型路由、用量计量（LiteLLM）
  └── Orchestrator     — 云端版实例生命周期管理
  └── Dashboard        — 用户 Web 控制台（Next.js）
  └── 数据库            — Supabase（PostgreSQL + RLS 多租户隔离）

        ↓ 消息投递

[Agent 实例]
  ├── 云端版：用户独立容器，直接接收
  └── Mac mini 版：设备与云端保持长连接，云端推送消息到本地 hermes
        └── hermes-agent（versioned dependency，非 fork）
```

**关键设计**：Mac mini 在用户本地网络（NAT 后），无法直接接收 webhook。所有消息统一经过云端 Router，Mac mini 主动与云端维持长连接接收推送。两个 SKU 的消息路径对用户完全透明。

---

## 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| Agent 运行时 | hermes-agent | 版本锁定，非 fork，按版本号更新 |
| 数据库 + Auth | Supabase | PostgreSQL + RLS 多租户，Auth 开箱即用 |
| 后端 API | FastAPI (Python) | 与 hermes 同语言，AI 生态兼容 |
| LLM Gateway | LiteLLM Proxy | 多模型路由、计量、限流 |
| Dashboard | Next.js | 用户控制台 |
| Mac mini 自启 | launchd | 开机自动运行，断电自恢复 |
| 云端实例 | Docker | 每用户独立容器 |
| 前端部署 | Vercel | Next.js 最优 |
| 后端部署 | Railway | FastAPI + LiteLLM，长驻进程 |

---

## 项目结构

```
agent/                   # hermes 实例运行相关
  installer/             # Mac mini 安装脚本 + 版本锁定
  launchd/               # Mac mini 开机自启配置
  container/             # 云端版 Dockerfile
  config-template/       # hermes 配置模板（含飞书接入参数）
  updater/               # OTA 更新脚本

cloud/                   # 云端平台
  api/                   # FastAPI 主服务
  router/                # 飞书 webhook 接收 + 消息路由（核心枢纽）
  gateway/               # LiteLLM 配置
  orchestrator/          # 云端实例生命周期管理
  dashboard/             # Next.js 用户控制台
  supabase/              # DB schema 与 migrations
```

---

## Hermes 版本管理策略

- hermes-agent 作为**依赖**，不 fork，不修改源码
- 版本号锁定在 `agent/installer/hermes.version`
- 升级流程：更新版本号 → 触发 OTA → 各实例拉取新版本并重启
- Mac mini 版通过 `agent/updater/update.sh` 执行
- 云端版通过 Orchestrator 滚动更新容器

---

## MVP 实施路线

### Phase 1 — 核心闭环（目标 2-3 周）

验证基本链路可行：

- [ ] 飞书自建应用创建，获取 App ID / App Secret / Verification Token
- [ ] `cloud/router/` 实现飞书 webhook 接收 + 签名验证
- [ ] hermes-agent 本地安装，配置飞书接入参数
- [ ] Router 将消息投递到本地 hermes，hermes 回复经 Router 发回飞书
- [ ] Supabase 项目创建，跑 001 migration
- [ ] FastAPI 设备注册 + 心跳接口本地验证
- [ ] 用户 open_id 绑定到 pi-matrix 账号

**交付标准**：本地 hermes 启动，飞书发消息能收到回复，消息经过云端 Router 路由。

### Phase 2 — 云端 SKU 可交付（目标 3-4 周）

云端版优先于 Mac mini 版上线，原因：无硬件物流，可快速找种子用户验证。

- [ ] Orchestrator：用户开通账号自动拉起独立容器
- [ ] LiteLLM Gateway 部署，hermes 通过网关调用 LLM
- [ ] Dashboard：用户登录、查看实例状态、修改配置
- [ ] 记忆同步：hermes 将上下文写入云端，跨会话保留

**交付标准**：注册账号 → 在飞书发消息 → 爱马仕员工响应，全程无需用户任何技术操作。

### Phase 3 — Mac mini 版可交付（目标 2-3 周）

- [ ] 一键安装脚本打磨（install.sh 完整测试）
- [ ] launchd 自启动验证（断电重启场景）
- [ ] 出厂配置流程：用户账号 token 如何写入设备
- [ ] OTA 更新流程端到端验证

**交付标准**：Mac mini 开箱，连 WiFi，飞书发消息，爱马仕员工响应。

---

## 商业模式

- **云端版**：纯订阅制，按月/年付费
- **Mac mini 版**：硬件一次性费用 + 云服务订阅
- 计量单位：通过 LiteLLM Gateway 按 token 用量统计，按套餐封顶
