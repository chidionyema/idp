"""Every fleetview_backend module must import inside the fleetview-backend image, and /voice/voices
must answer there.

2026-09-29: the /fleet voice picker on OKE opened empty. Every /voice/* route answered 500 with
ModuleNotFoundError: voice_media.py imports jsonschema, voice_intents.py imports yaml, voice.py
imports certifi plus two repo files, and fleetview-backend.Dockerfile installed none of them.
test_fleetview_backend_image_entrypoint_starts.py stayed green because it only asks for /healthz,
and serve.py imports those modules lazily, inside the routes. Past those imports the voice list
would still have 500ed, because the image carried no `sovereign.voice`; on 2026-10-08 that same
absence 500ed every /voice/hear, so the image now copies the package's four stdlib-only files.

The first two tests read the Dockerfile's pip pins and COPY lines, and requires every module-level
import in the package (and in the repo files it copies) to be stdlib, installed by that pip line,
or copied in; the second extends that to imports inside functions, apart from a named OPTIONAL
set. It needs no Docker and no network, so it runs on every PR that touches the image or
the package. The third runs voice_media.voices() with sovereign unimportable, which is the
image's own situation.
"""

from __future__ import annotations

import ast
import asyncio
import re
import shlex
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "fleetview-backend.Dockerfile"
PKG = ROOT / "backstage" / "plugins" / "fleetview-backend" / "src" / "fleetview_backend"

# The top-level modules a pinned distribution puts on sys.path, where that is not simply its own
# name. Its dependencies are listed too, since pip installs them alongside.
PROVIDES = {
    "fastapi": {
        "fastapi",
        "starlette",
        "pydantic",
        "pydantic_core",
        "anyio",
        "typing_extensions",
    },
    "uvicorn": {"uvicorn", "click", "h11"},
    "nats-py": {"nats"},
    "jsonschema": {
        "jsonschema",
        "referencing",
        "attrs",
        "rpds",
        "jsonschema_specifications",
    },
    "pyyaml": {"yaml"},
    "httpx": {"httpx", "httpcore", "certifi", "idna", "sniffio", "anyio"},
}

# Imported only inside a function, behind an exception the caller handles, and deliberately not
# in the image: the local speech models (faster_whisper, kokoro_onnx, and numpy which only they
# need) cannot load in a 256Mi sidecar, so sovereign/voice/engine.py reaches them only on the local
# engine path and voice_media turns their absence into a 502 naming the engine -- the router does
# the speech on OKE. Kafka, Langfuse and OpenTelemetry are off on OKE; deploy_journeys.py stubs
# datasette's hookimpl when it is absent. Anything else imported in a function body must be
# installed like the rest.
OPTIONAL = {
    "sovereign",
    "faster_whisper",
    "kokoro_onnx",
    "numpy",
    "aiokafka",
    "langfuse",
    "opentelemetry",
    "datasette",
}


def _image() -> tuple[set[str], list[Path]]:
    """(importable third-party top-level names, repo .py files COPYd into the image)."""
    installed: set[str] = set()
    copied: list[Path] = []
    for line in DOCKERFILE.read_text().splitlines():
        if line.startswith("RUN ") and "pip install" in line:
            for tok in shlex.split(line.split("pip install", 1)[1]):
                if tok.startswith("-"):
                    continue
                dist = re.split(r"[=<>~\[]", tok, maxsplit=1)[0].lower()
                installed |= PROVIDES.get(dist, {dist.replace("-", "_")})
        elif line.startswith("COPY "):
            src = ROOT / line.split()[1]
            copied += sorted(src.rglob("*.py")) if src.is_dir() else [src]
    assert installed, "fleetview-backend.Dockerfile has no pip install line"
    return installed, copied


def _module_level_imports(path: Path) -> set[str]:
    """Top-level names imported when the module loads: the body, and `if` blocks in it, but not
    a function body, an `if TYPE_CHECKING:` block, or a `try` that handles ImportError (that is a
    declared optional)."""
    names: set[str] = set()

    def walk(stmts):
        for n in stmts:
            if isinstance(n, ast.Import):
                names.update(a.name.split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                names.add(n.module.split(".")[0])
            elif isinstance(n, ast.If):
                if "TYPE_CHECKING" in ast.unparse(n.test):
                    continue  # never true at runtime
                walk(n.body)
                walk(n.orelse)
            elif isinstance(n, ast.Try):
                handled = {
                    getattr(h.type, "id", None) or getattr(h.type, "attr", None)
                    for h in n.handlers
                }
                if not handled & {
                    "ImportError",
                    "ModuleNotFoundError",
                    "Exception",
                    None,
                }:
                    walk(n.body)

    walk(ast.parse(path.read_text()).body)
    return names


def test_every_module_imports_with_only_what_the_image_installs():
    installed, copied = _image()
    local = {p.stem for p in copied} | {"fleetview_backend"}
    stdlib = set(sys.stdlib_module_names)
    missing = {}
    for path in copied:
        bad = sorted(
            n
            for n in _module_level_imports(path) - stdlib - installed - local
            if n != "__future__"
        )
        if bad:
            missing[str(path.relative_to(ROOT))] = bad
    assert any(p.parent == PKG for p in copied), (
        "the Dockerfile no longer COPYs fleetview_backend"
    )
    assert not missing, (
        "these modules would raise ModuleNotFoundError in the fleetview-backend image; add the "
        f"package to its pip line or COPY the file: {missing}"
    )


def test_every_import_inside_a_function_is_installed_or_declared_optional():
    installed, copied = _image()
    local = {p.stem for p in copied} | {"fleetview_backend"}
    stdlib = set(sys.stdlib_module_names)
    missing = {}
    for path in copied:
        names = set()
        for n in ast.walk(ast.parse(path.read_text())):
            if isinstance(n, ast.Import):
                names.update(a.name.split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                names.add(n.module.split(".")[0])
        bad = sorted(names - stdlib - installed - local - OPTIONAL - {"__future__"})
        if bad:
            missing[str(path.relative_to(ROOT))] = bad
    assert not missing, (
        "these imports would fail in the fleetview-backend image when their route runs; install "
        f"the package or, if it is meant to be absent on OKE, add it to OPTIONAL: {missing}"
    )


def test_voice_list_answers_without_the_local_speech_engine(monkeypatch):
    pytest.importorskip("jsonschema")
    sys.path.insert(0, str(PKG.parent))
    try:
        from fleetview_backend import voice_media as vm
    finally:
        sys.path.remove(str(PKG.parent))
    monkeypatch.setitem(sys.modules, "sovereign", None)
    monkeypatch.setitem(sys.modules, "sovereign.voice", None)
    monkeypatch.setattr(vm, "_choice", {"engine": "cloud", "voice": "troy"})

    cat = asyncio.run(vm.voices())

    assert cat["cloud"] == vm.CLOUD_VOICES and cat["cloud"]
    assert cat["kokoro"] == cat["say"] == cat["piper"] == []
    assert cat["current"] == {"engine": "cloud", "cloud": "troy"}
