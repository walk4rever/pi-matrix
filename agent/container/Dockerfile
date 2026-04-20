FROM python:3.12-slim

ARG HERMES_VERSION
RUN test -n "$HERMES_VERSION" || (echo "HERMES_VERSION required" && exit 1)

RUN pip install --no-cache-dir \
    "hermes-agent==${HERMES_VERSION}"

COPY ../config-template/hermes-config.yaml /etc/pi-matrix/hermes-config.yaml

CMD ["hermes", "--config", "/etc/pi-matrix/hermes-config.yaml"]
