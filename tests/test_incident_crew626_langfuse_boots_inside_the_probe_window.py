"""crew#626 CP15 (run 33259031857): crew#584 trimmed langfuse web and worker to a 50m CPU limit
(8493be89, 02:06Z). A Next.js server at 5% of a core never listened inside the 50 s liveness window
and was killed with exit 143, 164 times in 9 h; the old pod kept serving with the old SSO env, so
idp#810's AUTH_CUSTOM_ID_TOKEN never reached a serving pod and the founder read the same
OAuthCallback error for a day. Beside it, langfuse-redis's new pod sat Init:0/1 for 8 h with no
sandbox, and every helm-retry --reset stalled on it.

Guards: the two Langfuse Node services keep a boot-sized Guaranteed CPU (at least the fence line),
and helm-retry recreates a pod whose sandbox never started before it reconciles."""

from pathlib import Path


IDP = Path(__file__).resolve().parents[1]
FENCE_MILLICPU = (
    250  # platform/edge/capacity-policy.yaml: above this a request needs the label
)


def _millicpu(q: str) -> int:
    return int(q[:-1]) if q.endswith("m") else int(float(q) * 1000)


def test_diagnose_prints_langfuse_auth_env_and_log():
    src = (IDP / "bin/idp-oke-break-glass").read_text()
    body = src.split("pb_diagnose() {", 1)[1].split("\n}\n", 1)[0]
    assert "langfuse-auth-env" in body and "AUTH_CUSTOM_" in body
    assert "langfuse-auth-log" in body and "next-auth" in body
