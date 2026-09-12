"""Every gate gets a UI demo (founder 2026-09-12: "everything needs UI demo").

The page for a rule is generated from rules.yaml and carries the gate's own real output: the
refused case's stderr and the permitted case's, with both exit codes. Nothing here asserts
prose -- every assertion either runs the gate or reads a file it wrote.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "bin" / "idp-gate-demo"
RULES = ROOT / "rules.yaml"
OUT = ROOT / "docs" / "gates"
NAV = ROOT / "mkdocs.yml"


def rules() -> list[dict]:
    return yaml.safe_load(RULES.read_text())["rules"]


def run_gen(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GEN), *args], cwd=ROOT, capture_output=True, text=True
    )


@pytest.fixture(scope="module", autouse=True)
def generated() -> None:
    """Render once for the whole module, so the pages under test are current."""
    run_gen("--out", str(OUT))


class TestTheGeneratorExists:
    def test_the_generator_is_on_disk(self):
        assert GEN.is_file(), f"no gate-demo generator at {GEN}"

    def test_it_renders_every_rule(self):
        proc = run_gen("--out", str(OUT))
        assert proc.returncode == 0, (
            f"the generator failed:\n{proc.stdout}\n{proc.stderr}"
        )


class TestEveryRuleGetsAPage:
    def test_one_page_per_rule(self):
        want = {r["id"] for r in rules()}
        got = {p.stem for p in OUT.glob("*.md")} - {"index"}
        missing = want - got
        assert not missing, f"no demo page for {sorted(missing)}"

    def test_no_page_without_a_rule(self):
        want = {r["id"] for r in rules()}
        got = {p.stem for p in OUT.glob("*.md")} - {"index"}
        extra = got - want
        assert not extra, f"pages with no rule behind them: {sorted(extra)}"


class TestThePageCarriesRealOutput:
    def test_the_page_carries_the_real_exit_codes(self):
        """Re-run the gate and check the page agrees with what it did."""
        bad_ids = []
        for r in rules():
            page = OUT / f"{r['id']}.md"
            if not page.is_file():
                bad_ids.append(f"{r['id']}: no page")
                continue
            argv = [p for p in r["run"]]
            case = next(
                (c for c in r.get("cases", []) if c.get("args") and not c.get("live")),
                None,
            )
            if case is None:
                continue
            real = subprocess.run(
                [*argv, *case["args"]], cwd=ROOT, capture_output=True, text=True
            )
            if str(real.returncode) not in page.read_text():
                bad_ids.append(f"{r['id']}: page does not carry exit {real.returncode}")
        assert not bad_ids, "pages out of step with their gates:\n" + "\n".join(bad_ids)

    def test_a_refusing_gate_shows_its_own_refusal(self):
        """A page must carry the gate's stderr, not the word 'refuse' by itself."""
        shown = 0
        for r in rules():
            page = OUT / f"{r['id']}.md"
            if not page.is_file():
                continue
            case = next(
                (c for c in r.get("cases", []) if c.get("expect") == "refuse"), None
            )
            if case is None or not case.get("args"):
                continue
            real = subprocess.run(
                [*r["run"], *case["args"]], cwd=ROOT, capture_output=True, text=True
            )
            if real.returncode == 0:
                continue
            text = page.read_text()
            # the first non-empty line the gate printed must be on the page
            first = next(
                (ln for ln in (real.stdout + real.stderr).splitlines() if ln.strip()),
                "",
            )
            if first and first.strip() in text:
                shown += 1
        assert shown >= 5, (
            f"only {shown} page(s) carry their gate's actual refusal output; a page that says "
            "'refuse' without the gate's own words proves nothing"
        )


class TestCheckIsIdempotent:
    def test_two_renders_are_byte_identical(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        assert run_gen("--out", str(a)).returncode == 0
        assert run_gen("--out", str(b)).returncode == 0
        fa = {p.name: p.read_bytes() for p in a.glob("*.md")}
        fb = {p.name: p.read_bytes() for p in b.glob("*.md")}
        assert fa == fb, "two renders of one registry differ"

    def test_check_passes_when_pages_match(self):
        proc = run_gen("--out", str(OUT), "--check")
        assert proc.returncode == 0, f"--check refused a current tree:\n{proc.stdout}"

    def test_check_fails_when_a_page_is_edited_by_hand(self, tmp_path):
        import shutil

        edited = tmp_path / "gates"
        shutil.copytree(OUT, edited)
        victim = next(p for p in edited.glob("*.md") if p.stem != "index")
        victim.write_text(victim.read_text() + "\na hand edit\n")
        proc = run_gen("--out", str(edited), "--check")
        assert proc.returncode != 0, "a hand-edited page passed --check"


class TestBlindIsNotAPass:
    def test_blind_when_a_case_cannot_run(self, tmp_path):
        """A rule whose gate is missing must render a BLIND page that names it."""
        one = tmp_path / "rules.yaml"
        one.write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "rules": [
                        {
                            "id": "no-such-gate",
                            "label": "missing",
                            "statement": "a gate that is not there",
                            "law": "test",
                            "planes": ["ci"],
                            "run": ["python3", "bin/definitely-not-a-real-gate"],
                            "fixtures": {
                                "must_fail": "tests/fixtures/x",
                                "must_pass": "tests/fixtures/x",
                            },
                            "cases": [
                                {"expect": "refuse", "args": ["tests/fixtures/x"]},
                                {"expect": "pass", "args": ["tests/fixtures/x"]},
                            ],
                            "ok": "never",
                            "fail": "always",
                        }
                    ],
                }
            )
        )
        out = tmp_path / "pages"
        proc = run_gen("--rules", str(one), "--out", str(out))
        page = out / "no-such-gate.md"
        assert page.is_file(), (
            f"no page rendered for a rule with a missing gate\n{proc.stdout}"
        )
        text = page.read_text()
        assert "BLIND" in text, "a rule whose gate cannot run must say BLIND"
        assert "definitely-not-a-real-gate" in text, (
            "the BLIND page must name what is missing"
        )


class TestTheIndexAndTheNav:
    def test_the_index_lists_every_gate(self):
        idx = OUT / "index.md"
        assert idx.is_file(), "no docs/gates/index.md"
        text = idx.read_text()
        missing = [r["id"] for r in rules() if r["id"] not in text]
        assert not missing, f"the index omits {missing[:5]}"

    def test_every_index_row_links_a_page_that_exists(self):
        import re

        text = (OUT / "index.md").read_text()
        links = re.findall(r"\]\(([^)]+\.md)\)", text)
        assert links, "the index links no pages"
        broken = [ln for ln in links if not (OUT / ln).is_file()]
        assert not broken, f"the index links pages that do not exist: {broken[:5]}"

    def test_pages_are_in_the_nav(self):
        nav = NAV.read_text()
        not_in_nav = [r["id"] for r in rules() if f"gates/{r['id']}.md" not in nav]
        assert not not_in_nav, f"generated pages not in the nav: {not_in_nav[:5]}"
