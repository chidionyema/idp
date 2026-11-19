# Multi-arch (linux/arm64 + linux/amd64) build for Lane 1 Cloudflare Containers & Lane 2 OCI ARM A1
FROM rust:1.82-slim-bookworm AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends pkg-config ca-certificates && rm -rf /var/lib/apt/lists/*
COPY Cargo.toml ./
COPY migrations ./migrations
COPY src ./src
RUN cargo build --release --bins

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/genesis-ground-truth-d /usr/local/bin/genesis-ground-truth-d
COPY --from=builder /app/target/release/genesis-truth-boot /usr/local/bin/genesis-truth-boot
ENV GENESIS_DB_PATH=/var/lib/genesis/genesis.db
ENV GENESIS_BIND_ADDR=0.0.0.0:4001
EXPOSE 4001
ENTRYPOINT ["/usr/local/bin/genesis-ground-truth-d"]
