# Warden job image - proves vendor API keys and publishes metrics
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY sovereign/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the warden module
COPY platform/warden /app/warden

# Set entrypoint
ENV PYTHONPATH=/app
ENTRYPOINT ["python", "-m", "warden.warden"]
