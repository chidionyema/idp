# syntax=docker/dockerfile:1
FROM rust:1.89-bookworm AS build
WORKDIR /src
COPY Cargo.toml Cargo.lock .cargo ./
COPY src ./src
RUN cargo build --release --locked

FROM gcr.io/distroless/cc-debian12:nonroot
COPY --from=build /src/target/release/edge-runtime /edge-runtime
ENV EDGE_ARTIFACT_DIR=/artifact EDGE_BIND=127.0.0.1:8421
USER nonroot
ENTRYPOINT ["/edge-runtime"]
