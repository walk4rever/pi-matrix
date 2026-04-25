# pi-matrix

**Your AI employee. Yours forever.**

[中文版](./README.zh.md)

pi-matrix is an edge-cloud AI employee that gets smarter the more you use it. Your AI remembers everything about you, and it all belongs to you—**a private digital asset that grows over time.**

---

## Why pi-matrix

**It remembers you (The Moat)**
Structured memory grows with every conversation. Most AIs forget you every day; pi-matrix builds a growing graph of your preferences, projects, and work style. The more you use it, the more indispensable it becomes.

**It belongs to you (The Trust)**
Your AI's memories, personality, and data are yours. Locked in your Mac mini, your data stays local. We don't train on your data. Export it, migrate it, or run it offline. You own the brain.

**Industrial-grade Reliability**
Stop gambling with AI hallucinations. We provide a curated, verified set of industrial-grade Skills. Whether it's deep Feishu automation or complex data analysis, you get consistent, predictable results—not just "suggestions."

**Zero setup**
No terminal. No config files. No API keys. Unbox a Mac mini, connect WiFi, start talking. Or try free on cloud—no hardware needed.

---

## Two Ways to Start

### Mac mini Edition — The Real Thing

A pre-configured Mac mini delivered to your door. Your AI runs locally, data stays local. Cloud services provide LLM access, memory sync, and backup — like iCloud for your AI.

- Your AI lives on your desk, not on someone else's server
- Works offline (with graceful degradation)
- One USB drive to take everything with you
- Best for: privacy-conscious professionals (lawyers, doctors, executives)

### Cloud Edition — Try It First

No hardware needed. Full-featured experience in your browser. Free for 30 days.

- Experience what "an AI that remembers you" feels like
- All memories and personality transfer seamlessly to Mac mini
- The hook isn't feature limits — it's memory retention

Both editions feel identical: send a message in Feishu or WeChat, your AI responds instantly.

---

## How It Works

```
  Your Device                          Cloud Services
  ───────────                          ──────────────

  [Mac mini / Cloud Container]
   AI Agent Runtime  ──── API ────→   LLM Gateway        (smart model routing)
   Local Data        ──── sync ──→    Memory Service     (structured, searchable)
   Full Home Dir     ──── backup ─→   Backup Service     (incremental, one-click restore)
```

No matter where the agent runs, it consumes the same cloud services. You don't care where your AI lives — you care that it knows you.

---

## Getting Started

1. Open Feishu on mobile and scan the QR code
2. Send any message to start
3. Complete registration to bind your account
4. Start talking — your AI is ready

---

## What's Built

- Feishu message routing + user identity binding
- Per-user isolated agent containers with persistent storage
- LLM Gateway with multi-model routing (LiteLLM)
- Dashboard: device status, memory management, personality settings, execution logs
- File delivery via Feishu Drive and Cloudflare R2
- Session management with automatic compression
- Personality injection (SOUL.md)
- Structured memory sync to cloud database

## What's Coming

- Memory Service (mem0 + pgvector) — structured, searchable, growing memory
- Backup Service — incremental sync, one-click device restore
- Mac mini one-click installer + auto-start
- WeChat channel support
- Memory export (standard JSON format)
- Pre-built personality templates

---

## License

MIT
