.PHONY: ci fmt clippy test
ci: fmt clippy test
fmt:; cargo fmt --all -- --check
clippy:; cargo clippy --all-targets -- -D warnings
test:; cargo test --verbose
