# Aevum — the estate's evidence layer.
#
# THERE IS NO PUBLISHED CONTAINER, and that is a fact this file exists to record. Aevum publishes
# `aevum-server` to PyPI only; `ghcr.io/aevum-labs/aevum-server` does not exist (checked
# 2026-09-12). A Deployment pointing at an image nobody published merges green, reconciles green,
# and then its ReplicaSet fails to pull forever. So the estate builds the image itself, the way it
# builds platform/jit and platform/edge-runtime, and pins the version here as a literal the same
# way .github/actions/estate-tools pins its seven CLIs.
FROM python:3.12-slim AS build
# Pinned by version, never `latest`: the ledger's receipts are only as reproducible as the code
# that produced them.
# aevum-server does NOT pull the store or the crypto bindings the factory needs:
#   aevum-store-postgres  PostgresLedger + initialize_ledger_schema
#   cryptography          Ed25519PrivateKey for the signing key the vault holds
# Without them the pod starts and then dies importing the factory. Pinned to the same version
# family as the server, because 0.6/0.8/0.9 have shipped API changes (measured 2026-09-12:
# Sigchain has no load_or_create in ANY of them, and aevum-store-migrate is Oxigraph->Postgres
# data migration, not schema creation).
RUN pip install --no-cache-dir --target /out \
      "aevum-server==0.9.0" \
      "aevum-store-postgres==0.9.0" \
      "cryptography>=42"

FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/chidionyema/idp" \
      org.opencontainers.image.title="estate evidence layer (Aevum)" \
      org.opencontainers.image.description="Aevum HTTP API server wrapping the five governed functions."
# ML-DSA-65 is what makes the chain post-quantum, and Aevum FAILS CLOSED without it -- an image
# missing liboqs does not degrade politely, it refuses every write. It comes from the
# `liboqs-python` wheel (a dependency of aevum-core), which builds liboqs from source into the
# package itself: measured 2026-09-12, `oqs.get_enabled_sig_mechanisms()` lists ML-DSA-65 with no
# system package installed. An earlier draft of this file apt-installed `liboqs4`, which does not
# exist in the Debian archive -- the image failed to build on both architectures with apt exit 100.
# ca-certificates is still installed: the RFC 3161 timestamp client verifies a TSA over TLS.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates build-essential cmake ninja-build git \
 && rm -rf /var/lib/apt/lists/*
COPY --from=build /out /usr/local/lib/python3.12/site-packages
# The build tools installed above are what liboqs-python compiles against on first import, so the
# import is forced here: a missing toolchain would otherwise surface as a crashloop at runtime
# rather than a failed build. It also proves the post-quantum signature is actually available.
RUN python -c "import oqs; assert 'ML-DSA-65' in oqs.get_enabled_sig_mechanisms(), \
    'ML-DSA-65 unavailable: Aevum would fail closed on every write'; print('ML-DSA-65 enabled')" 
# Non-root, matching the pod's runAsUser 65532: an image that needs root to start cannot run under
# the policy this Deployment applies to it.
RUN useradd --uid 65532 --no-create-home --shell /usr/sbin/nologin aevum
USER 65532:65532
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8080
# The store is the estate's Postgres, set by the Deployment's env, never defaulted here. Aevum's
# in-memory default would report a valid empty chain after every restart.
ENTRYPOINT ["python", "-m", "aevum.server"]
CMD ["--host", "0.0.0.0", "--port", "8080"]
