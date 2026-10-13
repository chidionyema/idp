# The estate's hindsight api image: the vendor's 0.9.2 image plus the two local models it loads
# at boot, so the pod starts with no PVC and no network.
#
# WHY: #6088 swapped the 50GB modelCache PVC for an emptyDir on the claim that "the models are
# already on the image". They are not. The vendor image downloads them on first boot, and the
# PVC was the only copy (217M: bge-small-en-v1.5 + ms-marco-MiniLM-L-6-v2). The namespace fence
# allows no egress to huggingface.co and the api runs HF_HUB_OFFLINE=1, so the first pod on the
# emptyDir died with "couldn't connect to 'https://huggingface.co'" and CrashLoopBackOff
# (hindsight-api-6869b4d77, 2026-10-13 17:18Z).
#
# WHY NOT UNDER ~/.cache: platform/hindsight/hindsight.yaml mounts an emptyDir over
# /home/hindsight/.cache, which would hide anything baked there. The models live at
# /opt/hindsight-models and HF_HUB_CACHE points the hub client at them; HF_HOME (tokens, xet,
# locks) stays in the writable emptyDir.
#
# The revisions are the ones the PVC held (refs/main), so embeddings stay byte-compatible with
# the vectors already in estate Postgres. A different revision would change every new vector
# against every stored one.
FROM ghcr.io/vectorize-io/hindsight-api:0.9.2@sha256:7b14a1f4062252992d0176758753615e0a2071d9a269995be007be223ab01812

ENV HF_HUB_CACHE=/opt/hindsight-models/hub

USER root
# The vendor image ships six CRITICALs that have fixes, and the build's trivy gate refused it
# (build-multiarch on 8a3984f2b, 2026-10-13): perl-base 5.40.1-6 (CVE-2026-13221, -42496, -8376),
# PyJWT 2.13.0 (CVE-2026-102268), anyio 4.11.0 (CVE-2026-63374), sentence-transformers 5.2.0
# (CVE-2026-68770). Every pin in the venv admits the fixed versions (anyio<5, pyjwt<3,
# sentence-transformers>=5); the gate below proves the newer sentence-transformers still gives
# the vectors already stored.
RUN apt-get update \
    && apt-get install -y --no-install-recommends --only-upgrade perl-base \
    && rm -rf /var/lib/apt/lists/* \
    && uv pip install --python /app/api/.venv/bin/python --no-cache \
        'pyjwt[crypto]>=2.14.0' 'anyio>=4.14.2' 'sentence-transformers>=5.6.0'
RUN mkdir -p /opt/hindsight-models/hub \
    && HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 /app/api/.venv/bin/python -c "\
from huggingface_hub import snapshot_download; \
files = ['*.json', '*.txt', 'model.safetensors', 'README.md']; \
snapshot_download('BAAI/bge-small-en-v1.5', revision='5c38ec7c405ec4b44b94cc5a9bb96e735b38267a', allow_patterns=files); \
snapshot_download('cross-encoder/ms-marco-MiniLM-L-6-v2', revision='233902d25c440f23af6f7d6e94d2946bac0bee0a', allow_patterns=files)" \
    # A download by commit sha writes no refs/main, and the api asks for the model by name, which
    # offline resolves through refs/main. Write the ref the PVC had.
    && mkdir -p /opt/hindsight-models/hub/models--BAAI--bge-small-en-v1.5/refs \
                /opt/hindsight-models/hub/models--cross-encoder--ms-marco-MiniLM-L-6-v2/refs \
    && printf 5c38ec7c405ec4b44b94cc5a9bb96e735b38267a > /opt/hindsight-models/hub/models--BAAI--bge-small-en-v1.5/refs/main \
    && printf 233902d25c440f23af6f7d6e94d2946bac0bee0a > /opt/hindsight-models/hub/models--cross-encoder--ms-marco-MiniLM-L-6-v2/refs/main \
    && chmod -R a+rX /opt/hindsight-models
# Gate: both models must load with the network off, exactly as the pod will, or the build fails
# here instead of in a CrashLoopBackOff. They must also answer what the live 0.9.2 pod answers
# (hindsight-api-bcd445f9f-x6bkq, sentence-transformers 5.2.0, same revisions, 2026-10-13), or
# every new vector would drift from the stored ones.
RUN HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/tmp/hf-home /app/api/.venv/bin/python -c "\
from sentence_transformers import SentenceTransformer, CrossEncoder; \
v = SentenceTransformer('BAAI/bge-small-en-v1.5').encode(['the estate remembers'])[0]; \
s = float(CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2').predict([('a', 'b')])[0]); \
print(v.shape, list(v[:4]), s); \
assert v.shape == (384,); \
assert all(abs(float(a) - b) < 1e-3 for a, b in zip(v[:4], [-0.04894, 0.04007, 0.06701, -0.02038])), 'embedding drifted'; \
assert abs(s - -6.3800964) < 1e-2, 'reranker drifted'" \
    && rm -rf /tmp/hf-home
USER 1000
