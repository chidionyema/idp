"""crew#631 CP8: the mutation harness. A probe is trusted only if it FAILs against a broken
target. Each mutation below is a door with one thing wrong (auth off, the database down, an
accepted span that never lands, an identity that is nobody, a digest that is not the running
one); the probe under test must return at least one failed assertion against it, or it is
quarantined: a probe that cannot fail is theatre.

Graduation is the other half: a probe starts UNPROVEN and graduates on one real FAIL and one
real PASS seen in signed verdicts from the prover, so a probe that has only ever passed is
still marked as never having been exercised in the world.
"""

import json

from probes import langfuse as LF
from probes import verdict as V

TID = "b" * 32


def _door(mode):
    store = {}

    def http(url, auth=None, timeout=20, data=None):
        keyed = auth == ("pk", "sk")
        if url.endswith("/health?failIfDatabaseUnavailable=true"):
            if mode == "db_down":
                return 503, '{"status":"Database not available"}'
            if mode == "proxy_page":
                return 200, "<html>502 upstream</html>"
            return 200, '{"status":"OK","version":"3"}'
        if url.endswith("/api/public/otel/v1/traces"):
            if not keyed and mode != "auth_off":
                return 401, "{}"
            if mode != "ingest_drops":
                span = json.loads(data)["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
                store[span["traceId"]] = 1
            return 207, "{}"
        if "/api/public/traces/" in url:
            tid = url.rsplit("/", 1)[1]
            if keyed and tid in store:
                return 200, json.dumps({"id": tid})
            return 404, "{}"
        if url.endswith("/api/public/projects"):
            if keyed or mode == "auth_off":
                return 200, '{"data":[{"id":"p1"}]}'
            return 401, "{}"
        return 404, ""

    return http


def _clock():
    t = [0.0]
    return (lambda: t[0]), (lambda s: t.__setitem__(0, t[0] + s))


def _l4(mode):
    clock, sleep = _clock()
    return LF.l4_journey(
        "https://lf",
        "pk",
        "sk",
        TID,
        TID[:16],
        "m",
        http=_door(mode),
        sleep=sleep,
        clock=clock,
    )


# probe -> {mutation: callable returning the probe's assertions against that broken door}
MUTATIONS = {
    "l1_liveness": {
        "db_down": lambda: LF.l1_liveness("https://lf", get=_door("db_down")),
        "proxy_page": lambda: LF.l1_liveness("https://lf", get=_door("proxy_page")),
    },
    "l2_machine": {
        "auth_off": lambda: LF.l2_machine(
            "https://lf", "pk", "sk", get=_door("auth_off")
        ),
    },
    "l3_from_sessions": {
        "nobody": lambda: LF.l3_from_sessions({"user": {}}, None, "drill@zone"),
        "wrong_identity": lambda: LF.l3_from_sessions(
            {"user": {"email": "x@y"}}, None, "drill@zone"
        ),
        "auth_off": lambda: LF.l3_from_sessions(
            {"user": {"email": "drill@zone"}},
            {"user": {"email": "drill@zone"}},
            "drill@zone",
        ),
    },
    "l4_journey": {
        "ingest_drops": lambda: _l4("ingest_drops"),
        "auth_off": lambda: _l4("auth_off"),
    },
    "verdict_grade": {
        "wrong_digest": lambda: _grade_mutation("digest"),
        "tampered_byte": lambda: _grade_mutation("byte"),
    },
}


def _grade_mutation(kind):
    key = "mutation-key"
    v = V.sign(
        V.build(
            check_id="c",
            target="t",
            commit_sha="s",
            artifact_digest="sha256:running",
            config_revision="1",
            assertions=[V.assertion("x", 1, 1, True)],
        ),
        key,
    )
    if kind == "digest":
        outcome = V.grade(v, key, artifact_digest="sha256:other")[0]
    else:
        outcome = V.grade(dict(v, commit_sha="s2"), key)[0]
    # the "probe" here is grade() accepting the record; against a broken record it must not
    return [V.assertion(f"grade.{kind}.accepted", "PASS", outcome, outcome == "PASS")]


def run_mutations(mutations=MUTATIONS):
    """[(probe, mutation, failed)]: failed=True means the probe FAILed against the broken door,
    which is what we want. A row with failed=False is a quarantine."""
    rows = []
    for probe, muts in mutations.items():
        for name, fn in muts.items():
            out = fn()
            rows.append((probe, name, any(not a["ok"] for a in out)))
    return rows


def quarantine(rows):
    return sorted({p for p, _, failed in rows if not failed})


def graduation(verdicts):
    """verdicts: iterable of verdict dicts from the prover. Per assertion name: PROVEN when both a
    real FAIL and a real PASS have been seen; else UNPROVEN with what is missing."""
    seen = {}
    for v in verdicts:
        for a in v.get("assertions", []):
            s = seen.setdefault(a["name"], {"pass": 0, "fail": 0})
            s["pass" if a["ok"] else "fail"] += 1
    out = {}
    for name, s in sorted(seen.items()):
        if s["pass"] and s["fail"]:
            out[name] = ("PROVEN", f"{s['pass']} PASS, {s['fail']} FAIL")
        else:
            missing = "a real FAIL" if s["pass"] else "a real PASS"
            out[name] = (
                "UNPROVEN",
                f"{s['pass']} PASS, {s['fail']} FAIL; needs {missing}",
            )
    return out
