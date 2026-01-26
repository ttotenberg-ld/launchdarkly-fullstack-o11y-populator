FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared
COPY services/notification-service/app.py /app/
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5006

ENV FLASK_PORT=5006
ENV SERVICE_NAME=notification-service
ENV USE_DOCKER=true

CMD ["python", "app.py"]
