FROM python:3.12-slim
# See sovereign-worker.Dockerfile: the base floats, and on 2026-09-12 an upstream rebuild
# shipped perl-base 5.40.1-6 with three CRITICAL CVEs against a fix already published. Upgrade
# in the image so the fix is taken regardless of when the base was rebuilt.
RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# The promoter reuses bin/rca_worker/worker.py's _persist and NegativeConstraint (LAW 43 -- one
# writer of via_negativa:banned_signatures). Both files ship in this image so the import by path
# resolves; the worker's own entrypoint is NOT run here, only its module.
COPY promoter.py ./
COPY worker.py ./
ENTRYPOINT ["python", "promoter.py"]
CMD ["consume"]
