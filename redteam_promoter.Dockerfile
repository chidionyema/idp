FROM python:3.12-slim
# See sovereign-worker.Dockerfile: the base floats, and on 2026-09-12 an upstream rebuild
# shipped perl-base 5.40.1-6 with three CRITICAL CVEs against a fix already published. Upgrade
# in the image so the fix is taken regardless of when the base was rebuilt.
RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY bin/redteam_promoter/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# The promoter reuses bin/rca_worker/worker.py's _persist and NegativeConstraint (LAW 43 -- one
# writer of via_negativa:banned_signatures). Both files ship in this image so the import by path
# resolves; the worker's own entrypoint is NOT run here, only its module.
#
# The two paths below are the repository's own, kept verbatim, because promoter.py resolves the
# worker relative to itself:
#
#     ROOT = Path(__file__).resolve().parent.parent      # promoter.py:69
#     WORKER_PATH = ROOT / "bin" / "rca_worker" / "worker.py"
#
# A flattened image (both files at /app) puts promoter.py at /app/promoter.py, which makes ROOT
# `/` and sends that import to /bin/rca_worker/worker.py -- absent, so `promote` raises at the
# moment it is asked to write. Keeping the layout makes ROOT /app and the path resolve.
#
# The build context is this repository's root, not bin/redteam_promoter. A COPY can only read its
# own context, and bin/rca_worker is outside a bin/redteam_promoter context -- that is why the
# previous Dockerfile's `COPY worker.py ./` could not resolve and the amd64 build failed with
# `"/worker.py": not found`. estate-mcp.Dockerfile and estate-scheduler.Dockerfile sit at the root
# for the same reason, and bin/dockerfiles names a `<name>.Dockerfile` by its stem, so this file
# still emits the image `redteam_promoter` that platform/via-negativa/redteam-promoter.yaml and
# platform/image-automation/via-negativa.yaml already deploy.
COPY bin/redteam_promoter/promoter.py bin/redteam_promoter/promoter.py
COPY bin/rca_worker/worker.py bin/rca_worker/worker.py
ENTRYPOINT ["python", "bin/redteam_promoter/promoter.py"]
CMD ["consume"]
