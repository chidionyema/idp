FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pyyaml jsonschema
COPY . /app
ENV PYTHONPATH=/app
EXPOSE 8080
CMD ["python", "-m", "factory.server"]
