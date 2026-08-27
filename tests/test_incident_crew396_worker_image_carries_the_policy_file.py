"""crew#396: sovereign-worker crash-looped 18 times on OKE with
`PolicyError: cannot read /app/AGENTS.md` (oke-check 33038080419, 04:00Z).
sovereign/policy.py reads AGENTS.md from the directory above itself and
refuses to start without it; the image copied `sovereign/` and never the
file. Rule: every path the policy loader reads is copied into the image at
the place the loader resolves it. Rung 4, both ways."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "sovereign-worker.Dockerfile"


def copies(text: str) -> set[str]:
    out = set()
    for m in re.finditer(r"^COPY\s+(.+?)\s+(\S+)\s*$", text, re.M):
        out.add(m.group(2).rstrip("/"))
    return out


def policy_file_in_image(text: str) -> bool:
    """policy.py sits at /app/sovereign/policy.py, so it resolves /app/AGENTS.md."""
    return "/app/AGENTS.md" in copies(text) or "/app" in copies(text)


def test_the_worker_image_carries_agents_md_next_to_the_package():
    text = DOCKERFILE.read_text()
    assert "/app/sovereign" in copies(text)
    assert policy_file_in_image(text), "sovereign/policy.py needs /app/AGENTS.md"
    assert (ROOT / "AGENTS.md").is_file()


def test_an_image_without_the_policy_file_is_refused():
    stripped = DOCKERFILE.read_text().replace("COPY AGENTS.md /app/AGENTS.md\n", "")
    assert "/app/sovereign" in copies(stripped)
    assert not policy_file_in_image(stripped)
