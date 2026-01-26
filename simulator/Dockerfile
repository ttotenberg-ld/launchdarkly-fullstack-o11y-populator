FROM python:3.11-slim

WORKDIR /app

# Copy shared modules from backend
COPY backend/shared /app/backend/shared

# Copy simulator files
COPY simulator/traffic_generator.py /app/
COPY simulator/requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV API_GATEWAY_URL=http://api-gateway:5000
ENV REQUESTS_PER_MINUTE=30
ENV ERROR_SESSION_RATE=0.15

# Run the traffic generator
CMD ["python", "traffic_generator.py"]
