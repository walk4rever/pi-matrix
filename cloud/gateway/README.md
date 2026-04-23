# LLM Gateway (LiteLLM Proxy)

This is the **LLM Gateway**, not the Platform Gateway.

- **LLM Gateway** (`cloud/gateway/`) = LiteLLM Proxy that routes LLM requests to upstream providers.
- **Platform Gateway** (`cloud/platform-gateway/`) = Feishu adapter + session router + message delivery. This holds Feishu credentials.

## Run locally

```bash
pip install litellm[proxy]
litellm --config config.yaml --port 4000
```

## Deploy

```bash
docker compose up -d gateway
```
