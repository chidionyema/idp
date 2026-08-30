"""crew#66, idp#895: every dispatchable workflow became a button on the portal's Create page, and
the tap failed, because the portal held no GitHub credential (`grep -rn GITHUB_TOKEN platform/`
found only hermes and mcp). The scaffolder's `github:actions:dispatch` step authenticates with the
portal's GitHub integration, so the portal needs a token with `actions: write`.

The estate never pastes a PAT (crew#577): a row in platform/github-app/token-consumers.json makes
bin/idp-github-app refresh mint a one-hour installation token of the App, narrowed to a lane, into
the vault entry the workload already reads. This test pins that row: entry backstage-env (the
ExternalSecret extracts the whole entry, so the field arrives as a mounted file), field
GITHUB_TOKEN, lane platform-engineer (the one lane carrying actions: write), and a `reads` path
that exists. Red both ways: the live file must carry the row, and a consumers file without it is
refused by the same check.
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONSUMERS = ROOT / "platform" / "github-app" / "token-consumers.json"
LANES = ROOT / "platform" / "github-app" / "lanes.json"

ROW = {
    "entry": "backstage-env",
    "field": "GITHUB_TOKEN",
    "lane": "platform-engineer",
    "reads": "platform/backstage/overlays/oke/backstage-external-secret.yaml",
}


def _portal_rows(doc):
    return [
        r
        for r in doc["consumers"]
        if r.get("entry") == ROW["entry"] and r.get("field") == ROW["field"]
    ]


def test_the_portal_has_a_consumer_row_on_the_dispatching_lane():
    doc = json.loads(CONSUMERS.read_text())
    rows = _portal_rows(doc)
    assert rows == [ROW], f"portal consumer row missing or drifted: {rows}"
    assert (ROOT / ROW["reads"]).is_file(), "the reads path must exist"


def test_the_lane_can_dispatch_workflows():
    lanes = json.loads(LANES.read_text())
    assert lanes[ROW["lane"]].get("actions") == "write", (
        "github:actions:dispatch needs actions: write on the portal's lane"
    )


def test_a_consumers_file_without_the_row_is_red():
    doc = json.loads(CONSUMERS.read_text())
    doc["consumers"] = [r for r in doc["consumers"] if r not in _portal_rows(doc)]
    assert _portal_rows(doc) == []
