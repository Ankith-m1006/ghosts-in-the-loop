# Episode sandbox: Python 3.12 + Node 22, nothing else. No credentials ever go in here.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates git procps \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs && rm -rf /var/lib/apt/lists/*
RUN useradd -m agent && mkdir /work && chown agent /work
USER agent
WORKDIR /work
