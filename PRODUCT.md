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

两个版本用户体验完全一致，通过飞书或微信与数字员工对话。

### 用户交互方式

- **飞书**（MVP 首选，API 完善，开发友好）
- **企业微信**（后续接入）

### 数据归属原则

- 用户数据完全属于用户
- 云端数据可随时导出或删除
- Mac mini 版数据完全保留在本地

---

## 系统架构

```
[用户]
  └── 飞书 / 微信 发消息

        ↕ Bot API

[Agent 实例]  ← Mac mini 本地 或 我们的云容器
  └── hermes-agent（versioned dependency，非 fork）
  └── IM Bot Connector（hermes gateway 模块）
  └── 本地数据

        ↕ HTTPS

[云端平台]
  └── API（FastAPI）    — 设备注册、配置同步、记忆存储
  └── LLM Gateway      — 模型路由、用量计量（LiteLLM）
  └── Orchestrator     — 云端版实例生命周期管理
  └── Dashboard        — 用户 Web 控制台（Next.js）
  └── 数据库            — Supabase（PostgreSQL + RLS 多租户隔离）
```

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

- [ ] 飞书 Bot 与 hermes-agent 集成，消息收发端到端跑通
- [ ] Supabase 项目创建，跑 001 migration
- [ ] FastAPI 本地启动，设备注册 + 心跳接口验证
- [ ] 设备能从云端拉取配置（`GET /config/device`）

**交付标准**：本地 Mac mini 上 hermes 启动，飞书发消息能收到回复。

### Phase 2 — 云端 SKU 可交付（目标 3-4 周）

云端版优先于 Mac mini 版上线，原因：无硬件物流，可快速找种子用户验证。

- [ ] Orchestrator：用户开通账号自动拉起独立容器
- [ ] LiteLLM Gateway 部署，hermes 通过网关调用 LLM
- [ ] Dashboard：用户登录、查看实例状态、修改配置
- [ ] 记忆同步：hermes 将上下文写入云端，跨会话保留

**交付标准**：注册账号 → 在飞书发消息 → 数字员工响应，全程无需用户任何技术操作。

### Phase 3 — Mac mini 版可交付（目标 2-3 周）

- [ ] 一键安装脚本打磨（install.sh 完整测试）
- [ ] launchd 自启动验证（断电重启场景）
- [ ] 出厂配置流程：用户账号 token 如何写入设备
- [ ] OTA 更新流程端到端验证

**交付标准**：Mac mini 开箱，连 WiFi，飞书发消息，数字员工响应。

---

## 商业模式

- **云端版**：纯订阅制，按月/年付费
- **Mac mini 版**：硬件一次性费用 + 云服务订阅
- 计量单位：通过 LiteLLM Gateway 按 token 用量统计，按套餐封顶
