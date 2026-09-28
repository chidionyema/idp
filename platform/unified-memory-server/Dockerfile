# unified-memory-server: the estate's memory layer (§6: exactly one). Image:
# ghcr.io/chidionyema/unified-memory-server (bin/dockerfiles names it after this directory).
# Postgres is estate-db; this image is the API alone. It calls no model and no vendor.
FROM docker.io/library/python:3.13-alpine
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY main.py security_core.py schema.sql /app/
WORKDIR /app
USER 10001:10001
EXPOSE 8000
# One worker: the pod scales to zero and back on requests (KEDA HTTP), not on processes.
ENTRYPOINT ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
