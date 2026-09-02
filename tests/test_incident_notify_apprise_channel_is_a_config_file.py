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


def test_no_shell_sits_between_the_secret_and_apprise():
    container = _apprise_pod_spec()["containers"][0]
    assert "command" not in container and "args" not in container, (
        "the apprise container must run the image's own entrypoint: a shell that expands "
        "mounted secret files can print their values into the pod log, and did on 2026-09-02"
    )


def test_simple_mode_reads_exactly_the_secret_mount():
    container = _apprise_pod_spec()["containers"][0]
    env = {e["name"]: e.get("value") for e in container.get("env", [])}
    assert env.get("APPRISE_STATEFUL_MODE") == "simple", env
    mounts = {m["name"]: m["mountPath"] for m in container["volumeMounts"]}
    assert env.get("APPRISE_CONFIG_DIR") == mounts["channels"], (env, mounts)


def test_channel_key_is_the_cfg_file_simple_mode_serves():
    docs = yaml.safe_load_all(
        (ROOT / "platform/notify/external-secret.yaml").read_text()
    )
    es = next(d for d in docs if d)
    data = es["spec"]["target"]["template"]["data"]
    assert list(data) == ["founder-telegram.cfg"], (
        "simple mode serves /notify/<name> from <name>.cfg; a key without .cfg is a "
        "channel apprise cannot find, and a dash-named env var was the 2026-09-02 crash"
    )
    assert data["founder-telegram.cfg"].startswith("tgram://"), (
        "no store holds a half-URL"
    )


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
