# SPIRE Key Broker image.
# - OCI CLI: calls OCI Vault via workload identity (no static key)
# - spire-agent: verifies the caller's SVID before returning a key
# - Go broker: HTTP server + vault fetch
FROM ghcr.io/oracle/oraclelinux9-oci-cli:latest
# OCI CLI image is Oracle Linux 9 based. Install jq for JSON parsing.
RUN dnf install -y jq && dnf clean all

# Download the SPIRE agent binary. Used by the broker's verifySVID function to
# verify callers' SVIDs via the Workload API socket. The agent runs in the pod as
# a DaemonSet (spire-agent, separate from this binary); we only need the CLI.
ENV SPIRE_VERSION=1.15.3
RUN curl -fsSL \
        "https://github.com/spiffe/spire/releases/download/v${SPIRE_VERSION}/spire-${SPIRE_VERSION}-linux-x86_64.tar.gz" \
        -o /tmp/spire.tar.gz \
    && tar xzf /tmp/spire.tar.gz -C /tmp \
    && mv /tmp/spire-${SPIRE_VERSION}/bin/spire-agent /usr/local/bin/ \
    && chmod 755 /usr/local/bin/spire-agent \
    && rm -rf /tmp/spire*

# Copy the compiled broker binary and set ownership.
COPY --chown=10001:10001 spire-key-broker /usr/local/bin/spire-key-broker

# Run as non-root, matching the router's security posture.
USER 10001
ENTRYPOINT ["/usr/local/bin/spire-key-broker"]
