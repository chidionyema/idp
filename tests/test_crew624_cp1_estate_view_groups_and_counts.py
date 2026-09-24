"""crew#624 CP1: one grouped, counted estate view from the three receipts.

Founder, 2026-08-29: "I NEED THE NUMBERS OF THINGS GROUPED ... WHAT IS IN THE DARK". Graded on
fixture receipts: every red Flux row and pod lands in a layer with a reason, the dark counts
come from the coverage and drift receipts, and an unreadable receipt is a dark row, never a
crash.
"""

import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "idp-estate-view"
FIX = ROOT / "tests" / "fixtures" / "estate-view"


def run(*extra):
    args = [
        str(BIN),
        "--cluster",
        str(FIX / "cluster.txt"),
        "--coverage",
        str(FIX / "coverage.txt"),
        "--drift",
        str(FIX / "drift.txt"),
        *extra,
    ]
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def test_totals_and_reasons_are_counted():
    v = json.loads(run("--json"))
    assert v["totals"] == {
        "nodes": 2,
        "nodes_ready": 2,
        "flux": 6,
        "flux_red": 4,
        "pods": 100,
        "pods_red": 1,
        "alerts_firing": 2,
    }
    assert v["red_by_reason"] == {
        "stalled": 2,
        "waiting-on-dependency": 1,
        "image-or-chart-pull": 1,
        "Pending": 1,
    }


def test_reds_are_grouped_by_layer_red_first():
    v = json.loads(run("--json"))
    layers = [g["layer"] for g in v["groups"]]
    assert layers[0] in ("identity", "ai")  # both carry two reds; ties sort by name
    ident = next(g for g in v["groups"] if g["layer"] == "identity")
    assert ident["flux_red"] == 1 and ident["pods_red"] == 1
    assert {r["why"] for r in ident["red"]} == {"image-or-chart-pull", "Pending"}
    policy = next(g for g in v["groups"] if g["layer"] == "policy")
    assert policy["flux_red"] == 0 and policy["flux_total"] == 1


def test_dark_is_counted_from_the_other_receipts():
    v = json.loads(run("--json"))
    assert v["dark"]["pods_no_telemetry"] == 2
    assert v["dark"]["services_unlisted"] == 5
    assert v["dark"]["catalogue_drift"] == 5
    assert v["dark"]["receipts_unreadable"] == []


def test_an_unreadable_receipt_is_a_dark_row_not_a_crash(tmp_path):
    missing = tmp_path / "none.txt"
    out = subprocess.run(
        [
            str(BIN),
            "--cluster",
            str(FIX / "cluster.txt"),
            "--coverage",
            str(missing),
            "--drift",
            str(FIX / "drift.txt"),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    v = json.loads(out)
    assert len(v["dark"]["receipts_unreadable"]) == 1
    assert "idp-telemetry-coverage" in v["dark"]["receipts_unreadable"][0]


def test_text_mode_reads_as_one_screen():
    t = run()
    assert t.startswith("estate receipt 2026-08-29T13:00:00Z")
    assert (
        "flux red 4/6" in t
        and "dark: 2 pods no telemetry, 5 services unlisted, 5 catalogue drift" in t
    )
