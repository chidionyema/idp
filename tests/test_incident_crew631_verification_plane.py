"""crew#631: on 2026-08-29 agents reported Langfuse done while nobody could sign in for eight hours
(crew#626). Self-certification ends here: a verdict is signed by a key the agent does not hold, bound
to the running image, expires, and each probe is proved able to FAIL against a target with auth off."""

import json
import os
import subprocess
import sys
import time

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
IDP = os.path.dirname(HERE)
sys.path.insert(0, IDP)
from probes import langfuse as LF  # noqa: E402
from probes import verdict as V  # noqa: E402

KEY = "test-key-only"
OK_ASSERTIONS = [V.assertion("x", 1, 1, True)]


def _verdict(**kw):
    args = dict(
        check_id="c",
        target="t",
        commit_sha="s",
        artifact_digest="sha256:abc",
        config_revision="1",
        assertions=OK_ASSERTIONS,
    )
    args.update(kw)
    return V.sign(V.build(**args), KEY)


def test_signed_verdict_passes_and_one_changed_byte_is_unverified():
    v = _verdict()
    assert V.grade(v, KEY) == ("PASS", "all assertions ok")
    v2 = dict(v, artifact_digest="sha256:abd")
    assert V.grade(v2, KEY)[0] == "UNVERIFIED"
    assert V.grade(dict(v, sig=""), KEY)[0] == "UNVERIFIED"
    assert (
        V.grade(
            V.sign(
                V.build(
                    check_id="c",
                    target="t",
                    commit_sha="s",
                    artifact_digest="sha256:abc",
                    config_revision="1",
                    assertions=OK_ASSERTIONS,
                ),
                "other-key",
            ),
            KEY,
        )[0]
        == "UNVERIFIED"
    )


def test_expired_or_other_digest_or_no_digest_is_never_pass():
    v = _verdict(ttl_seconds=10)
    assert V.grade(v, KEY, now=time.time() + 11)[0] == "UNVERIFIED"
    assert (
        V.grade(v, KEY, artifact_digest="sha256:running-something-else")[0]
        == "UNVERIFIED"
    )
    assert V.grade(_verdict(artifact_digest=""), KEY)[0] == "UNVERIFIED"


def test_blocked_target_is_blocked_whatever_the_assertions_say():
    v = _verdict(blocked="cluster unreadable")
    assert v["outcome"] == "BLOCKED"
    assert V.grade(v, KEY)[0] == "BLOCKED"
    assert (
        V.grade(_verdict(assertions=[V.assertion("x", 1, 2, False)]), KEY)[0] == "FAIL"
    )


def _fake(mode):
    """A Langfuse that is `closed` (correct) or `open` (auth not enforced)."""

    def get(url, auth=None, timeout=0):
        if "/api/public/health" in url:
            return 200, '{"status":"OK"}'
        if "/api/public/projects" in url:
            if auth == ("pk", "sk") or mode == "open":
                return 200, '{"data":[{"id":"p1","name":"estate"}]}'
            return 401, '{"message":"Unauthorized"}'
        return 404, ""

    return get


def test_l2_is_green_on_a_closed_api_and_red_when_no_key_is_accepted():
    closed = LF.l2_machine("https://lf", "pk", "sk", get=_fake("closed"))
    assert all(a["ok"] for a in closed), closed
    opened = LF.l2_machine("https://lf", "pk", "sk", get=_fake("open"))
    assert [a["name"] for a in opened if not a["ok"]] == [
        "l2.NEGATIVE.no_key_is_refused"
    ]


def test_l1_and_l2_carry_no_layout_words_and_l3_grades_identity_not_a_cookie():
    src = open(os.path.join(IDP, "probes", "langfuse.py")).read()
    for word in (
        "getByTestId",
        "data-testid",
        "querySelector",
        "locator(",
        "css=",
        "xpath",
    ):
        assert word not in src, word
    good = LF.l3_from_sessions(
        {"user": {"email": "Estate-Drill@zone"}}, None, "estate-drill@zone"
    )
    assert all(a["ok"] for a in good), good
    wrong_user = LF.l3_from_sessions(
        {"user": {"email": "someone@else"}}, None, "estate-drill@zone"
    )
    assert not wrong_user[0]["ok"] and wrong_user[1]["ok"]
    session_exists_but_nobody = LF.l3_from_sessions(
        {"user": {}}, None, "estate-drill@zone"
    )
    assert not session_exists_but_nobody[0]["ok"]
    gate_open = LF.l3_from_sessions(
        {"user": {"email": "estate-drill@zone"}},
        {"user": {"email": "estate-drill@zone"}},
        "estate-drill@zone",
    )
    assert not gate_open[1]["ok"], "a cold context with a user must be red"


def test_every_level_has_a_negative_control_or_identity_pair():
    names = [a["name"] for a in LF.l2_machine("h", "pk", "sk", get=_fake("closed"))]
    assert any("NEGATIVE" in n for n in names)
    names = [a["name"] for a in LF.l3_from_sessions({}, None, "x")]
    assert any("NEGATIVE" in n for n in names) and any("identity" in n for n in names)


def test_the_drill_grades_the_langfuse_session_with_the_same_probe():
    src = open(os.path.join(IDP, "bin", "idp-login-drill")).read()
    assert "from probes.langfuse import l3_from_sessions" in src
    assert 'export IDP_ROOT="$IDP"' in src
    assert "DRILL_ASSERTIONS_OUT" in src
    assert "the gate is open" in src, (
        "an open gate must be red in the drill, not advisory"
    )


def test_the_prover_runs_on_the_machine_identity_and_posts_a_check_run():
    wf = yaml.safe_load(
        open(os.path.join(IDP, ".github", "workflows", "verdict-langfuse.yml"))
    )
    assert (
        wf["permissions"]["checks"] == "write"
        and wf["permissions"]["id-token"] == "write"
    )
    text = open(
        os.path.join(IDP, ".github", "workflows", "verdict-langfuse.yml")
    ).read()
    assert (
        "bin/idp-prove langfuse" in text
        and "check-runs" in text
        and "verify/langfuse" in text
    )
    assert "oci-token-exchange-action" in text, (
        "the prover's credentials come from the OIDC exchange, never a stored secret"
    )
    cat = yaml.safe_load(open(os.path.join(IDP, "drills", "catalogue.yaml")))
    row = [d for d in cat["drills"] if d["name"] == "verdict-langfuse"]
    assert row and row[0]["schedule"] == wf[True]["schedule"][0]["cron"]
    tf = open(os.path.join(IDP, "platform", "oci", "identity", "main.tf")).read()
    assert 'secret_name    = "verdict-hmac-key"' in tf


def test_idp_verdict_cli_signs_and_verifies_a_file(tmp_path):
    p = tmp_path / "v.json"
    p.write_text(
        json.dumps(
            V.build(
                check_id="c",
                target="t",
                commit_sha="s",
                artifact_digest="sha256:abc",
                config_revision="1",
                assertions=OK_ASSERTIONS,
            )
        )
    )
    env = dict(os.environ, VERDICT_HMAC_KEY=KEY)
    tool = os.path.join(IDP, "bin", "idp-verdict")
    assert (
        subprocess.run(
            [tool, "sign", str(p)], env=env, capture_output=True, text=True
        ).returncode
        == 0
    )
    out = subprocess.run(
        [tool, "verify", str(p)], env=env, capture_output=True, text=True
    )
    assert out.returncode == 0 and out.stdout.startswith("ok      verdict"), out.stdout
    doc = json.loads(p.read_text())
    doc["outcome"] = "PASS"
    doc["assertions"] = []
    p.write_text(json.dumps(doc))
    out = subprocess.run(
        [tool, "verify", str(p)], env=env, capture_output=True, text=True
    )
    assert out.returncode == 1 and "signature" in out.stdout
    out = subprocess.run(
        [tool, "verify", str(p), "--digest", "x"],
        env=dict(os.environ, VERDICT_HMAC_KEY="", PATH="/nonexistent"),
        capture_output=True,
        text=True,
    )
    assert out.returncode != 0
