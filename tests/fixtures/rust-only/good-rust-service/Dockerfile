# The known-good service: Rust, built and run from a Rust base image. The gate must admit it.
FROM rust:1.83-slim AS build
WORKDIR /src
COPY Cargo.toml ./
COPY src ./src
RUN cargo build --release

FROM gcr.io/distroless/cc-debian12
COPY --from=build /src/target/release/service /app/service
USER 65532
ENTRYPOINT ["/app/service"]
