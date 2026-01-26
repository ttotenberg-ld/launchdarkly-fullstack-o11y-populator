FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared
COPY services/analytics-service/app.py /app/
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5007

ENV FLASK_PORT=5007
ENV SERVICE_NAME=analytics-service
ENV USE_DOCKER=true

CMD ["python", "app.py"]
