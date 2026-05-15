# Use Playwright's official Python image with browsers pre-installed.
# The image tag MUST match the `playwright` pip package version in
# simulator/requirements.txt — mismatches surface as missing system libs
# (e.g. libgtk-4-1 for WebKit), which crash-loops the container.
FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

WORKDIR /app

# Copy shared modules from backend
COPY backend/shared /app/backend/shared

# Copy simulator files
COPY simulator/traffic_generator.py /app/
COPY simulator/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers. Two engines (chromium + firefox) — Chrome,
# Edge, Safari, iOS, and Android profiles all ride chromium with UA / device
# overrides per-context (the session-replay UI keys browser identity off the
# UA string, not the underlying engine). WebKit on Linux (WPEWebProcess) was
# dropped after repeated cgroup OOM kills in the renderer; chromium and
# firefox are stable under sustained context churn.
RUN playwright install chromium firefox

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV FRONTEND_URL=http://frontend:80
ENV SESSIONS_PER_MINUTE=10
ENV MAX_CONCURRENT_BROWSERS=3

# Run the traffic generator
CMD ["python", "traffic_generator.py"]
