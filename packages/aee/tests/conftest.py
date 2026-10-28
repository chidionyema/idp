"""Make the package and the estate's canonical serialisation importable."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PKG_SRC = HERE.parents[1] / "src"
REPO_ROOT = HERE.parents[3]

for path in (str(PKG_SRC), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)
