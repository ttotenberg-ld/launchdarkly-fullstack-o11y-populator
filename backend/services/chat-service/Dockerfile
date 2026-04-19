FROM python:3.11-slim

# Unbuffered stdout/stderr so `docker compose logs` shows Flask/LD output
# in real time instead of waiting for the buffer to fill.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY shared /app/shared
COPY services/chat-service/app.py /app/
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5009

ENV FLASK_PORT=5009
ENV SERVICE_NAME=chat-service
ENV USE_DOCKER=true

CMD ["python", "app.py"]
