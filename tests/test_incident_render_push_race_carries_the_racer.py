"""Run 33705855559 (2026-09-03): bin/catalog-render and estate-state.yml both push
state/live-diagram; dispatched together, the render lost the force-with-lease and exited 1
after all its work. The founder's word: build the retry, don't schedule around the race.

The property: a refused lease refreshes the remote ref, re-carries the racer's files and
retries; it never gives up on the first refusal and never pushes without a lease.
"""

from pathlib import Path

RENDER = Path(__file__).resolve().parents[1] / "bin" / "catalog-render"


def test_push_retries_on_lease_refusal_carrying_the_racer():
    text = RENDER.read_text()
    assert "def push_carrying_the_racer" in text
    body = text.split("def push_carrying_the_racer")[1].split("\ndef ")[0]
    flat = " ".join(body.split())
    # retries, bounded
    assert "for _ in range(3)" in flat
    # every push keeps the lease; a bare force would clobber the racer instead of carrying it
    assert flat.count("--force-with-lease") >= 2
    assert '"--force",' not in flat and '"--force"]' not in flat
    # the retry refreshes the lease and re-carries the racer's files before pushing again
    assert "fetch" in flat and "refs/remotes/origin/" in flat
    assert "checkout" in flat and "--amend" in flat


def test_the_push_step_uses_the_retry():
    text = RENDER.read_text()
    assert "push_carrying_the_racer(carried)" in text
    assert 'step("push", ["git", "push", "-q"' not in text, (
        "the old single-shot quiet push is back; the race returns with it"
    )
