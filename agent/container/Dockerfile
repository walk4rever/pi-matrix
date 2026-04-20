FROM python:3.12-slim

RUN pip install --no-cache-dir \
    "git+https://github.com/NousResearch/hermes-agent.git" \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.29.0" \
    "httpx>=0.27.0"

WORKDIR /app
COPY inbox.py .

ENV HERMES_MODEL=anthropic/claude-haiku-4-5
ENV ROUTER_REPLY_URL=""

CMD ["uvicorn", "inbox:app", "--host", "0.0.0.0", "--port", "8080"]
