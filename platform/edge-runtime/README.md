# edge-runtime

Spec: `docs/specs/2026-09-06-model-forge-edge-runtime.md`, section 4. One artifact directory in,
`POST /v1/infer {task, input}` out, loopback only. The artifact is pulled by an `oras` init
container; the Runtime never talks to a registry (LAW 43: oras is the mature OCI client).

    EDGE_ARTIFACT_DIR=./artifact cargo run --release
    curl -s 127.0.0.1:8421/v1/infer -d '{"task":"voice-gate","input":"..."}' -H 'content-type: application/json'
    curl -s 127.0.0.1:8421/v1/health
