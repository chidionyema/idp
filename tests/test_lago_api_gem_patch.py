"""lago-api's gem patch: the lock it writes is consistent, or the build stops (idp#8658).

getlago/api v1.52.1 locks activestorage 8.0.5.1, CRITICAL (CVE-2026-122006), and the 8.0
line's patch release fixes it. platform/commerce/app/lago-api-gem-patch.rb moves the bundle
to that closure inside the image build. These tests prove the script refuses what would
break the app: a dependent left behind, a downgrade, or a target the lock does not hold.
A known-good bump is accepted, and only the versions and the target's own dependency lines
change. `--optimus` prints how many advisories in ADVISORIES the Dockerfile does not patch.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "platform/commerce/app"
SCRIPT = APP / "lago-api-gem-patch.rb"
DOCKERFILE = APP / "lago-api.Dockerfile"

# gem -> the first version that fixes a CRITICAL the base image's lock carries, on its line.
ADVISORIES = {"activestorage": "8.0.5.2"}  # CVE-2026-122006 / GHSA-f3w6-w445-fwh9

LOCK = """GEM
  remote: https://rubygems.org/
  specs:
    alpha (1.0.0)
      beta (= 1.0.0)
      gamma (~> 1.0)
    beta (1.0.0)
      gamma (>= 1.0)
    delta (2.0.0)
      gamma (~> 1.0)
    gamma (1.0.0-x86_64-linux-gnu)
      racc (~> 1.4)
    gamma (1.0.0-aarch64-linux-gnu)
      racc (~> 1.4)
    racc (1.8.1)

PLATFORMS
  x86_64-linux

DEPENDENCIES
  alpha (~> 1.0)
"""


def _spec(directory: Path, name: str, version: str, deps: dict[str, list[str]]) -> None:
    lines = [
        "Gem::Specification.new do |s|",
        f"  s.name = {name!r}",
        f"  s.version = {version!r}",
        "  s.summary = 'fixture'",
        "  s.authors = ['estate']",
        "  s.files = []",
    ]
    lines += [f"  s.add_dependency {d!r}, {reqs!r}" for d, reqs in deps.items()]
    lines.append("end")
    (directory / f"{name}-{version}.gemspec").write_text("\n".join(lines) + "\n")


def _run(tmp_path: Path, specs: list[tuple[str, str, dict[str, list[str]]]]):
    ruby = shutil.which("ruby")
    assert ruby, "ruby is not on PATH: this gate cannot judge, so it refuses"
    lock = tmp_path / "Gemfile.lock"
    lock.write_text(LOCK)
    specdir = tmp_path / "specs"
    specdir.mkdir()
    for name, version, deps in specs:
        _spec(specdir, name, version, deps)
    proc = subprocess.run(  # noqa: S603 - fixed argv
        [ruby, str(SCRIPT), str(lock), str(specdir)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return proc, lock.read_text()


def test_known_good_bump_rewrites_versions_and_only_the_targets_dependencies(tmp_path):
    proc, lock = _run(
        tmp_path,
        [
            ("alpha", "1.0.1", {"beta": ["= 1.0.1"], "gamma": ["~> 1.0", ">= 1.0.2"]}),
            ("beta", "1.0.1", {"gamma": [">= 1.0"]}),
            ("gamma", "1.0.2", {"racc": ["~> 1.4"]}),
        ],
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split("\n")[:3] == ["alpha 1.0.0", "beta 1.0.0", "gamma 1.0.0"]
    assert (
        "    alpha (1.0.1)\n      beta (= 1.0.1)\n      gamma (~> 1.0, >= 1.0.2)\n"
        in lock
    )
    # every platform the lock records moves, and keeps its platform
    assert "    gamma (1.0.2-x86_64-linux-gnu)\n" in lock
    assert "    gamma (1.0.2-aarch64-linux-gnu)\n" in lock
    # an untouched gem and every other section stay byte-identical
    assert "    delta (2.0.0)\n      gamma (~> 1.0)\n" in lock
    assert lock.endswith("DEPENDENCIES\n  alpha (~> 1.0)\n")


def test_falsifier_a_dependent_left_behind_is_refused_and_nothing_is_written(tmp_path):
    # alpha 1.0.1 pins beta 1.0.1, but beta is not among the targets
    proc, lock = _run(tmp_path, [("alpha", "1.0.1", {"beta": ["= 1.0.1"]})])
    assert proc.returncode == 1
    assert "alpha (1.0.1) needs beta (= 1.0.1); the lock holds 1.0.0" in proc.stderr
    assert lock == LOCK


def test_falsifier_a_requirement_the_new_version_breaks_is_refused(tmp_path):
    # gamma 2.0.0 leaves delta's `~> 1.0` unmet
    proc, lock = _run(tmp_path, [("gamma", "2.0.0", {"racc": ["~> 1.4"]})])
    assert proc.returncode == 1
    assert "delta (2.0.0) needs gamma (~> 1.0)" in proc.stderr
    assert lock == LOCK


def test_falsifier_a_downgrade_is_refused(tmp_path):
    proc, lock = _run(tmp_path, [("racc", "1.7.0", {})])
    assert proc.returncode == 1
    assert "refusing to downgrade" in proc.stderr
    assert lock == LOCK


def test_falsifier_a_target_the_lock_does_not_hold_is_refused(tmp_path):
    proc, lock = _run(tmp_path, [("epsilon", "1.0.0", {})])
    assert proc.returncode == 1
    assert "the lock holds no epsilon" in proc.stderr
    assert lock == LOCK


def fetched_versions(dockerfile: str) -> dict[str, str]:
    """gem -> version the Dockerfile's `gem fetch` lines take, loops included."""
    text = dockerfile.replace("\\\n", " ")
    out: dict[str, str] = {}
    for names, version in re.findall(
        r"for g in ([a-z0-9_ -]+?); do\s+gem fetch \"\$g\" --version (\S+)", text
    ):
        out.update(dict.fromkeys(names.split(), version))
    out.update(dict(re.findall(r"gem fetch ([a-z][a-z0-9_-]*) --version (\S+)", text)))
    return out


def _at_least(version: str, floor: str) -> bool:
    def key(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v.split("."))

    return key(version) >= key(floor)


def unpatched(dockerfile: str) -> list[str]:
    got = fetched_versions(dockerfile)
    return [
        g
        for g, fixed in ADVISORIES.items()
        if g not in got or not _at_least(got[g], fixed)
    ]


def test_the_dockerfile_runs_the_patch_and_reaches_every_advisory_fix():
    text = DOCKERFILE.read_text()
    assert "COPY lago-api-gem-patch.rb /tmp/gem-patch.rb" in text
    assert "ruby /tmp/gem-patch.rb Gemfile.lock /tmp/gems" in text
    assert unpatched(text) == []


def boot_requires(dockerfile: str) -> list[str]:
    """The libraries the build's load check requires after the patch, in order."""
    m = re.search(r"puts \"patched #\{want\}\"", dockerfile)
    line = dockerfile[: m.start()].rsplit("bundle exec ruby -e", 1)[-1] if m else ""
    return re.findall(r'require "([^"]+)"', line)


def test_the_load_check_boots_rails_the_way_the_app_does():
    # getlago/api v1.52.1 config/application.rb: `require "rails/all"`. A framework required on
    # its own skips what Rails loads first: activestorage 8.0.5.2 raised
    # `uninitialized constant ActiveStorage::OpenSSL` on main run 46047259207.
    assert boot_requires(DOCKERFILE.read_text())[0] == "rails/all"


def test_falsifier_a_check_that_requires_one_framework_alone_is_refused():
    landed = (
        "bundle exec ruby -e 'want = {}; "
        'require "active_storage"; require "nokogiri"; puts "patched #{want}"\''
    )
    assert boot_requires(landed)[0] != "rails/all"


def test_falsifier_the_metric_counts_a_dockerfile_without_the_patch():
    assert unpatched("FROM docker.io/getlago/api:v1.52.1\n") == ["activestorage"]
    assert unpatched(
        'RUN for g in activestorage rails; do \\\n gem fetch "$g" --version 8.0.5.1'
    ) == ["activestorage"]


if __name__ == "__main__" and "--optimus" in sys.argv:
    print(
        f"optimus.images.lago_api_critical_gems_unpatched={len(unpatched(DOCKERFILE.read_text()))}"
    )
