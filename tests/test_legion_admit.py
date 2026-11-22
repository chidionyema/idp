"""Falsifiers for bin/legion-admit (idp#8283): every refusal happens BEFORE inference.

Each historical Legion failure is replayed against the real entrypoint in a disposable
git repository, and against a real local HTTP server standing in for a provider:

  #8061  seven files against MAX_FILES_PER_CHANGE=5, refused at submit after inference
  #8165  a patch to .github/workflows/greenlane.yml, refused at submit after inference
  #7838  Gemini 429 then MiniMax 429, discovered by the harness crashing
  (new)  a mission with no scope at all, which the submit lane could not bound

and the positive controls: an in-bounds mission is admitted, the scope envelope it writes
is the exact one the submit lane verifies (idp-agent-base-apply.py --scope-file), and a
patch outside the admitted scope is refused by that submit lane.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADMIT = ROOT / "bin/legion-admit"
APPLY = ROOT / "bin/idp-agent-base-apply.py"


def git(repo, *args, check=True):
    return subprocess.run(
        ["git", *args], cwd=repo, check=check, capture_output=True, text=True
    )


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    (r / "web").mkdir(parents=True)
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.name", "Agent-Test")
    git(r, "config", "user.email", "test@example.invalid")
    for i in range(8):
        (r / "web" / f"f{i}.txt").write_text(f"{i}\n")
    git(r, "add", ".")
    git(r, "commit", "-qm", "base")
    git(
        r,
        "update-ref",
        "refs/remotes/origin/main",
        git(r, "rev-parse", "HEAD").stdout.strip(),
    )
    return r


class _Provider(BaseHTTPRequestHandler):
    codes: dict = {}
    seen: list = []

    delay: dict = {}

    def do_POST(self):  # noqa: N802
        import time as _t

        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n))
        lane = self.path.split("/")[1]
        type(self).seen.append(
            (lane, body["model"], body["max_tokens"], self.headers["Authorization"])
        )
        code = type(self).codes.get(lane, 200)
        _t.sleep(type(self).delay.get(lane, 0))
        self.send_response(code)
        self.end_headers()
        self.wfile.write(
            b'{"choices":[]}' if code == 200 else b'{"error":"secret-detail"}'
        )

    def log_message(self, *a):
        pass


@pytest.fixture
def provider():
    _Provider.codes, _Provider.seen, _Provider.delay = {}, [], {}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Provider)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv, f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def admit(repo, out, mission, base_url=None, extra=(), **env_over):
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_OUTPUT",)}
    env.update({"TASK": mission, "GEMINI_API_KEY": "g-key", "MINIMAX_API_KEY": "m-key"})
    if base_url:
        env["LEGION_GOOGLE_BASE"] = base_url + "/google"
        env["LEGION_MINIMAX_BASE"] = base_url + "/minimax"
    env.update(env_over)
    return subprocess.run(
        [sys.executable, str(ADMIT), "--out", str(out), *extra],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def record(out):
    return json.loads((out / "admission.json").read_text())


# ---- scope: refused before inference -------------------------------------------------


def test_a_mission_with_no_scope_is_refused_before_inference(repo, tmp_path, provider):
    _, url = provider
    r = admit(repo, tmp_path / "o", "[LEGION] fix the contact page", url)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "SCOPE_UNDECLARED" in r.stdout
    assert record(tmp_path / "o")["decision"] == "REFUSED_SCOPE"
    assert _Provider.seen == [], (
        "a provider was called for a mission that could not be admitted"
    )


def test_8061_seven_files_are_refused_before_inference(repo, tmp_path, provider):
    _, url = provider
    files = ", ".join(f"web/f{i}.txt" for i in range(7))
    r = admit(repo, tmp_path / "o", f"Do it.\nScope: {files}\n", url)
    assert r.returncode == 2
    assert "7 files exceeds MAX_FILES_PER_CHANGE (5)" in r.stdout
    assert _Provider.seen == []


def test_8165_a_protected_path_is_refused_before_inference(repo, tmp_path, provider):
    _, url = provider
    r = admit(repo, tmp_path / "o", "Scope: .github/workflows/greenlane.yml", url)
    assert r.returncode == 2
    assert "protected paths" in r.stdout
    assert _Provider.seen == []


@pytest.mark.parametrize(
    "scope", ["web/*.txt", "web/f1.txt ../etc/passwd", "web/f1.txt, bin/x"]
)
def test_globs_traversal_and_cross_subsystem_scopes_are_refused(repo, tmp_path, scope):
    r = admit(repo, tmp_path / "o", f"Scope: {scope}", extra=("--skip-capacity",))
    assert r.returncode == 2, r.stdout


def test_two_different_scope_declarations_are_ambiguous(repo, tmp_path):
    r = admit(
        repo,
        tmp_path / "o",
        "Scope: web/f1.txt\nScope: web/f2.txt",
        extra=("--skip-capacity",),
    )
    assert r.returncode == 2 and "SCOPE_AMBIGUOUS" in r.stdout


def test_a_new_python_file_is_refused_before_inference_the_commit_hook_would_refuse_it(
    repo, tmp_path
):
    r = admit(
        repo, tmp_path / "o", "Scope: web/new_tool.py", extra=("--skip-capacity",)
    )
    assert r.returncode == 2 and "LANGUAGE_GATE" in r.stdout
    ok = admit(
        repo, tmp_path / "o2", "Scope: tests/test_new.py", extra=("--skip-capacity",)
    )
    assert ok.returncode == 0, ok.stdout


def test_a_dirty_admission_checkout_is_blind(repo, tmp_path):
    (repo / "web" / "f1.txt").write_text("tampered\n")
    r = admit(repo, tmp_path / "o", "Scope: web/f1.txt", extra=("--skip-capacity",))
    assert r.returncode == 2 and "not clean" in r.stdout


# ---- capacity: refused before inference, in seconds -----------------------------------


def test_7838_both_providers_429_is_refused_before_inference(repo, tmp_path, provider):
    _, url = provider
    _Provider.codes = {"google": 429, "minimax": 429}
    r = admit(
        repo,
        tmp_path / "o",
        "Scope: web/f1.txt",
        url,
        LEGION_FAILOVER="1",
        HARNESS="gemini",
    )
    assert r.returncode == 75, r.stdout
    assert (
        "CAPACITY_EXHAUSTED" in r.stdout
        and "google=rate-limited" in r.stdout
        and "minimax=rate-limited" in r.stdout
    )
    assert "secret-detail" not in r.stdout + r.stderr, (
        "the provider body reached the public log"
    )
    rec = record(tmp_path / "o")
    assert rec["decision"] == "REFUSED_CAPACITY" and "provider" not in rec
    assert [s[2] for s in _Provider.seen] == [1, 1], "probes must be 1-token requests"


def test_gemini_429_selects_minimax_when_failover_is_allowed(repo, tmp_path, provider):
    _, url = provider
    _Provider.codes = {"google": 429}
    r = admit(
        repo,
        tmp_path / "o",
        "Scope: web/f1.txt",
        url,
        LEGION_FAILOVER="1",
        HARNESS="gemini",
    )
    assert r.returncode == 0, r.stdout
    assert record(tmp_path / "o")["provider"] == "minimax"


def test_no_failover_means_no_second_provider(repo, tmp_path, provider):
    _, url = provider
    _Provider.codes = {"google": 429}
    r = admit(
        repo,
        tmp_path / "o",
        "Scope: web/f1.txt",
        url,
        LEGION_FAILOVER="0",
        HARNESS="gemini",
    )
    assert r.returncode == 75
    assert [s[0] for s in _Provider.seen] == ["google"]


def test_an_unreachable_provider_is_transport_not_capacity(repo, tmp_path):
    r = admit(
        repo,
        tmp_path / "o",
        "Scope: web/f1.txt",
        "http://127.0.0.1:9",
        HARNESS="gemini",
        LEGION_FAILOVER="0",
    )
    assert r.returncode == 75 and "google=transport" in r.stdout


def test_a_missing_key_is_not_reported_as_capacity(repo, tmp_path, provider):
    _, url = provider
    r = admit(
        repo,
        tmp_path / "o",
        "Scope: web/f1.txt",
        url,
        HARNESS="gemini",
        LEGION_FAILOVER="0",
        GEMINI_API_KEY="",
    )
    assert r.returncode == 75 and "google=no-key" in r.stdout
    assert _Provider.seen == []


def test_the_key_never_reaches_stdout(repo, tmp_path, provider):
    _, url = provider
    r = admit(
        repo,
        tmp_path / "o",
        "Scope: web/f1.txt",
        url,
        HARNESS="gemini",
        GEMINI_API_KEY="SUPERSECRET-123",
    )
    assert r.returncode == 0
    assert (
        "SUPERSECRET"
        not in r.stdout + r.stderr + (tmp_path / "o" / "admission.json").read_text()
    )
    assert _Provider.seen[0][3] == "Bearer SUPERSECRET-123"


# ---- positive control and end-to-end binding with the submit lane ----------------------


def test_admitted_scope_is_the_one_the_submit_lane_enforces(repo, tmp_path, provider):
    _, url = provider
    out = tmp_path / "o"
    r = admit(
        repo,
        out,
        "Fix it.\n**Scope:** `web/f1.txt`, `web/f2.txt`\n",
        url,
        HARNESS="gemini",
    )
    assert r.returncode == 0, r.stdout + r.stderr
    raw = (out / "scope.json").read_bytes()
    digest = (out / "scope.sha256").read_text().strip()
    assert hashlib.sha256(raw).hexdigest() == digest
    env = json.loads(raw)
    assert env["paths"] == ["web/f1.txt", "web/f2.txt"]
    assert "web/f1.txt" in (out / "contract.txt").read_text()
    base = env["base"]
    (tmp_path / "base").write_text(base + "\n")

    def submit(changes):
        for name in changes:
            (repo / name).write_text("agent\n")
        (tmp_path / "patch").write_text(git(repo, "diff", "--binary").stdout)
        git(repo, "checkout", "--", ".")
        res = subprocess.run(
            [
                sys.executable,
                str(APPLY),
                "--base-file",
                str(tmp_path / "base"),
                "--patch",
                str(tmp_path / "patch"),
                "--scope-file",
                str(out / "scope.json"),
                "--scope-sha256",
                digest,
            ],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        git(repo, "reset", "-q", "--hard")
        git(repo, "checkout", "-q", "main")
        return res

    ok = submit(["web/f1.txt"])
    assert ok.returncode == 0, ok.stderr
    assert json.loads(ok.stdout)["changed_files"] == ["web/f1.txt"]
    bad = submit(["web/f1.txt", "web/f5.txt"])
    assert bad.returncode == 2 and "exceeds admitted scope" in bad.stderr


def test_github_output_carries_the_trusted_digest(repo, tmp_path, provider):
    _, url = provider
    gh = tmp_path / "gh_out"
    r = admit(
        repo,
        tmp_path / "o",
        "Scope: web/f1.txt",
        url,
        HARNESS="gemini",
        GITHUB_OUTPUT=str(gh),
    )
    assert r.returncode == 0
    lines = dict(l.split("=", 1) for l in gh.read_text().splitlines())
    assert (
        lines["scope_sha256"] == (tmp_path / "o" / "scope.sha256").read_text().strip()
    )
    assert (
        hashlib.sha256(lines["scope_json"].encode()).hexdigest()
        == lines["scope_sha256"]
    )
    assert lines["provider"] == "google"


# ---- resilience: every way a provider can misbehave ends in a bounded, named verdict -------


def test_a_hanging_provider_is_cut_at_the_probe_timeout_and_the_next_lane_is_tried(
    repo, tmp_path, provider
):
    import time

    _, url = provider
    _Provider.delay = {"google": 5}
    t0 = time.monotonic()
    r = admit(
        repo,
        tmp_path / "o",
        "Scope: web/f1.txt",
        url,
        HARNESS="gemini",
        LEGION_FAILOVER="1",
        LEGION_PROBE_TIMEOUT_S="1",
    )
    assert time.monotonic() - t0 < 4, "the probe waited past its bound"
    assert r.returncode == 0, r.stdout
    rec = record(tmp_path / "o")
    assert rec["probes"][0]["verdict"] == "transport" and rec["provider"] == "minimax"


@pytest.mark.parametrize(
    ("code", "verdict"),
    [
        (500, "unavailable"),
        (503, "unavailable"),
        (401, "authentication"),
        (403, "authentication"),
        (404, "model-unavailable"),
        (418, "http-418"),
    ],
)
def test_every_non_200_is_refused_with_its_own_class(
    repo, tmp_path, provider, code, verdict
):
    _, url = provider
    _Provider.codes = {"google": code}
    r = admit(
        repo,
        tmp_path / "o",
        "Scope: web/f1.txt",
        url,
        HARNESS="gemini",
        LEGION_FAILOVER="0",
    )
    assert r.returncode == 75 and f"google={verdict}" in r.stdout
    assert record(tmp_path / "o")["decision"] == "REFUSED_CAPACITY"


def test_the_refusal_record_is_left_for_the_sealed_debug_pack(repo, tmp_path):
    """A refused run still leaves admission.json: the evidence the encrypt step seals."""
    r = admit(repo, tmp_path / "o", "no scope here", extra=("--skip-capacity",))
    assert r.returncode == 2
    rec = record(tmp_path / "o")
    assert rec["decision"] == "REFUSED_SCOPE" and "SCOPE_UNDECLARED" in rec["reason"]


def test_claude_native_needs_no_probe_it_proves_its_provider_itself(
    repo, tmp_path, provider
):
    _, url = provider
    r = admit(repo, tmp_path / "o", "Scope: web/f1.txt", url, HARNESS="claude-code")
    assert r.returncode == 0 and _Provider.seen == []


# A new provider is data, not another branch in the scheduler.
def _auto_module():
    import importlib.util
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader("legion_auto_test", str(ADMIT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _registry(path, provider, cls="free", price=0, models=("capable", "backup")):
    path.mkdir(exist_ok=True)
    header = (
        f'id="{provider}"\ndialect="openai"\n'
        f'base_url="https://{provider}.example"\n'
        'request_path="/v1/chat/completions"\n[auth]\nkind="bearer"\n'
        f'key_env="{provider.upper()}_API_KEY"\n'
    )
    rows = "".join(
        f'\n[[models]]\nid="{m}"\nclass="{cls}"\n'
        f"price_in_per_mtok={price}\nprice_out_per_mtok={price}\n"
        "context_window=131072\n"
        for m in models
    )
    (path / f"{provider}.toml").write_text(header + rows)


def test_auto_excludes_unfunded_and_disabled(tmp_path):
    mod = _auto_module()
    _registry(tmp_path, "north")
    _registry(tmp_path, "south", "paid", 2)
    _registry(tmp_path, "west")
    env = {
        "NORTH_API_KEY": "n",
        "SOUTH_API_KEY": "s",
        "WEST_API_KEY": "w",
        "LEGION_DISABLED_PROVIDERS": "west",
    }
    routes = mod.auto_candidates(tmp_path, env)
    assert {r["provider"] for r in routes} == {"north"}
    assert routes[0]["base"] == "https://north.example/v1"
    env["LEGION_PAID_PROVIDERS"] = "south"  # stale flag is never spend authority
    assert {r["provider"] for r in mod.auto_candidates(tmp_path, env)} == {"north"}


def test_auto_rate_limit_skips_account_not_only_model(tmp_path):
    mod = _auto_module()
    _registry(tmp_path, "north")
    _registry(tmp_path, "south")
    env = {"NORTH_API_KEY": "n", "SOUTH_API_KEY": "s"}
    seen = []

    def probe(route, env):
        seen.append(route["provider"])
        return {
            "verdict": "rate-limited" if route["provider"] == "north" else "capacity"
        }

    selected, _ = mod.auto_select(mod.auto_candidates(tmp_path, env), env, probe)
    assert selected["provider"] == "south"
    assert seen == ["north", "south"]


def test_auto_new_provider_only_requires_registry(tmp_path):
    mod = _auto_module()
    _registry(tmp_path, "new")
    env = {"NEW_API_KEY": "n"}
    selected, _ = mod.auto_select(
        mod.auto_candidates(tmp_path, env), env, lambda r, e: {"verdict": "capacity"}
    )
    assert selected["provider"] == "new"


@pytest.mark.parametrize(
    "response,verdict",
    [
        (
            {
                "model": "backup",
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "legion_ready",
                                        "arguments": '{"ready":true}',
                                    }
                                }
                            ]
                        }
                    }
                ],
            },
            "capacity",
        ),
        (
            {"model": "other", "choices": [{"message": {"tool_calls": []}}]},
            "tool-or-model-unverified",
        ),
        ({"model": "backup", "choices": []}, "invalid-response"),
        (
            {"model": "backup", "choices": [{"message": {"content": "yes"}}]},
            "tool-or-model-unverified",
        ),
    ],
)
def test_auto_probe_requires_model_and_tool(tmp_path, response, verdict):
    from unittest import mock

    mod = _auto_module()
    _registry(tmp_path, "north")
    env = {"NORTH_API_KEY": "secret"}
    route = mod.auto_candidates(tmp_path, env)[0]
    with mock.patch("urllib.request.build_opener") as opener:
        reader = opener.return_value.open.return_value.__enter__.return_value
        reader.read.return_value = json.dumps(response).encode()
        assert mod.auto_probe(route, env)["verdict"] == verdict


def test_auto_launcher_binds_base_model_and_isolates_key(tmp_path):
    from unittest import mock

    mod = _auto_module()
    _registry(tmp_path, "north")
    env = {
        "NORTH_API_KEY": "n",
        "OTHER_API_KEY": "other",
        "ADMITTED_PROVIDER": "north",
        "ADMITTED_MODEL": "backup",
        "ADMITTED_KEY_ENV": "NORTH_API_KEY",
        "LEGION_SELECTED_KEY": "n",
        "RUNNER_TEMP": str(tmp_path),
        "PATH": "/usr/bin",
    }
    route = mod.auto_candidates(tmp_path, env)[0]
    record = {"decision": "ADMITTED", "route": route, "base": "exact"}
    with (
        mock.patch("subprocess.check_output", return_value="exact\n"),
        mock.patch("subprocess.run") as run,
    ):
        run.return_value.returncode = 0
        assert mod.auto_launch(tmp_path, record, "test", tmp_path, env) == 0
        assert run.call_args.kwargs["env"]["LEGION_SELECTED_KEY"] == "n"
        assert "OTHER_API_KEY" not in run.call_args.kwargs["env"]
        config = (tmp_path / "legion-pi/models.json").read_text()
        assert '"apiKey": "$LEGION_SELECTED_KEY"' in config
    with pytest.raises(ValueError, match="admission mismatch"):
        mod.auto_launch(
            tmp_path, record, "test", tmp_path, dict(env, ADMITTED_MODEL="fake")
        )


def test_an_exhausted_account_is_not_reprobed_on_the_next_run(tmp_path):
    # Founder, 2026-11-19 21:46 (#8283): run 44619180014 retried Gemini and MiniMax unchanged
    # after both had 429'd. The cooldown written by one run is read by the next.
    mod = _auto_module()
    _registry(tmp_path, "north")
    _registry(tmp_path, "south")
    env = {"NORTH_API_KEY": "n", "SOUTH_API_KEY": "s"}
    cool = tmp_path / "cooldown.json"
    seen = []

    def probe(route, env):
        seen.append(route["provider"])
        return {
            "verdict": "rate-limited" if route["provider"] == "north" else "capacity"
        }

    routes = mod.auto_candidates(tmp_path, env)
    first = mod.load_cooldown(cool, 1000.0)
    mod.auto_select(routes, env, probe, cooldown=first, now=1000.0)
    mod.save_cooldown(cool, first, 1000.0)
    assert seen == ["north", "south"]

    seen.clear()
    second = mod.load_cooldown(cool, 1060.0)
    selected, observed = mod.auto_select(
        routes, env, probe, cooldown=second, now=1060.0
    )
    assert seen == ["south"]
    assert selected["provider"] == "south"
    assert observed[0] == {
        "provider": "north",
        "model": routes[0]["model"],
        "verdict": "cooling",
        "until": 1000 + mod.COOLDOWN_S["rate-limited"],
    }


def test_a_cooldown_expires_and_the_account_is_probed_again(tmp_path):
    mod = _auto_module()
    _registry(tmp_path, "north")
    env = {"NORTH_API_KEY": "n"}
    cool = tmp_path / "cooldown.json"
    mod.save_cooldown(cool, {"north": 2000.0}, 1000.0)
    assert mod.load_cooldown(cool, 1999.0) == {"north": 2000.0}
    assert mod.load_cooldown(cool, 2000.0) == {}
    seen = []
    selected, _ = mod.auto_select(
        mod.auto_candidates(tmp_path, env),
        env,
        lambda r, e: seen.append(r["provider"]) or {"verdict": "capacity"},
        cooldown=mod.load_cooldown(cool, 2001.0),
        now=2001.0,
    )
    assert seen == ["north"] and selected["provider"] == "north"


def test_an_unreadable_cooldown_file_cools_nothing(tmp_path):
    mod = _auto_module()
    cool = tmp_path / "cooldown.json"
    cool.write_text("{not json")
    assert mod.load_cooldown(cool, 0.0) == {}
    cool.write_text('["north"]')
    assert mod.load_cooldown(cool, 0.0) == {}
    assert mod.load_cooldown(None, 0.0) == {}


def test_paid_catalogue_route_refused_before_network_even_with_old_allowlist(tmp_path):
    from unittest import mock

    mod = _auto_module()
    _registry(tmp_path, "south", "paid", 2)
    env = {"SOUTH_API_KEY": "present", "LEGION_PAID_PROVIDERS": "south"}
    assert mod.auto_candidates(tmp_path, env) == []
    stale = dict(provider="south", model="capable", price_in=2, price_out=2)
    stale["class"] = "paid"
    seen = []

    def illicit_probe(route, unused):
        seen.append(route)
        return {"verdict": "capacity"}

    selected, observations = mod.auto_select([stale], env, illicit_probe)
    assert selected is None and seen == []
    assert observations[0]["verdict"] == "cost-unverified"
    with mock.patch("urllib.request.build_opener") as opener:
        assert mod.auto_probe(stale, env)["verdict"] == "cost-unverified"
        opener.assert_not_called()


def test_unpriced_or_falsely_free_record_cannot_probe_or_launch(tmp_path):
    from unittest import mock

    mod = _auto_module()
    env = {"NORTH_API_KEY": "present"}
    forged = dict(provider="north", model="capable", price_in=0, price_out=1)
    forged["class"] = "free"
    selected, observations = mod.auto_select([forged], env)
    assert selected is None and observations[0]["verdict"] == "cost-unverified"
    with mock.patch("urllib.request.build_opener") as opener:
        assert mod.auto_probe(forged, env)["verdict"] == "cost-unverified"
        opener.assert_not_called()
    with pytest.raises(ValueError, match="COST_UNVERIFIED"):
        mod.auto_launch(
            tmp_path,
            {"decision": "ADMITTED", "route": forged},
            "task",
            tmp_path,
            env,
        )


def test_remote_legacy_model_probe_is_refused_before_network():
    from unittest import mock

    mod = _auto_module()
    env = {
        "GEMINI_API_KEY": "secret",
        "LEGION_GOOGLE_BASE": "https://vendor.example/v1",
    }
    with (
        mock.patch.dict(os.environ, env),
        mock.patch("urllib.request.urlopen") as remote,
    ):
        result = mod.probe("google", "gemini-test")
    assert result["verdict"] == "cost-unverified"
    remote.assert_not_called()
