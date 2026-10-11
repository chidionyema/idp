"""The shadow bundle is the lever that turns 4m50s into ~30s (idp#5769, measured
on flux/image-updates 38145360914). The manifest is the contract; the export
and import are the two halves the workflow drives."""

from __future__ import annotations

import importlib.machinery
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_shadow_bundle():
    loader = importlib.machinery.SourceFileLoader(
        "idp_shadow_bundle", str(REPO / "bin" / "idp-shadow-bundle")
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_the_manifest_lists_every_image_the_run_needs(tmp_path):
    b = load_shadow_bundle()
    images = b.list_images()
    # k3s node image (the biggest single pull), all four flux controllers, the
    # DB stand-in's pinned image. These are the ones every run pulls today.
    assert any(img.endswith("rancher/k3s:v1.31.2-k3s1") for img in images), images
    for ctl in ("source-controller", "kustomize-controller", "helm-controller"):
        assert any(ctl in img and "ghcr.io/fluxcd/" in img for img in images), (
            ctl,
            images,
        )
    assert any("postgres-partman" in img for img in images), images
    # The manifest is comment-and-blank-tolerant.
    assert all(img and not img.startswith("#") for img in images)


def test_export_pulls_every_image_then_saves_them_all(monkeypatch, tmp_path):
    b = load_shadow_bundle()
    pulled: list[str] = []
    saved_with: list[list[str]] = []

    def fake_run(argv, check=True, **kw):
        if argv[:2] == ["docker", "pull"]:
            pulled.append(argv[2])
        elif argv[:2] == ["docker", "save"]:
            # docker save -o PATH img1 img2 ... is the layout the script uses.
            oi = argv.index("-o")
            saved_with.append(list(argv[oi + 2 :]))
            Path(argv[oi + 1]).write_bytes(b"tar")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(b.subprocess, "run", fake_run)
    tar = tmp_path / "out.tar"
    b.bundle_export(["a:1", "b:2"], tar)
    assert pulled == ["a:1", "b:2"]
    assert saved_with == [["a:1", "b:2"]]
    assert tar.read_bytes() == b"tar"


def test_import_loads_the_tar(monkeypatch, tmp_path):
    b = load_shadow_bundle()
    tar = tmp_path / "b.tar"
    tar.write_bytes(b"tar")
    calls = []

    def fake_run(argv, check=True, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(b.subprocess, "run", fake_run)
    b.bundle_import(tar)
    assert calls == [["docker", "load", "-i", str(tar)]]


def test_an_empty_manifest_refuses_to_export(monkeypatch, tmp_path):
    b = load_shadow_bundle()

    def fake_run(argv, check=True, **kw):
        raise AssertionError("no docker calls expected on an empty manifest")

    monkeypatch.setattr(b.subprocess, "run", fake_run)
    try:
        b.bundle_export([], tmp_path / "x.tar")
    except SystemExit as e:
        assert "no images" in str(e)
    else:
        raise AssertionError("empty manifest should refuse")
