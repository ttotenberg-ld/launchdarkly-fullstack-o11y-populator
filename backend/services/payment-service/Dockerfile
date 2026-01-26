FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared
COPY services/payment-service/app.py /app/
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5004

ENV FLASK_PORT=5004
ENV SERVICE_NAME=payment-service
ENV USE_DOCKER=true

CMD ["python", "app.py"]
