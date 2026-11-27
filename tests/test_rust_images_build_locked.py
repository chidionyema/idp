"""Every Rust image builds from its committed lock, on a toolchain at least as new as its floor.

main build-multiarch went red on two Rust images on 2026-11-27 (run 46012162636), one class:
- ground-truth committed a Cargo.lock but its Dockerfile never copied it and built without
  --locked, so every build resolved fresh crates; icu_properties_data 2.4.0 needs edition2024,
  which the pinned rust:1.82 cannot parse.
- edge-runtime locked candle-core 0.11.1, which calls core::arch __cpuid_count as a safe fn
  (safe from Rust 1.94.0); on the pinned rust:1.89 it fails E0133. Nothing declared the floor.
genesis-v1 had no lock at all, and nothing tied any image's toolchain to its crate (idp#8652).

Rules, per Rust image bin/dockerfiles lists:
1. the Dockerfile copies Cargo.lock and every `cargo build` passes --locked;
2. the crate (or workspace) declares rust-version, and every workspace member inherits it;
3. the builder image's rust:<x.y> is >= that rust-version.
"""

import json
import pathlib
import re
import subprocess
import sys

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11 on a laptop; CI runs 3.12
    import tomli as tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUST_FROM = re.compile(r"^FROM\s+(?:docker\.io/)?(?:library/)?rust:(\d+)\.(\d+)", re.M)


def _ver(text: str) -> tuple[int, int]:
    major, minor = text.split(".")[:2]
    return int(major), int(minor)


def violations(
    dockerfile_text: str, cargo: dict, members: dict[str, dict]
) -> list[str]:
    out = []
    m = RUST_FROM.search(dockerfile_text)
    if not m:
        return ["no rust:<x.y> builder image"]
    image = (int(m.group(1)), int(m.group(2)))
    if not re.search(r"^COPY\s+(?:\.\s|.*\bCargo\.lock\b)", dockerfile_text, re.M):
        out.append("Dockerfile does not copy Cargo.lock")
    builds = re.findall(r"cargo build[^\n]*", dockerfile_text)
    if not builds or any("--locked" not in b for b in builds):
        out.append("cargo build without --locked")
    floor = (cargo.get("package") or {}).get("rust-version") or (
        (cargo.get("workspace") or {}).get("package") or {}
    ).get("rust-version")
    if not floor:
        out.append("no rust-version declared")
    elif image < _ver(floor):
        out.append(f"rust:{image[0]}.{image[1]} is below rust-version {floor}")
    for name, member in members.items():
        rv = (member.get("package") or {}).get("rust-version")
        if rv != {"workspace": True} and not isinstance(rv, str):
            out.append(f"member {name} does not inherit rust-version")
    return out


def rust_images() -> list[dict]:
    listing = subprocess.run(  # noqa: S603 -- the estate's own image inventory
        [str(ROOT / "bin" / "dockerfiles"), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return [
        d
        for d in json.loads(listing.stdout)
        if RUST_FROM.search((ROOT / d["dockerfile"]).read_text())
    ]


def check_image(d: dict) -> list[str]:
    ctx = ROOT / d["context"]
    text = (ROOT / d["dockerfile"]).read_text()
    out = [] if (ctx / "Cargo.lock").is_file() else ["no committed Cargo.lock"]
    cargo = tomllib.loads((ctx / "Cargo.toml").read_text())
    members = {}
    for pattern in (cargo.get("workspace") or {}).get("members", []):
        for path in sorted(ctx.glob(pattern)):
            members[str(path.relative_to(ctx))] = tomllib.loads(
                (path / "Cargo.toml").read_text()
            )
    return out + violations(text, cargo, members)


IMAGES = rust_images()


def test_the_inventory_finds_the_rust_images():
    # An inventory that finds nothing would make every case below vacuous.
    assert {"edge-runtime", "ground-truth"} <= {d["name"] for d in IMAGES}, IMAGES


@pytest.mark.parametrize("d", IMAGES, ids=lambda d: d["name"])
def test_rust_image_builds_locked_on_its_floor(d):
    assert check_image(d) == []


GOOD = (
    "FROM rust:1.94-bookworm AS b\n"
    "COPY Cargo.toml Cargo.lock ./\n"
    "RUN cargo build --release --locked\n"
)
FLOOR = {"package": {"rust-version": "1.94"}}


def test_known_good_passes():
    assert violations(GOOD, FLOOR, {}) == []


@pytest.mark.parametrize(
    "dockerfile,cargo,expected",
    [
        # ground-truth on main: lock not copied, unlocked build, no floor
        (
            "FROM rust:1.82-slim-bookworm AS b\n"
            "COPY Cargo.toml ./\n"
            "RUN cargo build --release --bins\n",
            {"package": {}},
            {
                "Dockerfile does not copy Cargo.lock",
                "cargo build without --locked",
                "no rust-version declared",
            },
        ),
        # edge-runtime with its floor declared but the old toolchain
        (GOOD.replace("1.94", "1.89"), FLOOR, {"rust:1.89 is below rust-version 1.94"}),
    ],
)
def test_known_bad_is_refused(dockerfile, cargo, expected):
    assert set(violations(dockerfile, cargo, {})) == expected


def test_a_member_that_does_not_inherit_the_floor_is_refused():
    ws = {"workspace": {"package": {"rust-version": "1.89"}}}
    got = violations(GOOD.replace("1.94", "1.89"), ws, {"crates/a": {"package": {}}})
    assert got == ["member crates/a does not inherit rust-version"]


if __name__ == "__main__":
    if "--optimus" in sys.argv:
        n = sum(len(check_image(d)) for d in IMAGES)
        print(f"optimus.rust.image_lock_floor_violations={n}")
        raise SystemExit(0)
    raise SystemExit("run under pytest, or with --optimus")
