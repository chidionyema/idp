"""crew#539, 2026-08-27: oke-check receipt 33125739247 carried the autoscaler's Warning event as
`... Error returned by LaunchInstance operation in Compute service.(400, LimitExceeded` — the
collector kept 300 characters and OCI names the exceeded limit after that; the Kyverno audit row
ended at `failed at pa`. A receipt that cuts the word that says which limit is not a receipt
(LAW 28). Same class as crew#483, which fixed it for Flux messages and not for events.
Rule: an event message up to 500 characters is kept whole; a longer one keeps its head and its
tail, so the limit name / rule path at the end survives. Rung 4, incident test."""
import re
import textwrap
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"


def _event_message():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    collect = next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]
    m = re.search(r"^( *)def event_message\(msg: str\) -> str:\n(?:\1 .*\n|\n)+", collect, re.M)
    assert m, "event_message is defined inside the collector"
    assert 'event_message(e.get("message") or "")' in collect, "the events row uses it"
    assert '(e.get("message") or "")[:300]' not in collect, "the 300-char cut is gone"
    ns: dict = {}
    exec(textwrap.dedent(m.group(0)), ns)
    return ns["event_message"]


def test_a_long_oci_refusal_keeps_the_limit_name_at_its_tail():
    f = _event_message()
    msg = ("Failed adding 1 nodes to group ocid1.nodepool.oc1.region.aaaa due to OutOfResource.LimitExceeded; "
           "source errors: Error returned by LaunchInstance operation in Compute service." + "x" * 400 +
           "(400, LimitExceeded) The following service limits were exceeded: standard-a1-core-count.")
    out = f(msg)
    assert out.endswith("standard-a1-core-count.") and out.startswith("Failed adding 1 nodes")
    assert " ... " in out and len(out) < len(msg)


def test_a_short_message_is_kept_whole():
    f = _event_message()
    assert f("Back-off restarting failed container") == "Back-off restarting failed container"
    assert f("y" * 500) == "y" * 500
