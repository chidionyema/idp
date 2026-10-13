# The broker's image. Distroless, non-root, no shell: the one workload that can mint write
# access is not a workload anyone should be able to get a prompt inside.
# The build's Python must be the runtime's. distroless/python3-debian12 runs Debian 12's 3.11, and
# cffi (cryptography's dependency) ships a per-version extension: built on 3.12 it lands as
# _cffi_backend.cpython-312-*.so, which 3.11 cannot import. Measured 2026-10-13: jit-broker in
# CrashLoopBackOff (1112 restarts) on `No module named '_cffi_backend'` since the enrollment door
# added cryptography. tests/test_image_python_matches_runtime.py holds the pair together.
FROM python:3.11-slim-bookworm AS build
WORKDIR /w
# cryptography verifies the Ed25519 signature a first-time device makes with the estate age
# identity (ADR 0032). It is the same library the estate already trusts for TLS; the wheel is
# manylinux, so distroless picks it up without a build toolchain.
RUN pip install --no-cache-dir --target=/deps pyyaml==6.0.2 cryptography==42.0.5

FROM gcr.io/distroless/python3-debian12:nonroot
COPY --from=build /deps /app
COPY broker /app/broker
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
USER 65532
ENTRYPOINT ["python3", "-m", "broker.serve"]
