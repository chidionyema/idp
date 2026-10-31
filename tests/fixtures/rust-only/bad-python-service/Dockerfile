# The known-bad service: Python written into an image that targets the k3s spine.
# The gate must refuse it, with the exact message, every time.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY worker.py ./
ENTRYPOINT ["python", "worker.py"]
