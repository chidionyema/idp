# Multi-stage portable OCI image for genesis-harness-v1 (Lane 1 Cloudflare Containers / Lane 2 / Lane 3)
FROM rust:1.83-slim-bookworm AS builder
WORKDIR /build
COPY Cargo.toml ./
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates     && rm -rf /var/lib/apt/lists/*     && useradd -m -u 10001 harness
COPY --from=builder /build/target/release/genesis-harness-v1 /usr/local/bin/genesis-harness-v1
USER harness
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/genesis-harness-v1"]
