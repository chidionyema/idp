# ruff: noqa: S101
"""The GGUF export must never depend on a terminal.

Run 34401515600 (2026-09-09) trained ci-flake-triage, passed both gates -- held-out agreement
0.9773 against a 0.95 floor, abstain 0.175 against a 0.20 ceiling -- and published nothing,
because unsloth's save_pretrained_gguf builds llama.cpp during the run and asks the terminal to
approve an apt-get first. On a headless GPU container that read EOF:
"RuntimeError: Unsloth: GGUF conversion failed: EOF when reading a line". The GPU was billed and
the model was lost. These two tests are the guard.
"""

import ast
import importlib
import sys
import types
from pathlib import Path

import pytest

FORGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FORGE))


NEEDED = {"torch": "no_grad", "datasets": "load_dataset"}


def _train_module():
    """train.py without a GPU.

    torch and datasets are stubbed unless the real ones are importable AND carry the name
    train.py imports. `sys.path` holds forge/, which contains a datasets/ directory of JSONL
    files, so a bare `import datasets` can resolve to that folder and pass an import check while
    having no load_dataset at all.
    """
    for name, attr in NEEDED.items():
        try:
            if hasattr(importlib.import_module(name), attr):
                continue
        except ImportError:
            pass
        mod = types.ModuleType(name)
        setattr(mod, attr, lambda *a, **k: None)
        sys.modules[name] = mod
    return importlib.import_module("train")


class FakeModel:
    def __init__(self):
        self.merged_to = None

    def save_pretrained_merged(self, path, tokenizer, save_method):
        self.merged_to = (path, save_method)
        Path(path).mkdir(parents=True, exist_ok=True)


def test_export_gguf_converts_and_quantises_through_llama_cpp(tmp_path, monkeypatch):
    train = _train_module()
    calls = []

    def fake_run(argv, **kwargs):
        calls.append([str(a) for a in argv])
        if "--outfile" in argv:
            Path(argv[argv.index("--outfile") + 1]).write_bytes(b"f16")
        if argv[0].endswith("llama-quantize"):
            Path(argv[2]).write_bytes(b"q4")
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(train.subprocess, "run", fake_run)
    model = FakeModel()
    out = tmp_path / "artifact"
    out.mkdir()
    train.export_gguf(model, object(), str(out))

    assert model.merged_to[1] == "merged_16bit"
    convert, quantize = calls
    assert convert[1].endswith("convert_hf_to_gguf.py")
    assert convert[convert.index("--outtype") + 1] == "f16"
    assert quantize[0].endswith("llama-quantize")
    assert quantize[-1] == "Q4_K_M"
    # the artifact the Runtime pulls, and nothing else: no f16 intermediate, no merged weights
    assert (out / "model.gguf").exists()
    assert sorted(p.name for p in out.iterdir()) == ["model.gguf"]


def test_export_gguf_refuses_when_llama_cpp_fails(tmp_path, monkeypatch):
    """A converter that exits non-zero must raise, not leave a half-written model.gguf."""
    train = _train_module()

    def fake_run(argv, **kwargs):
        raise train.subprocess.CalledProcessError(1, argv)

    monkeypatch.setattr(train.subprocess, "run", fake_run)
    out = tmp_path / "artifact"
    out.mkdir()
    with pytest.raises(train.subprocess.CalledProcessError):
        train.export_gguf(FakeModel(), object(), str(out))
    assert not (out / "model.gguf").exists()


def test_no_call_builds_llama_cpp_during_the_run():
    """No exporter that installs its own toolchain mid-run may be called from train.py."""
    tree = ast.parse((FORGE / "train.py").read_text(encoding="utf-8"))
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "save_pretrained_gguf" not in called
