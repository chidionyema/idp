# syntax=docker/dockerfile:1
FROM rust:1.89-slim AS build
WORKDIR /src
COPY . .
RUN cargo build --workspace --release --locked

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /src/target/release/pennyd /usr/local/bin/pennyd
COPY config.example.toml /app/config.toml
COPY providers /app/providers
RUN mkdir -p /var/lib/pennyd && chown -R 65534:65534 /var/lib/pennyd
VOLUME ["/var/lib/pennyd"]
EXPOSE 4000
USER nobody
# k8s readinessProbe covers health; no curl in slim runtime
ENTRYPOINT ["/usr/local/bin/pennyd", "/app/config.toml"]
