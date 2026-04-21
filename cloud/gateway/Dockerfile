FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends gettext-base && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "litellm[proxy]>=1.40.0"
WORKDIR /app
COPY config.yaml config.yaml.tpl
CMD ["/bin/sh", "-c", "envsubst < config.yaml.tpl > config.yaml && litellm --config config.yaml --port 4000 --host 0.0.0.0"]
