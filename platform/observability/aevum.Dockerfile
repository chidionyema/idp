# Aevum — the estate's evidence layer.
#
# THERE IS NO PUBLISHED CONTAINER, and this file exists because of that. Aevum publishes
# `aevum-server` to PyPI only; `ghcr.io/aevum-labs/*` returns 404 (checked 2026-09-12). A
# Deployment pointing at an image nobody published merges green, reconciles green, and then its
# ReplicaSet fails to pull forever. So the estate builds the image itself, the way it builds
# platform/jit and platform/edge-runtime.
#
# EVERY FAILURE BELOW WAS MEASURED IN THIS REPOSITORY'S CI, NOT GUESSED:
#
#   1. `apt-get install liboqs4` failed with exit 100 on both architectures: no such package. The
#      C library underneath the post-quantum signature is not available as an apt dependency of
#      this stack, so it is built here (step 5).
#
#   2. Installing aevum-core does NOT install `oqs`. Verified locally: a target install holds
#      every dependency except that one, and the image died at
#      `ModuleNotFoundError: No module named 'oqs'`. It matters because Aevum signs with Ed25519
#      AND post-quantum ML-DSA-65 by default and FAILS CLOSED without it -- the pod would have
#      crashlooped on every start. `liboqs-python` is therefore installed explicitly.
#
#   3. `liboqs-python` does NOT ship liboqs. Its README says so plainly: it is "a Python 3 wrapper
#      for the liboqs C library", and the library must already be present. With the bindings
#      installed alone the image died with `RuntimeError: No oqs shared libraries found`. So
#      liboqs is built from source here, pinned to the version the bindings wrap.
#
#   4. `liboqs4` and `liboqs2` were both guesses at a package name. Debian may carry a liboqs, but
#      the soname this base image would get is not something to bet a receipt on, and guessing
#      twice is how this build failed twice. platform/cyrus/Dockerfile sets the precedent: for a
#      dependency whose apt route did not work on arm64, build it from source.
#
# Pinned, never `latest`: a receipt is only as reproducible as the code that produced it, and
# policy disallow-latest-tag refuses an untagged image.
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/chidionyema/idp" \
      org.opencontainers.image.title="estate evidence layer (Aevum)" \
      org.opencontainers.image.description="Aevum HTTP API server wrapping the five governed functions."

# ca-certificates: the RFC 3161 timestamp client verifies a TSA over TLS.
# build-essential + cmake + ninja + git: what liboqs is compiled with, below.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates build-essential cmake ninja-build git \
 && rm -rf /var/lib/apt/lists/*

# aevum-server alone does NOT pull the pieces the factory needs:
#   aevum-store-postgres  PostgresLedger + initialize_ledger_schema
#   liboqs-python         the Python bindings for ML-DSA-65 (the C library is built at step 5)
#   cryptography          Ed25519PrivateKey for the signing key the vault holds
# All pinned to the same version family: 0.6/0.8/0.9 shipped API changes (measured 2026-09-12 --
# `Sigchain` has no `load_or_create` in any of them, and `aevum-store-migrate` is an
# Oxigraph->Postgres data migration, not schema creation).
RUN pip install --no-cache-dir \
      "aevum-server==0.9.0" \
      "aevum-store-postgres==0.9.0" \
      "liboqs-python==0.16.0" \
      "cryptography>=42"

# liboqs itself, built from source and installed where the bindings look for it. Pinned to the
# version liboqs-python==0.16.0 wraps. Without this the bindings import and then raise
# "RuntimeError: No oqs shared libraries found" on first use.
# The install prefix is NOT arbitrary. liboqs-python resolves the library in this order
# (oqs/oqs.py:256-269): $OQS_INSTALL_PATH, else $HOME/_oqs, and inside that <dir>/lib64 then
# <dir>/lib. It also auto-installs liboqs into $HOME/_oqs on first use -- which cannot happen for
# a pod running as uid 65532 with no writable home, so the library must be present at BUILD time
# in a path the bindings search. /usr/local/liboqs/lib is that path, and OQS_INSTALL_PATH names it.
ARG LIBOQS_VERSION=0.16.0
RUN git clone --depth 1 --branch "${LIBOQS_VERSION}" \
      https://github.com/open-quantum-safe/liboqs /usr/src/liboqs \
 && cmake -S /usr/src/liboqs -B /usr/src/liboqs/build \
      -GNinja \
      -DCMAKE_INSTALL_PREFIX=/usr/local/liboqs \
      -DOQS_BUILD_ONLY_LIB=ON \
      -DOQS_USE_OPENSSL=OFF \
 && cmake --build /usr/src/liboqs/build --parallel \
 && cmake --install /usr/src/liboqs/build \
 && echo /usr/local/liboqs/lib > /etc/ld.so.conf.d/liboqs.conf \
 && ldconfig \
 && rm -rf /usr/src/liboqs

# The variable liboqs-python reads before it decides to install its own copy.
ENV OQS_INSTALL_PATH=/usr/local/liboqs
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Non-root, matching the pod's runAsUser 65532: an image that needs root to start cannot run under
# the policy the Deployment applies to it.
RUN useradd --uid 65532 --no-create-home --shell /usr/sbin/nologin aevum
USER 65532:65532

# Assert the post-quantum signature is genuinely available, AS THE POD'S OWN USER. Aevum fails
# closed without it, so this is the difference between a failed build and a crashloop -- and
# checking as root would pass while the unprivileged pod still failed the same import.
RUN python -c "import os, oqs; \
    assert 'ML-DSA-65' in oqs.get_enabled_sig_mechanisms(), \
        'ML-DSA-65 unavailable: Aevum would fail closed on every write'; \
    assert os.getuid() == 65532, 'this check must run as the pod user'; \
    print('ML-DSA-65 enabled as uid', os.getuid())"

# The store is set by the Deployment's env from the vault, never defaulted here. Aevum's in-memory
# default reports a VALID empty chain after every restart, which looks present and records nothing.
ENTRYPOINT ["uvicorn", "aevum_factory:create", "--factory"]
CMD ["--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
