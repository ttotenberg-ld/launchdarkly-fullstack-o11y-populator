FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared
COPY services/inventory-service/app.py /app/
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5005

ENV FLASK_PORT=5005
ENV SERVICE_NAME=inventory-service
ENV USE_DOCKER=true

CMD ["python", "app.py"]
