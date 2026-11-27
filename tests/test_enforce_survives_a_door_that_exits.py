"""estate-memory-enforce must load when its memory door exits on import (idp#8672).

`platform/estate/memory/local_store.py` raises SystemExit when the write guard's dependencies
(pydantic) are absent. The hook imported `door` inside `except Exception`, which SystemExit
escapes, so the hook died on import in any checkout without pydantic. Greenlane runs every
catalog measure in such a checkout, so the three measures that load the hook printed nothing and
idp#8660 was judged NOT OPERATIONAL at 19:10Z on `hooks.enforce_shared_name_unresolved_when_relocated=UNKNOWN`.
A door that will not import is a verdict, never a crash: the hook must load with door=None.
"""

import ast
import importlib.abc
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BIN = REPO / "bin" / "estate-memory-enforce"
MEMORY = REPO / "platform" / "estate" / "memory"


def loads_when_door_exits(source: Path) -> bool:
    """True when the hook at `source` imports while `import door` raises SystemExit."""

    class _Exits(importlib.abc.Loader):
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            raise SystemExit("local_store needs the estate's own write guard")

    class _Finder:
        @staticmethod
        def find_spec(name, path=None, target=None):
            if name == "door":
                return importlib.util.spec_from_loader("door", _Exits())
            return None

    saved = sys.modules.pop("door", None)
    sys.meta_path.insert(0, _Finder)
    # A copy outside bin/ (main's file, the falsifier's) still finds focus/handback/plan.
    sys.path.insert(0, str(MEMORY))
    try:
        loader = importlib.machinery.SourceFileLoader("eme_door_probe", str(source))
        spec = importlib.util.spec_from_loader("eme_door_probe", loader)
        mod = importlib.util.module_from_spec(spec)
        try:
            loader.exec_module(mod)
        except SystemExit:
            return False
        return mod.door is None and "SystemExit" in mod.door_error
    finally:
        sys.meta_path.remove(_Finder)
        sys.path.remove(str(MEMORY))
        sys.modules.pop("door", None)
        if saved is not None:
            sys.modules["door"] = saved


DOOR_MODULES = {"door", "local_store"}


def unguarded_door_imports(root: Path) -> list[str]:
    """Every `try: import door` (or local_store) whose handlers let SystemExit escape.

    local_store raises SystemExit on a missing dependency, so a guard that names only
    Exception or ImportError crashes the caller instead of returning its verdict.
    """
    found = []
    files = [
        p
        for d in ("bin", "platform", "greenlane", "mcp")
        for p in (root / d).rglob("*")
    ]
    for path in files:
        if not path.is_file() or "node_modules" in path.parts:
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if "import door" not in text and "import local_store" not in text:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            imports = {
                a.name.split(".")[0]
                for st in node.body
                if isinstance(st, (ast.Import, ast.ImportFrom))
                for a in (
                    st.names
                    if isinstance(st, ast.Import)
                    else [ast.alias(st.module or "")]
                )
            }
            if not imports & DOOR_MODULES:
                continue
            caught = set()
            for h in node.handlers:
                if h.type is None:
                    caught.add("BaseException")
                for n in ast.walk(h.type) if h.type is not None else []:
                    if isinstance(n, ast.Name):
                        caught.add(n.id)
            if not caught & {"SystemExit", "BaseException"}:
                found.append(f"{path.relative_to(root)}:{node.lineno}")
    return sorted(found)


def test_sweep_no_door_import_lets_systemexit_escape():
    assert unguarded_door_imports(REPO) == []


def test_falsifier_the_sweep_finds_an_exception_only_guard(tmp_path):
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "x.py").write_text(
        "try:\n    import door\nexcept Exception:\n    door = None\n"
    )
    (tmp_path / "bin" / "ok.py").write_text(
        "try:\n    import door\nexcept (Exception, SystemExit):\n    door = None\n"
    )
    assert unguarded_door_imports(tmp_path) == ["bin/x.py:1"]


def test_the_hook_loads_with_the_door_as_a_verdict():
    assert loads_when_door_exits(BIN)


def test_falsifier_an_exception_only_guard_dies_on_import(tmp_path):
    text = BIN.read_text()
    old = "except (Exception, SystemExit) as _door_exc:"
    assert old in text, "the door guard line moved; update the falsifier"
    narrow = tmp_path / "estate-memory-enforce"
    narrow.write_text(text.replace(old, "except Exception as _door_exc:"))
    assert not loads_when_door_exits(narrow)


if __name__ == "__main__":
    if "--optimus" not in sys.argv:
        sys.exit(
            "usage: python3 tests/test_enforce_survives_a_door_that_exits.py --optimus [--source PATH] [--root PATH]"
        )
    src = (
        Path(sys.argv[sys.argv.index("--source") + 1])
        if "--source" in sys.argv
        else BIN
    )
    print(
        f"optimus.hooks.enforce_dies_when_door_exits={int(not loads_when_door_exits(src))}"
    )
    root = (
        Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else REPO
    )
    print(
        f"optimus.memory.door_imports_crash_on_exit={len(unguarded_door_imports(root))}"
    )
