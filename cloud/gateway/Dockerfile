FROM python:3.12-slim
RUN pip install --no-cache-dir "litellm[proxy]>=1.40.0"
WORKDIR /app
COPY config.yaml .
CMD ["litellm", "--config", "config.yaml", "--port", "4000", "--host", "0.0.0.0"]
