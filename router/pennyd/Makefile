.PHONY: test clippy fmt build release run audit sbom image

test:
	cargo test --workspace

clippy:
	cargo clippy --workspace --all-targets -- -D warnings

fmt:
	cargo fmt --all -- --check

build:
	cargo build --workspace

release:
	cargo build --workspace --release

run: release
	./target/release/pennyd config.example.toml

audit:
	cargo audit

sbom:
	cargo cyclonedx --format json --output dist/sbom

image:
	docker build -t pennyd:local .
