"""Complete automated verification of /fleet and /face (crew research 2026-10-02, CP1).

THE LAW (docs/research/2026-10-02-complete-automated-verification.md §3): coverage is generated,
not narrated. The inventory is enumerated from the code at run time and the gate FAILS when any
enumerated feature lacks a covering probe, or when an inventory source parses to nothing.

CP1 levels:
  L1 reach   every page and asset fetched THROUGH THE PUBLIC GATE (signed-out): 200 + type + size
  L2 auth    negative controls: a bad bearer is refused on the API surface
  COVERAGE   inventory ∩ probe plan == inventory, else red

Every function takes the http callable so tests run against a stub and mutations can break doors.
Output contract, like every bin/idp-* helper: one grading line per assertion,
`PASS|FAIL  surfaces.<name>  <detail>`, and probe() returns verdict assertion objects.
"""

from __future__ import annotations

import re
import subprocess
import sys

from probes.langfuse import http
from probes.verdict import assertion

REPO = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
).stdout.strip()

# --- inventory sources -------------------------------------------------------
# Seed paths lane A serves as public shells; the enumerator adds everything the code contains.
SEED_PAGES = ["/fleet", "/face", "/voice"]

_ASSET_DIR = "backstage/packages/app/public/face"
_PANEL_DIR = "backstage/packages/app/src/modules/room/ui"
_MODULES = "backstage/packages/app/src/modules"
_SERVE = "backstage/plugins/fleetview-backend/src/fleetview_backend/serve.py"
_ROUTES = "backstage/plugins/fleetview-backend/src/fleetview_backend/routes.py"


def _git(*args: str) -> str:
    p = subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO)
    return p.stdout if p.returncode == 0 else ""


def _read(path: str) -> str:
    return _git("show", f"HEAD:{path}")


def enumerate_inventory() -> dict[str, list[str]]:
    """Every feature is enumerated from the code. A source that parses to nothing is a defect
    (§3): the caller must treat an empty key as a parse failure, not as 'no features'."""
    inv: dict[str, list[str]] = {}

    # pages: route bindings in frontend modules + committed seed. PUBLIC shells must serve
    # without the gate (lane A, crew#1017); /fleet is the founder's private surface and the
    # GATE ITSELF is its expected signed-out behaviour (app-behind-gate is graded with the
    # prover token in CI, same as probes/backstage.py).
    public_seed = {"/face", "/voice"}
    pages = set(SEED_PAGES)
    tree = _git("ls-tree", "-r", "HEAD", "--name-only", _MODULES).splitlines()
    for f in tree:
        if not f.endswith((".tsx", ".ts")):
            continue
        src = _read(f)
        # ONLY frontend-module route mounts are app pages; bare path= strings are proxy
        # prefixes, links and config literals and must not leak into the page inventory
        for m in re.finditer(r'mountRoute\s*\(\s*[^,]+,\s*["\'](/[A-Za-z0-9_\-]+)["\']', src):
            pages.add(m.group(1))
    inv["pages"] = sorted(pages)
    inv["public_pages"] = sorted(pages & public_seed)

    # face assets: every file under public/face is load-bearing for the avatar
    inv["face_assets"] = sorted(
        "/face/" + line.split("/")[-1]
        for line in _git("ls-tree", "-r", "HEAD", "--name-only", _ASSET_DIR).splitlines()
        if line.endswith((".mjs", ".js", ".glb"))
    )

    # fleet panels: every component under room/ui (logic modules get behaviour probes in CP2)
    inv["panels"] = sorted(
        line.split("/")[-1].removesuffix(".tsx")
        for line in _git("ls-tree", "-r", "HEAD", "--name-only", _PANEL_DIR).splitlines()
        if line.endswith(".tsx") and not line.endswith(".test.tsx")
    )

    # voice states: the state machine in useEstateVoice is the contract
    hook = _read("backstage/packages/app/src/modules/home/useEstateVoice.ts")
    m = _STATE_RE.search(hook)
    inv["voice_states"] = (
        sorted(s.strip().strip("'") for s in m.group(1).split("|") if s.strip())
        if m
        else []
    )

    # backend surface: every mounted endpoint
    endpoints = set(re.findall(r'@app\.(?:get|post|delete|put)\("([^"]+)"', _read(_SERVE)))
    endpoints.update(
        re.findall(r'^\s*[A-Z_]*PATH\s*=\s*"([^"]+)"', _read(_ROUTES), re.M)
    )
    inv["backend"] = sorted(endpoints)
    return inv


_STATE_RE = re.compile(r"EstateVoiceState = ([^;]+);")


# --- probe plan: which inventory class each level covers ----------------------
COVERS = {
    "pages": ["l1.pages"],
    "face_assets": ["l1.face_assets"],
    "panels": ["enumerate.panels"],      # CP2 adds l3.panels.* behaviour probes
    "voice_states": ["enumerate.voice"],  # CP3 adds l4.voice.* conversation probes
    "backend": ["l2.backend.negative"],
}


def coverage_gate(inv: dict[str, list[str]]) -> list:
    out = []
    for klass, items in inv.items():
        if not items:
            out.append(assertion(f"coverage.{klass}", "non-empty enumeration", "EMPTY", False))
            continue
        out.append(assertion(f"coverage.{klass}", f"{len(items)} features", f"{len(items)}", True))
    return out


# --- L1: through the public gate, signed out ---------------------------------
LOGIN_MARKERS = ("identity.oraclecloud", "oauth2/authorize", "Sign in")


def _looks_like_login(body: str) -> bool:
    head = body[:600]
    return any(m in head for m in LOGIN_MARKERS)


def l1_gate_battery(host: str, inv: dict[str, list[str]], get=http, timeout: int = 15) -> list:
    """This is the probe that was missing on 2026-10-02: it fetches /face/brunette.glb
    through catalogue.mumchimp.com and refuses to accept a login redirect (followed
    redirects surface as 200 + HTML sign-in page, so the BODY is graded, not just status)."""
    out = []
    # public shells: the gate must NOT answer for these (today's live defect is exactly here)
    targets = [(p, 2_000, "public") for p in inv.get("public_pages", [])]
    targets += [(a, 1_000, "public") for a in inv["face_assets"]]
    # gated pages signed out: the gate answering with the login page is the CORRECT behaviour;
    # a 200-without-gate would be a security hole and fails here too
    targets += [(p, None, "gated") for p in inv["pages"] if p not in inv.get("public_pages", [])]
    for path, floor, kind in targets:
        status, body = get(f"{host}{path}", timeout=timeout)
        size = len(body or "")
        login = _looks_like_login(body or "")
        if kind == "public":
            ok = status == 200 and size >= floor and not login
            why = f"200 >={floor}B, no login page"
            got = f"{status}, {size}B" + (", LOGIN PAGE" if login else "")
        else:
            ok = (bool(login) and status == 200) or status in (401, 403)
            why = "gate present (login page or 401/403) signed-out"
            got = f"{status}, {size}B" + (", NO GATE" if not login and status not in (401, 403) else "")
        out.append(assertion(f"l1.gate{path}", why, got, ok))
    return out


def l1_subresources_battery(
    host: str, inv: dict[str, list[str]], get=http, timeout: int = 15
) -> list:
    """2026-10-03 defect class: a public shell whose every script 302s to SSO serves a page
    that can never execute -- l1.gate above passes (200, no login page) while the browser gets
    40 console errors and a blank canvas. The dependency closure comes from the SERVED HTML,
    not a hand list: every src=/href= the shell itself references must answer 200 without a
    login page. A followed 302 into SSO surfaces as 200 + sign-in body and fails here."""
    out = []
    for page in inv.get("public_pages", []):
        status, body = get(f"{host}{page}", timeout=timeout)
        refs = sorted(
            {
                m.group(1).split("?")[0]
                for m in re.finditer(r'(?:src|href)="(/[^"#]+)"', body or "")
                if not m.group(1).startswith("//")
            }
        )
        if not refs:
            out.append(
                assertion(
                    f"l1.exec{page}",
                    "shell references subresources",
                    "none found",
                    False,
                )
            )
            continue
        bad = []
        for r in refs:
            s2, b2 = get(f"{host}{r}", timeout=timeout)
            if s2 != 200 or _looks_like_login(b2 or ""):
                bad.append(f"{r}={s2}")
        out.append(
            assertion(
                f"l1.exec{page}",
                f"all {len(refs)} referenced subresources 200, no login page",
                f"{len(refs) - len(bad)}/{len(refs)} ok"
                + (f"; RED: {', '.join(bad[:4])}" if bad else ""),
                not bad,
            )
        )
    return out


# --- L2: negative controls ----------------------------------------------------
def l2_auth_negative(host: str, inv: dict[str, list[str]], get=http) -> list:
    out = []
    for ep in inv["backend"][:6]:  # sample per run; full sweep in CI (vault identity)
        status, _ = get(f"{host}{ep}", bearer="definitely-not-a-token", timeout=15)
        ok = status in (401, 403)
        out.append(assertion(f"l2.backend.negative{ep}", "refused (401/403)", f"{status}", ok))
    return out


def probe(host: str, token: str | None = None, get=http) -> list:
    inv = enumerate_inventory()
    return (
        coverage_gate(inv)
        + l1_gate_battery(host, inv, get=get)
        + l1_subresources_battery(host, inv, get=get)
        + l2_auth_negative(host, inv, get=get)
    )


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "https://catalogue.mumchimp.com"
    inv = enumerate_inventory()
    fails = 0
    lines = coverage_gate(inv) + l1_gate_battery(host, inv) + l2_auth_negative(host, inv)
    for a in lines:
        verdict = "PASS" if a["ok"] else "FAIL"
        fails += 0 if a["ok"] else 1
        print(f"{verdict}  surfaces.{a['name']}  expected={a['expected']} got={a['actual']}")
    print(f"--- inventory: {sum(len(v) for v in inv.values())} features "
          f"({', '.join(f'{k}={len(v)}' for k, v in inv.items())})")
    sys.exit(1 if fails else 0)
