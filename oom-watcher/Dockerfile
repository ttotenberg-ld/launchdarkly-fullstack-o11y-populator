FROM python:3.12-slim

# util-linux gives us `dmesg`. Many slim images already include it, but the
# 3.12-slim base ships without the dmesg binary by default.
RUN apt-get update \
    && apt-get install -y --no-install-recommends util-linux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY oom-watcher/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY oom-watcher/watcher.py /app/

ENV PYTHONUNBUFFERED=1

CMD ["python", "watcher.py"]
