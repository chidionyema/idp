FROM python:3.12-slim
# See sovereign-worker.Dockerfile: the base floats, and on 2026-09-12 an upstream rebuild
# shipped perl-base 5.40.1-6 with three CRITICAL CVEs (CVE-2026-13221, CVE-2026-42496,
# CVE-2026-8376) against a fix already published as 5.40.1-6+deb13u1.
RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY worker.py schema.sql ./
ENTRYPOINT ["python", "worker.py"]
