FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Install Hermes (for FeishuAdapter) + gateway deps
RUN git clone --depth=1 https://github.com/NousResearch/hermes-agent.git /opt/hermes && \
    pip install --no-cache-dir -e "/opt/hermes[all]" \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.29.0" \
    "httpx>=0.27.0" \
    "pydantic-settings>=2.0" \
    "supabase>=2.0.0" \
    "lark-oapi>=1.0.0" \
    "boto3>=1.34.0"

WORKDIR /app
COPY main.py config.py session_store.py delivery.py r2.py ./
RUN mkdir -p /app/sessions

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
