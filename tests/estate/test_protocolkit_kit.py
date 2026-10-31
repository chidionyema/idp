"""The founder's own kit suite, run from the repository so it cannot be lost with /tmp.

The kit at platform/estate/protocolkit is the founder's artifact, byte for byte: this file does
not change it. It puts the kit on sys.path, loads the founder's test module, and re-exports its
tests so pytest collects them HERE. If the kit is deleted or edited, this file fails -- which is
the point. The kit is a dependency of this repository, not a scratch copy in /tmp.
"""

import importlib.util
import os
import sys

KIT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "platform",
    "estate",
    "protocolkit",
)


def _load_kit():
    """The kit, loaded BY PATH so no sys.path entry can shadow it with a namespace package.

    /tmp/protocolkit -- where the kit was born -- is a directory named `protocolkit` without an
    __init__.py, so a plain `import protocolkit` finds THAT and the real package never loads.
    """
    existing = sys.modules.get("protocolkit")
    if existing is not None and str(getattr(existing, "__file__", "")).startswith(
        KIT_DIR
    ):
        return existing
    pkg_dir = os.path.join(KIT_DIR, "protocolkit")
    spec = importlib.util.spec_from_file_location(
        "protocolkit",
        os.path.join(pkg_dir, "__init__.py"),
        submodule_search_locations=[pkg_dir],
    )
    assert spec and spec.loader, (
        "the founder's protocol kit is missing from the repository"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["protocolkit"] = module
    spec.loader.exec_module(module)
    return module


_load_kit()

_SPEC = importlib.util.spec_from_file_location(
    "protocolkit_founder_tests", os.path.join(KIT_DIR, "test_protocolkit.py")
)
assert _SPEC and _SPEC.loader, "the founder's kit test file is missing"
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules["protocolkit_founder_tests"] = _MODULE
_SPEC.loader.exec_module(_MODULE)

for _name in dir(_MODULE):
    if _name.startswith("test_"):
        globals()[_name] = getattr(_MODULE, _name)
