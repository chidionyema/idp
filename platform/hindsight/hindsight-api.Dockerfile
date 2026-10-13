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
# here instead of in a CrashLoopBackOff.
RUN HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/tmp/hf-home /app/api/.venv/bin/python -c "\
from sentence_transformers import SentenceTransformer, CrossEncoder; \
print(SentenceTransformer('BAAI/bge-small-en-v1.5').encode(['ok']).shape); \
print(CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2').predict([('a', 'b')]))" \
    && rm -rf /tmp/hf-home
USER 1000
