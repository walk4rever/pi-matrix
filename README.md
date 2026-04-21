# pi-matrix

**Your personal iHermes employee, ready out of the box.**

[中文版](./README.zh.md)

pi-matrix is an AI employee platform built on hermes-agent. It delivers a production-ready assistant experience through **Feishu (Lark)** with near-zero setup for end users.

---

## Current Product Scope (v0.3.x)

- **Primary channel:** Feishu / Lark
- **WeChat / WeCom:** planned, not the current default flow
- **Runtime:** one isolated Hermes container per user (cloud SKU)
- **Session continuity:** Hermes native session persistence enabled

---

## Onboarding Flow (Current)

1. Open Feishu on mobile and scan the QR code
2. Enter the iHermes chat and send any message
3. Receive the registration card, complete signup, and click the email link to bind
4. Start chatting directly in Feishu

This keeps identity binding explicit (`open_id -> user`) and avoids fragmented signup paths.

---

## Two SKUs

### Mac mini Edition
A pre-configured Mac mini shipped to users. Data stays on local hardware.

### Cloud Edition
No hardware required. We host a dedicated cloud instance per user.

Both SKUs are designed to feel the same from the user perspective: talk to iHermes in Feishu.

---

## What’s Implemented

- Feishu router + user binding flow
- API / Gateway / Orchestrator service stack
- Per-user agent container provisioning
- Hermes native session persistence with per-user state volume
- Tool progress messages in Feishu (e.g. terminal / execute_code / clarify)

---

## License

MIT
