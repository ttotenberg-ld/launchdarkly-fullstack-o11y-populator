FROM python:3.11-slim

WORKDIR /app

# Copy shared modules first
COPY shared /app/shared

# Copy service-specific files
COPY services/api-gateway/app.py /app/
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_PORT=5000
ENV SERVICE_NAME=api-gateway
ENV USE_DOCKER=true

# Run the application
CMD ["python", "app.py"]
