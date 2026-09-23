#!/usr/bin/env python3
"""bin/estate-diagram: property + incident tests (crew#236 row 2, R29).

Rungs, per ~/AGENTS.md "How to test":
  property  for random synthetic catalogues, every Component and every port/job
            Resource name appears on the page, the counts on a node equal the
            dependsOn edges pointing at it, and rendering twice gives the same bytes.
  incident  named for R29 "a hand-drawn one is deleted": --check fails when the
            page on disk drifts from the catalogue and passes after a render, proved
            both ways in one run.

Run: python3 tests/test_estate_diagram.py (needs pyyaml). Exit 0 pass, 1 fail.
"""
import importlib.machinery
import importlib.util
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "estate-diagram"
spec = importlib.util.spec_from_loader("estate_diagram", importlib.machinery.SourceFileLoader("estate_diagram", str(BIN)))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def synth(rng: random.Random) -> list:
    comps = [f"repo-{i}" for i in range(rng.randint(1, 6))]
    docs = [{"apiVersion": "backstage.io/v1alpha1", "kind": "Component",
             "metadata": {"name": c, "annotations": {"estate/path": f"checkout-{c}", "estate/coupling": rng.choice(["none", "anthropic", "openai"])}},
             "spec": {"type": "service"}} for c in comps]
    for t in ("scheduled-job", "guard", "ledger", "port", "drill"):
        for i in range(rng.randint(0, 5)):
            ann = {"estate/interval-s": str(rng.choice([30, 60, 3600])), "estate/last-status": rng.choice(["0", "1"]), "estate/loaded": "yes"}
            if t == "port":
                ann = {"estate/port": str(1000 + i), "estate/owner": "python", "estate/bind": "127.0.0.1", "estate/command": f"checkout-{rng.choice(comps)}/run"}
            docs.append({"kind": "Resource", "metadata": {"name": f"{t}-{i}", "annotations": ann},
                         "spec": {"type": t, "dependsOn": [] if t == "port" else [f"component:default/{rng.choice(comps)}"]}})
    return docs


def prop_every_entity_present_and_counts_match(n=200) -> int:
    fails = 0
    for seed in range(n):
        rng = random.Random(seed)
        docs = synth(rng)
        page = mod.render("2026-01-01T00:00:00Z", docs)
        if page != mod.render("2026-01-01T00:00:00Z", docs):
            fails += 1; print(f"FAIL seed={seed}: not deterministic"); continue
        for d in docs:
            t = d.get("spec", {}).get("type")
            if d["kind"] == "Component" or t in ("port", "scheduled-job"):
                if d["metadata"]["name"] not in page:
                    fails += 1; print(f"FAIL seed={seed}: {d['metadata']['name']} missing"); break
        for c in (d for d in docs if d["kind"] == "Component"):
            name = c["metadata"]["name"]
            want = {t: sum(1 for d in docs if d["kind"] == "Resource" and d["spec"]["type"] == t and f"component:default/{name}" in d["spec"]["dependsOn"])
                    for t in ("scheduled-job", "guard", "ledger")}
            label = f"{name}<br/>{want['scheduled-job']} jobs · {want['guard']} guards · {want['ledger']} ledgers"
            if label not in page:
                fails += 1; print(f"FAIL seed={seed}: counts wrong for {name}"); break
    return fails


def incident_r29_hand_drawn_page_is_refused() -> int:
    with tempfile.TemporaryDirectory() as td:
        cat, out = Path(td) / "c.yaml", Path(td) / "live.md"
        cat.write_text("# inventory taken: 2026-01-01T00:00:00Z\n" + yaml.safe_dump_all(synth(random.Random(7))))
        out.write_text("# Live estate\nhand drawn\n")
        bad = subprocess.run([sys.executable, str(BIN), "--catalog", cat, "--out", out, "--check"], capture_output=True, text=True)
        subprocess.run([sys.executable, str(BIN), "--catalog", cat, "--out", out], check=True, capture_output=True)
        good = subprocess.run([sys.executable, str(BIN), "--catalog", cat, "--out", out, "--check"], capture_output=True, text=True)
        missing = subprocess.run([sys.executable, str(BIN), "--catalog", cat.with_name("nope.yaml"), "--check"], capture_output=True, text=True)
    ok = bad.returncode == 1 and "FAIL" in bad.stdout and good.returncode == 0 and "ok" in good.stdout and missing.returncode == 3 and "BLIND" in missing.stderr
    print(f"{'ok  ' if ok else 'FAIL'}  incident r29: drifted rc={bad.returncode}, rendered rc={good.returncode}, no catalogue rc={missing.returncode}")
    return 0 if ok else 1


def test_property_every_entity_present_and_counts_match():
    assert prop_every_entity_present_and_counts_match() == 0


def test_incident_r29_hand_drawn_page_is_refused():
    assert incident_r29_hand_drawn_page_is_refused() == 0


if __name__ == "__main__":
    f = prop_every_entity_present_and_counts_match()
    print(f"{'ok  ' if not f else 'FAIL'}  property: 200 synthetic catalogues, {f} failures")
    f += incident_r29_hand_drawn_page_is_refused()
    sys.exit(1 if f else 0)
