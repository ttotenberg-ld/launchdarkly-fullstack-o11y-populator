FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared
COPY services/auth-service/app.py /app/
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5001

ENV FLASK_PORT=5001
ENV SERVICE_NAME=auth-service
ENV USE_DOCKER=true

CMD ["python", "app.py"]
