# Use Playwright's official Python image with browsers pre-installed
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Copy shared modules from backend
COPY backend/shared /app/backend/shared

# Copy simulator files
COPY simulator/traffic_generator.py /app/
COPY simulator/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only for smaller image)
RUN playwright install chromium

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV FRONTEND_URL=http://frontend:80
ENV SESSIONS_PER_MINUTE=10
ENV MAX_CONCURRENT_BROWSERS=3

# Run the traffic generator
CMD ["python", "traffic_generator.py"]
