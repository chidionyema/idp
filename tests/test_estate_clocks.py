"""The estate's clock view: it must survive its own tree, and it must be fast.

2026-10-28, measured on this machine: `bin/estate-clocks` died on
`platform/vendors/templates/externalsecrets.yaml` -- a TEMPLATE holding ${...}
placeholders, which is not YAML -- and every clock in the estate went down with it.
A view that cannot survive one unreadable file is a view that cannot show the dead
scheduler, which is the one thing it exists to show.

It was also slow: the view read 753 platform manifests and took 65.8s. A view nobody
waits for is a view nobody reads, so the loader (libyaml when the machine has it),
the token pre-filter and the cached kustomization lookup are part of the fix, and
this file is the proof that they stay.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CLOCKS = REPO / "bin" / "estate-clocks"


def load_clocks():
    spec = importlib.util.spec_from_loader(
        "estate_clocks",
        importlib.machinery.SourceFileLoader("estate_clocks", str(CLOCKS)),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_clock_view_survives_a_manifest_that_is_not_yaml(tmp_path, capsys):
    """A template with placeholders is not YAML. It is reported, and it is skipped.

    The file that broke the view for real (2026-10-28) is a HELM template, and it
    carries no clock. The pre-filter skips it before it is ever parsed. This case is
    the one the pre-filter cannot save: a file that names a clock and is still not
    YAML. It must be named and skipped, and the other clocks must still be listed.
    """
    module = load_clocks()
    platform = tmp_path / "platform" / "vendors" / "templates"
    platform.mkdir(parents=True)
    (platform / "externalsecrets.yaml").write_text(
        "{{- if .Values.enable }}\n"
        "kind: CronJob\n"
        "metadata:\n"
        "  name: {{ .Values.name }}\n"
        "{{- end }}\n"
    )
    cronjob = tmp_path / "platform" / "estate" / "cronjob.yaml"
    cronjob.parent.mkdir(parents=True)
    cronjob.write_text(
        "apiVersion: batch/v1\n"
        "kind: CronJob\n"
        "metadata:\n"
        "  name: estate-example\n"
        "  namespace: estate\n"
        "spec:\n"
        "  schedule: '*/5 * * * *'\n"
    )
    (tmp_path / ".github" / "workflows").mkdir(parents=True)

    clocks = module._read_cronjobs(tmp_path)
    assert [c["clock"] for c in clocks] == ["estate-example"], clocks
    assert clocks[0]["where"] == "cluster - estate"
    err = capsys.readouterr().err
    assert "externalsecrets.yaml" in err, err
    assert "not readable YAML" in err, err


def test_the_clock_view_renders_only_ascii(tmp_path):
    """The rendered page must hold no byte above 127, or the push gate refuses it.

    Measured 2026-11-28, run 46177326054: `.githooks/pre-push` Layer 1c refused the
    regenerated page with "non-ASCII bytes added in docs/scheduling/CLOCKS.md". The
    generator wrote U+00B7 and U+2026 itself, and a manifest description carries
    whatever prose a human wrote in it: a section sign, an em dash, a curly quote.

    So the generator emits ASCII: the strings it builds say " - " and "...", and
    everything a manifest contributes is folded to ASCII as the last step of render().
    This is the falsifier for that.
    """
    module = load_clocks()
    platform = tmp_path / "platform" / "estate"
    platform.mkdir(parents=True)
    # The description of this clock holds a middle dot, an ellipsis, a section sign,
    # an em dash and curly quotes. The escapes keep this file ASCII too.
    (platform / "cronjob.yaml").write_text(
        "# Runs the \u00b7 thing \u2026 with \u00a7 and \u2014 and \u2018quotes\u2019\n"
        "apiVersion: batch/v1\n"
        "kind: CronJob\n"
        "metadata:\n"
        "  name: estate-example\n"
        "  namespace: estate\n"
        "spec:\n"
        "  schedule: '*/5 * * * *'\n"
    )
    (tmp_path / ".github" / "workflows").mkdir(parents=True)

    out = module.render(tmp_path)

    assert "estate-example" in out, out
    raw = out.encode("utf-8")
    bad = [i for i, byte in enumerate(raw) if byte > 127]
    assert not bad, "the rendered page holds non-ASCII bytes at offsets {}".format(
        bad[:5]
    )
    assert all(byte < 128 for byte in raw), "the rendered page holds a byte above 127"


def test_the_clock_view_lists_every_clock_in_the_estate():
    """The view is the estate's clocks: it must render the tree it lives in."""
    import time

    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, str(CLOCKS), "--stdout"],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    elapsed = time.monotonic() - started
    assert result.returncode == 0, result.stdout + result.stderr
    assert "com.estate.registry-reconcile" in result.stdout, result.stdout[:2000]
    assert "clocks:" in result.stdout
    # Measured 2026-10-28: 65.8s before the loader, the pre-filter and the cached
    # lookup; 1.1s after. A view nobody waits for is a view nobody reads, and this
    # bound is 20x the new cost and 3x under the old one.
    assert elapsed < 20.0, "the clock view took {:.1f}s".format(elapsed)


def test_the_committed_clocks_page_is_current():
    """The page is generated, and a stale page must fail the suite.

    The page used to name a test that did not exist
    (tests/test_clocks_table_matches_sources.py), so the promise it made was a gate that
    could not fire. This is the gate.
    """
    module = load_clocks()
    fresh = module.render(REPO)
    committed = (REPO / "docs" / "scheduling" / "CLOCKS.md").read_text()
    assert committed == fresh, (
        "docs/scheduling/CLOCKS.md is stale: run bin/estate-clocks"
    )


def test_the_clock_view_does_not_reparse_the_same_manifest_for_every_file(monkeypatch):
    """753 platform manifests, and the view parsed each of them.

    Measured 2026-10-28: the view took 65.8s because it re-parsed the same
    kustomization.yaml once per file, on top of parsing all 753 files. The token
    pre-filter and the cached lookup are the fix; this is the proof that they stay.
    """
    module = load_clocks()
    calls = {"n": 0}
    real_load = yaml.load
    real_load_all = yaml.load_all

    def counting_load(*args, **kwargs):
        calls["n"] += 1
        return real_load(*args, **kwargs)

    def counting_load_all(*args, **kwargs):
        calls["n"] += 1
        return real_load_all(*args, **kwargs)

    monkeypatch.setattr(module.yaml, "load", counting_load)
    monkeypatch.setattr(module.yaml, "load_all", counting_load_all)

    out = module.render(REPO)
    assert "clocks:" in out
    platform_files = sum(1 for _ in (REPO / "platform").rglob("*.yaml"))
    assert platform_files > 500, "the tree this guards is the tree we think it is"
    assert calls["n"] < platform_files / 4, (
        "the clock view parsed {} manifests for {} platform files".format(
            calls["n"], platform_files
        )
    )
