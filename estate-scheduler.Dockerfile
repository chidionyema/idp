# The estate scheduler, as it runs in the cluster (crew#716 CP1).
#
# The Mac scheduler (bin/scheduler-up) runs dagster-daemon and dagster-webserver on the Mac.
# This image moves both onto the cluster: the daemon ticks schedules and sensors, the webserver
# serves the UI. The user-code deployment (estate-scheduler) loads the definitions from
# scheduler/workspace.yaml the same way the Mac does.
#
# dagster 1.13.19, dagster-postgres 0.29.19, dagster-k8s 0.29.19: the library versions are
# pinned to match the helm chart 1.13.19. The version pairing is from the Dagster release table:
# chart 1.13.19 -> app 1.13.19 -> dagster 1.13.19, dagster-postgres 0.29.19, dagster-k8s 0.29.19.
# If the pairing ever drifts, the daemon will log a version mismatch at startup.
#
# Build context is the repository root (bin/dockerfiles: context = dirname).
# The image runs the gRPC server for user code: dagster api grpc -h 0.0.0.0 -p 3030 -m estate_scheduler.definitions
# The workspace.yaml loads the same code locations the Mac scheduler loads.
FROM docker.io/library/python:3.11-slim
WORKDIR /app/scheduler
# Non-root user: uid 10001, same as sovereign-worker.Dockerfile.
RUN useradd --system --uid 10001 --create-home scheduler
# Copy the scheduler code - the same paths workspace.yaml loads.
COPY scheduler/ /app/scheduler/
# Install dagster and its kubernetes library, matching the helm chart version.
RUN pip install --no-cache-dir \
    dagster==1.13.19 \
    dagster-postgres==0.29.19 \
    dagster-k8s==0.29.19
# The image runs as non-root.
USER scheduler
EXPOSE 3030
CMD ["dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "3030", "-m", "estate_scheduler.definitions"]
