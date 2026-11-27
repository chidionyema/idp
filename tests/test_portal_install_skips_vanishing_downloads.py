"""The portal's yarn install never depends on a binary downloaded at install time (idp#8655).

onnxruntime-node 1.21.0 (pulled by @huggingface/transformers) runs a postinstall that, on
linux/x64, downloads onnxruntime-linux-x64-gpu-1.21.0.tgz from GitHub releases. That asset now
answers 404, so `yarn install --immutable` failed in portal-build (queue/b6405, job 140621394801)
for every lane that touched backstage/ or sovereign/requirements.txt, and would fail the image
build the first time its install layer missed the cache. The package ships its CPU binaries for
linux x64 and arm64; the download adds only the CUDA provider, which no runner or pod has.

Every package named in DOWNLOADS_AT_INSTALL must be `built: false` in backstage/package.json,
and the root workspace entry of backstage/yarn.lock must carry the same dependenciesMeta, or
`yarn install --immutable` refuses the lockfile.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKSTAGE = ROOT / "backstage"

# package -> what its install script fetches that the portal never uses
DOWNLOADS_AT_INSTALL = {
    "onnxruntime-node": "CUDA execution provider from github.com/microsoft/onnxruntime releases",
}


def lock_root_meta(lock: str) -> dict:
    m = re.search(
        r'^"root@workspace:\.":\n((?:  .*\n|    .*\n)+?)(?=\n|\Z)', lock, re.M
    )
    if not m:
        return {}
    body = m.group(1)
    meta = re.search(r"^  dependenciesMeta:\n((?:    .*\n)+)", body, re.M)
    out: dict = {}
    if not meta:
        return out
    name = None
    for line in meta.group(1).splitlines():
        if line.startswith("    ") and not line.startswith("      "):
            name = line.strip().rstrip(":").strip('"')
            out[name] = {}
        elif name and line.startswith("      "):
            k, _, v = line.strip().partition(": ")
            out[name][k] = {"true": True, "false": False}.get(v, v)
    return out


def violations(manifest: dict, lock: str) -> list[str]:
    meta = manifest.get("dependenciesMeta") or {}
    out = [
        f"{pkg} is not built: false in backstage/package.json ({why})"
        for pkg, why in sorted(DOWNLOADS_AT_INSTALL.items())
        if (meta.get(pkg) or {}).get("built") is not False
    ]
    if lock_root_meta(lock) != meta:
        out.append(
            "backstage/yarn.lock root workspace dependenciesMeta differs from package.json"
        )
    return out


def current() -> list[str]:
    return violations(
        json.loads((BACKSTAGE / "package.json").read_text()),
        (BACKSTAGE / "yarn.lock").read_text(),
    )


def test_the_portal_install_downloads_nothing_it_never_uses():
    assert current() == []


GOOD_LOCK = (
    '"root@workspace:.":\n  version: 0.0.0-use.local\n  resolution: "root@workspace:."\n'
    '  dependencies:\n    a: "npm:1"\n  dependenciesMeta:\n    onnxruntime-node:\n'
    "      built: false\n  languageName: unknown\n  linkType: soft\n\n"
)
GOOD = {"dependenciesMeta": {"onnxruntime-node": {"built": False}}}


def test_known_good_is_accepted():
    assert violations(GOOD, GOOD_LOCK) == []


def test_main_before_the_fix_is_refused():
    lock = GOOD_LOCK.replace(
        "  dependenciesMeta:\n    onnxruntime-node:\n      built: false\n", ""
    )
    v = violations({}, lock)
    assert any("onnxruntime-node is not built: false" in x for x in v)


def test_a_manifest_the_lockfile_does_not_mirror_is_refused():
    lock = GOOD_LOCK.replace(
        "  dependenciesMeta:\n    onnxruntime-node:\n      built: false\n", ""
    )
    assert violations(GOOD, lock) == [
        "backstage/yarn.lock root workspace dependenciesMeta differs from package.json"
    ]


def test_built_true_is_refused():
    bad = {"dependenciesMeta": {"onnxruntime-node": {"built": True}}}
    assert violations(bad, GOOD_LOCK.replace("built: false", "built: true"))


if __name__ == "__main__" and "--optimus" in sys.argv:
    print(f"optimus.portal.install_time_downloads_enabled={len(current())}")
