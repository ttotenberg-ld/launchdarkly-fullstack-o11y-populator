FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared
COPY services/order-service/app.py /app/
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5003

ENV FLASK_PORT=5003
ENV SERVICE_NAME=order-service
ENV USE_DOCKER=true

CMD ["python", "app.py"]
