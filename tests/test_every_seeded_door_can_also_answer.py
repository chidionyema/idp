"""A binding row the seed creates is a channel the door answers on -- or it is a lie.

`platform/otto-gateway/binding-seed.yaml` is where a channel comes into existence: the init
container puts these rows in `channel_binding` before the first message can arrive, and the
door decides which plugin, which principal and which authority a message gets by looking its
channel up there. Three properties of a row decide whether the turn that follows is answered
or silently dropped:

* the row exists at all -- no row, and the door answers 401 to a caller holding the credential;
* `outbound_secret_ref` says whether the channel can be pushed to. NULL is not "unfinished":
  it marks a pullable channel, whose answer is read back by task id at `GET /turns/<id>` (the
  rule the HTTPRoute beside the seed carries);
* `principal_allowlist` is who the channel recognises. A caller not named there normalises to
  an unknown principal, carries the untrusted taint, and is capped at authority T1 while
  `note` -- the one tool the answering lane calls -- is T2. The turn is then refused, and the
  door posts its designed answer to an unauthorised sender: nothing.

That last one is not hypothetical. Measured 2026-10-24 on the public door: `POST /webhook/http`
returned 202 with a task id, the pod logged `gateway.denied TIER_INSUFFICIENT`, the worker
logged `worker.no_reply`, and `GET /turns/<id>` was a 404 for two hours of retries. The row the
door was using existed in the database and in no file here -- it had been created by hand -- so
a re-provisioned cluster would have lost the channel entirely while the running one kept
working. This test is what would have caught that: it reads the seed the cluster is built from,
not the database a hand once wrote.

What is graded is the seed's own text, parsed into rows. A property that only holds in a
database nobody can re-create is not a property of the estate.
"""

import json
import os
import re

import pytest

yaml = pytest.importorskip("yaml")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEED = os.path.join(ROOT, "platform", "otto-gateway", "binding-seed.yaml")

# One INSERT tuple: the outer parentheses and anything inside them, including the one level
# of nesting `jsonb_build_object(...)` uses. Values are SQL literals, psql variables (`:'x'`)
# or the keyword NULL, so this is a shape match and not a SQL parser.
_TUPLE = re.compile(r"\n\s*(\((?:[^()]|\([^()]*\))*\))")
_CHANNEL = re.compile(r"^\(\s*'[^']*'\s*,\s*'([^']*)'")


def _seed_sql() -> str:
    with open(SEED, encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)
    return manifest["data"]["seed.sql"]


def _seeded_rows() -> list[dict[str, str]]:
    """The INSERT's own rows, as (channel, tuple text)."""
    sql = _seed_sql()
    assert "INSERT INTO channel_binding" in sql, (
        "the seed no longer inserts a binding row"
    )
    body = sql.split("INSERT INTO channel_binding", 1)[1].split("ON CONFLICT", 1)[0]
    rows = []
    for match in _TUPLE.finditer(body):
        text = match.group(1)
        channel = _CHANNEL.match(text)
        if channel is not None:
            rows.append({"channel": channel.group(1), "text": text})
    assert rows, "the INSERT's VALUES list did not parse into rows"
    return rows


def test_the_seed_still_builds_the_operator_chat():
    """The row the estate's own operator messages through is the one that must never go."""
    channels = {row["channel"] for row in _seeded_rows()}
    assert "telegram" in channels, (
        "the seed no longer creates the operator's telegram binding; a fresh cluster would "
        "answer 401 to the founder"
    )


def test_the_public_api_door_is_in_the_seed_and_not_only_in_the_database():
    """`http` is a channel the door serves, so it is a channel the seed must create.

    It is the one that was missing: live in `channel_binding`, absent from every file, so
    `POST https://otto.mumchimp.com/webhook/http` worked on this cluster and would 401 on the
    next one.
    """
    rows = _seeded_rows()
    http_rows = [row for row in rows if row["channel"] == "http"]
    assert http_rows, (
        "the seed creates no `http` binding row; the public door's channel exists only as a "
        "hand-written row in one cluster"
    )


def test_an_api_row_is_pullable_rather_than_pushable():
    """NULL outbound reference is what makes the channel pullable, not what makes it broken.

    A channel with no address to push to is answered and recorded; the caller reads the answer
    by task id. The other shape -- an outbound reference to a vault path that does not exist --
    fails at delivery time, one turn later, where nobody is watching.
    """
    http = [row for row in _seeded_rows() if row["channel"] == "http"]
    assert http, "no `http` row to grade"
    for row in http:
        fields = row["text"]
        assert re.search(r",\s*NULL\s*,", fields), (
            f"the http binding row is not pullable: {fields}"
        )
        assert "vault://" not in fields.split("NULL")[-1], (
            f"the pullable http row names an outbound address anyway: {fields}"
        )


def test_a_seeded_caller_is_named_and_so_can_be_answered():
    """Every seeded channel names at least one principal, or it can only ever refuse.

    An empty allow-list is not a neutral default on a seeded channel: it caps every caller at
    T1, `note` is T2, and the door accepts the task and posts silence. That is the exact
    failure this test exists to prevent, so it is graded on the seed's rows rather than on one
    channel's.
    """
    for row in _seeded_rows():
        allowlist = re.search(r"jsonb_build_object\((.*)\)", row["text"], re.DOTALL)
        assert allowlist is not None, (
            f"the {row['channel']} row carries no principal allow-list at all: {row['text']}"
        )
        entries = [
            part.strip() for part in allowlist.group(1).split(",") if part.strip()
        ]
        assert entries, (
            f"the {row['channel']} row's allow-list is empty, so every caller is untrusted "
            f"and the turn is refused: {row['text']}"
        )


def test_the_api_door_presents_the_same_credential_the_operator_chat_does():
    """One tenant, one secret: the row the API door checks is the row the operator chat uses.

    Both fingerprints come from the same mounted file in the seed container and both rows name
    the same vault entry, so this is a property of the file, not of a deployment. If the two
    ever diverge, one of the doors answers 401 to a caller the other one accepts.
    """
    rows = _seeded_rows()
    operator = next(
        row["text"]
        for row in rows
        if row["channel"] == "telegram"
        and "vault://otto-staging-telegram/webhook_secret" in row["text"]
    )
    api = next(row["text"] for row in rows if row["channel"] == "http")
    assert "vault://otto-staging-telegram/webhook_secret" in api, (
        "the api door's binding row no longer names the operator's vault entry; the seed "
        "container computes its fingerprint from the same file"
    )
    assert ":'fingerprint'" in operator and ":'fingerprint'" in api, (
        "the operator chat and the api door must key the same computed fingerprint"
    )


def test_the_rows_are_ordered_so_the_insert_is_idempotent():
    """`ON CONFLICT (channel, external_id)` is what lets every replica run this on a roll.

    It only converges if the conflict target is in the seed's own key and the update sets the
    fields an operator could have changed by hand -- the allow-list especially, since that is
    the one whose absence is silent.
    """
    sql = _seed_sql()
    assert "ON CONFLICT (channel, external_id) DO UPDATE" in sql
    for field in (
        "token_fingerprint",
        "status",
        "outbound_secret_ref",
        "principal_allowlist",
    ):
        assert re.search(rf"^\s*{field} = excluded\.{field}", sql, re.MULTILINE), (
            f"the seed does not converge {field} on a re-run"
        )


def test_the_manifest_is_still_a_configmap_the_deployment_mounts():
    """A row nobody mounts is a comment."""
    with open(SEED, encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)
    assert manifest["kind"] == "ConfigMap"
    assert manifest["metadata"]["name"] == "otto-gateway-binding-seed"
    assert json.dumps(manifest["data"])  # seed.sql is text, and stays text
