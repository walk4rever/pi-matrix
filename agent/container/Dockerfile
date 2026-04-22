FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

RUN git clone --depth=1 https://github.com/NousResearch/hermes-agent.git /opt/hermes && \
    pip install --no-cache-dir "/opt/hermes[all]" \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.29.0" \
    "httpx>=0.27.0"

WORKDIR /app
COPY inbox.py .
COPY hermes-config.yaml /app/default-config.yaml
COPY SOUL.md /app/default-soul.md

# Hermes user config + persisted dirs: skills, state, workspace, SOUL, config
RUN mkdir -p /root/.hermes/skills /root/.hermes/state /root/.hermes/workspace
COPY hermes-config.yaml /root/.hermes/config.yaml
COPY SOUL.md /root/.hermes/SOUL.md

ENV HERMES_MODEL=default
ENV ROUTER_REPLY_URL=""
ENV HERMES_BUNDLED_SKILLS=/opt/hermes/skills
ENV HERMES_WORKSPACE_DIR=/root/.hermes/workspace

CMD ["uvicorn", "inbox:app", "--host", "0.0.0.0", "--port", "8080"]
