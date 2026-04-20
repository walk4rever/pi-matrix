# LLM Gateway

Powered by [LiteLLM Proxy](https://docs.litellm.ai/docs/proxy/quick_start).

## Run locally

```bash
pip install litellm[proxy]
litellm --config config.yaml --port 4000
```

## Deploy to Railway

Add env vars from `.env.example`, set start command:
```
litellm --config config.yaml --port $PORT
```
