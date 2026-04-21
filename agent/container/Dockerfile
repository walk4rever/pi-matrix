FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

RUN git clone --depth=1 https://github.com/NousResearch/hermes-agent.git /opt/hermes && \
    pip install --no-cache-dir /opt/hermes \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.29.0" \
    "httpx>=0.27.0"

WORKDIR /app
COPY inbox.py .

# Hermes user config: skills, SOUL, config
RUN mkdir -p /root/.hermes
COPY hermes-config.yaml /root/.hermes/config.yaml
COPY SOUL.md /root/.hermes/SOUL.md

ENV HERMES_MODEL=default
ENV ROUTER_REPLY_URL=""

CMD ["uvicorn", "inbox:app", "--host", "0.0.0.0", "--port", "8080"]
