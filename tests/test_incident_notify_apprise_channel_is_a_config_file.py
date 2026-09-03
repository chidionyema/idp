"""Incident 2026-09-02: the notify kustomization reported True while every apprise pod
crash-looped, and the crash printed the founder alert channel's telegram token into the
pod log. Root: the manifest fed the mounted secret files through a shell export loop; the
file is named founder-telegram, a dash is illegal in a shell identifier, ``set -eu`` made
that fatal, and bash's error message carried the whole assignment, value included. The
exec line was dead too: the image has no ``apprise-api`` binary (its CMD is
supervisord-startup). The fix removes every shell from the road: Apprise stateful
"simple" mode serves /notify/founder-telegram from founder-telegram.cfg inside
APPRISE_CONFIG_DIR, which is the secret mount itself.

This test pins the class."""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _apprise_pod_spec():
    docs = yaml.safe_load_all((ROOT / "platform/notify/apprise-api.yaml").read_text())
    dep = next(d for d in docs if d and d.get("kind") == "Deployment")
    return dep["spec"]["template"]["spec"]


def test_simple_mode_reads_exactly_the_secret_mount():
    container = _apprise_pod_spec()["containers"][0]
    env = {e["name"]: e.get("value") for e in container.get("env", [])}
    assert env.get("APPRISE_STATEFUL_MODE") == "simple", env
    mounts = {m["name"]: m["mountPath"] for m in container["volumeMounts"]}
    assert env.get("APPRISE_CONFIG_DIR") == mounts["channels"], (env, mounts)


# Ratchet, not amnesty: these three predate the incident and their secret keys happen to be
# valid identifiers today, so they run -- but each is one dash-named key away from the same
# crash-and-leak and is queued for the same files-not-environment rework. A NEW instance of
# the pattern is refused outright.
KNOWN_EXPORT_LOOPS = frozenset(
    {
        "platform/llm/litellm.yaml",
        "platform/healthchecks/healthchecks.yaml",
        "platform/guacamole/guacamole.yaml",
    }
)


def test_no_new_manifest_exports_secret_files_through_a_shell():
    offenders = [
        str(p.relative_to(ROOT))
        for p in (ROOT / "platform").rglob("*.yaml")
        if 'export "$(basename' in p.read_text()
    ]
    assert set(offenders) <= KNOWN_EXPORT_LOOPS, sorted(
        set(offenders) - KNOWN_EXPORT_LOOPS
    )
