"""An image-update commit builds nothing.

2026-09-29: Flux image-automation wrote `newTag:` lines to main every ~5 min; bin/dockerfiles saw
the kustomization inside aevum's and sovereign-worker's build context and rebuilt them, which
minted the next tag, which image-automation wrote back. 37 commits in 8h; the Greenlane voided
every candidate with "main moved under it" and landed 0 of 24. This pins the cut: a diff whose
only changed lines carry `$imagepolicy` reaches no image; a real change still reaches its image.
"""

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "bin" / "dockerfiles"


def _init(tmp: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)


def _commit(tmp: Path, msg: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=tmp, check=True)
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp, text=True
    ).strip()


def _changed(tmp: Path, since: str) -> list[str]:
    # the script cds to its own repo root, so the copy under <tmp>/bin grades <tmp>
    (tmp / "bin").mkdir(exist_ok=True)
    (tmp / "bin" / "dockerfiles").write_bytes(SCRIPT.read_bytes())
    (tmp / "bin" / "dockerfiles").chmod(0o755)
    out = subprocess.check_output(
        [str(tmp / "bin" / "dockerfiles"), "--json", "--changed-since", since],
        cwd=tmp,
        text=True,
    )
    return [d["name"] for d in json.loads(out)]


def _seed(tmp: Path) -> str:
    _init(tmp)
    (tmp / "app.Dockerfile").write_text("FROM scratch\nCOPY . /app\n")
    (tmp / "main.py").write_text("print(1)\n")
    (tmp / "kustomization.yaml").write_text(
        'images:\n  - name: ghcr.io/x/app\n    newTag: main-1-aaaa # {"$imagepolicy": "flux-system:app:tag"}\n'
    )
    return _commit(tmp, "seed")


def test_image_update_only_commit_builds_nothing(tmp_path):
    base = _seed(tmp_path)
    (tmp_path / "kustomization.yaml").write_text(
        'images:\n  - name: ghcr.io/x/app\n    newTag: main-2-bbbb # {"$imagepolicy": "flux-system:app:tag"}\n'
    )
    _commit(tmp_path, "platform: image update app -> main-2-bbbb")
    assert _changed(tmp_path, base) == []


def test_real_change_in_context_still_builds(tmp_path):
    base = _seed(tmp_path)
    (tmp_path / "main.py").write_text("print(2)\n")
    _commit(tmp_path, "feat: change the app")
    assert _changed(tmp_path, base) == ["app"]


def test_tag_change_beside_a_real_line_still_builds(tmp_path):
    base = _seed(tmp_path)
    (tmp_path / "kustomization.yaml").write_text(
        'images:\n  - name: ghcr.io/x/app\n    newTag: main-2-bbbb # {"$imagepolicy": "flux-system:app:tag"}\nnamespace: app\n'
    )
    _commit(tmp_path, "kustomization: set namespace and bump tag")
    assert _changed(tmp_path, base) == ["app"]


def test_mid_sized_diff_is_never_dropped(tmp_path):
    # 2026-10-09: `git diff | grep ... | grep -q` under pipefail SIGPIPEd the writer whenever
    # grep -q quit before the diff was all written; both branches read false and #5545's
    # 65-line diff built nothing on the Linux runner. The size band that raced was a few KB to
    # 64KB, so every size in it is graded, several times.
    base = _seed(tmp_path)
    for n in (60, 200, 800, 2000, 4000):
        (tmp_path / "main.py").write_text(
            "".join(f"x{i} = {n}  # ›…\n" for i in range(n))
        )
        _commit(tmp_path, f"feat: {n} lines")
        for _ in range(5):
            assert _changed(tmp_path, base) == ["app"], n
