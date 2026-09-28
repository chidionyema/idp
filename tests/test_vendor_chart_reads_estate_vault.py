"""ExternalSecrets for browser-setup rows read estate-vault, not a human-pasted store.

crew#832: setup.road browser rows are keys the estate captures itself via setup.road/steps, so
the ExternalSecret can read estate-vault directly, property = field, the same shape as
platform/otto-golden-secret's otto-webhook. There is no PushSecret for these rows: the estate
writes the keys, so nothing is ever pushed.

helm is not optional here and its absence is a failure, not a skip -- a test that executes
nothing is not a test (~AGENTS.md).
"""

import pathlib
import shutil
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]

FAKE = {
    "kind": "secret",
    "page": "https://example.invalid/keys",
    "store_default": "estate-vault",
    "verify": {
        "method": "GET",
        "url": "https://example.invalid/v",
        "headers": {"Authorization": "Bearer {key}"},
    },
    "targets": [
        {"ns": "llm", "field": "FAKE_API_KEY"},
        {"ns": "llm", "field": "FAKE_ORG"},
        {"ns": "dagster", "field": "FAKE_API_KEY"},
    ],
    "setup": {
        "road": "browser",
        "entry": "fake-vendor-env",
        "steps": [
            {"goto": "https://example.invalid"},
            {"capture": {"field": "FAKE_API_KEY", "regex": "tok_[0-9a-f]{32}"}},
        ],
    },
}


def _render(chart_dir):
    helm = shutil.which("helm")
    assert helm, (
        "helm is not on PATH; this test grades the chart's rendered objects and cannot grade "
        "them without rendering. .github/actions/estate-tools installs it."
    )
    out = subprocess.run(
        [helm, "template", "vendor-bridge", str(chart_dir)],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, (
        f"helm template {chart_dir} failed:\n{out.stderr[-2000:]}"
    )
    return [d for d in yaml.safe_load_all(out.stdout) if d]


def _chart_with(tmp_path, rows: dict):
    chart_dir = tmp_path / "vendors"
    shutil.copytree(ROOT / "platform/vendors", chart_dir)
    reg = yaml.safe_load((chart_dir / "consoles.yaml").read_text())
    reg["vendors"].update(rows)
    (chart_dir / "consoles.yaml").write_text(yaml.safe_dump(reg, sort_keys=False))
    return chart_dir


def test_an_estate_vault_row_renders_from_estate_vault(tmp_path):
    chart_dir = _chart_with(tmp_path, {"fake_vendor": FAKE})
    docs = _render(chart_dir)

    es = [
        d
        for d in docs
        if d["kind"] == "ExternalSecret"
        and d["metadata"]["name"] == "vendor-fake-vendor"
    ]
    namespaces = sorted(d["metadata"]["namespace"] for d in es)
    assert namespaces == ["dagster", "llm"]

    by_ns = {d["metadata"]["namespace"]: d for d in es}
    for d in es:
        assert d["spec"]["secretStoreRef"] == {
            "kind": "ClusterSecretStore",
            "name": "estate-vault",
        }
        assert d["spec"]["refreshInterval"] == "10m"
        assert d["spec"]["target"]["name"] == "vendor-fake-vendor"

    assert by_ns["llm"]["spec"]["data"] == [
        {
            "secretKey": "FAKE_API_KEY",
            "remoteRef": {"key": "fake-vendor-env", "property": "FAKE_API_KEY"},
        },
        {
            "secretKey": "FAKE_ORG",
            "remoteRef": {"key": "fake-vendor-env", "property": "FAKE_ORG"},
        },
    ]

    others = [
        d
        for d in docs
        if not (
            d["kind"] == "ExternalSecret"
            and d["metadata"]["name"] == "vendor-fake-vendor"
        )
    ]
    for d in others:
        assert "fake" not in yaml.safe_dump(d), (
            f"{d['kind']} {d.get('metadata', {}).get('name')} mentions fake; there must be no "
            "PushSecret for an estate-vault row"
        )


def test_the_human_vault_objects_are_unchanged(tmp_path):
    base_docs = _render(ROOT / "platform/vendors")
    modified_docs = _render(_chart_with(tmp_path, {"fake_vendor": FAKE}))

    def without_vendor(docs):
        return [d for d in docs if not d["metadata"]["name"].startswith("vendor-")]

    assert without_vendor(modified_docs) == without_vendor(base_docs)


def test_oidc_and_assisted_estate_vault_rows_render_nothing(tmp_path):
    rows = {
        "fake_oidc": {
            "kind": "secret",
            "store_default": "estate-vault",
            "setup": {"road": "oidc"},
            "targets": [{"ns": "llm", "field": "X"}],
        },
        "fake_assisted": {
            "kind": "secret",
            "store_default": "estate-vault",
            "targets": [{"ns": "llm", "field": "X"}],
        },
    }
    chart_dir = _chart_with(tmp_path, rows)
    docs = _render(chart_dir)
    names = {d["metadata"]["name"] for d in docs}
    assert "vendor-fake-oidc" not in names
    assert "vendor-fake-assisted" not in names
