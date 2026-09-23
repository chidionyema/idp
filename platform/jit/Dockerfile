# The broker's image. Distroless, non-root, no shell: the one workload that can mint write
# access is not a workload anyone should be able to get a prompt inside.
FROM python:3.12-slim AS build
WORKDIR /w
RUN pip install --no-cache-dir --target=/deps pyyaml==6.0.2

FROM gcr.io/distroless/python3-debian12:nonroot
COPY --from=build /deps /app
COPY broker /app/broker
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
USER 65532
ENTRYPOINT ["python3", "-m", "broker.serve"]
