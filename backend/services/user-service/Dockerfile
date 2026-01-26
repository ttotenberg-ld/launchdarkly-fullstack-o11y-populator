FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared
COPY services/user-service/app.py /app/
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5002

ENV FLASK_PORT=5002
ENV SERVICE_NAME=user-service
ENV USE_DOCKER=true

CMD ["python", "app.py"]
