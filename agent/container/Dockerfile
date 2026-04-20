FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl git && \
    rm -rf /var/lib/apt/lists/*

# Install hermes-agent via official script (no venv, no interactive setup)
RUN curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh \
    | bash -s -- --no-venv --skip-setup

ENV PYTHONPATH="/root/.hermes/hermes-agent"

RUN pip install --no-cache-dir \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.29.0" \
    "httpx>=0.27.0"

WORKDIR /app
COPY inbox.py .

ENV HERMES_MODEL=default
ENV ROUTER_REPLY_URL=""

CMD ["uvicorn", "inbox:app", "--host", "0.0.0.0", "--port", "8080"]
