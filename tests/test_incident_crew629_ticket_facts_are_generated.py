"""crew#629 CP1, founder 2026-08-29: "should every ticket auto populate crucial infra details?"

A session spent eight attempts on idp#800 re-finding which admission policies reached one Flux
row. `bin/idp-ticket-facts <row>` prints those facts from git in six sections; a ticket carries
the block, a session reads it. Proved on the `llm` row (the acceptance line on crew#629) and on
a row that does not exist (the tool says so and exits 1, never an empty page).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin" / "idp-ticket-facts"
SECTIONS = (
    "## Flux rows",
    "## Admission policies that apply",
    "## On/off keys",
    "## Doors and login",
    "## Drills that grade it",
    "## Standards row",
)


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args], capture_output=True, text=True, check=False
    )


def test_llm_prints_all_six_sections_non_empty():
    r = run("llm", "--no-live")
    assert r.returncode == 0, r.stderr
    for head in SECTIONS:
        assert head in r.stdout, head
        body = r.stdout.split(head, 1)[1].split("\n## ", 1)[0]
        if head == "## Standards row" and "BLIND" in body:
            # The standards page lives in the crew repo beside the main checkout; a CI runner
            # has no crew checkout, and the honest answer there is BLIND naming the page, not
            # a green section nobody could read (crew#629 CP1; silent green is the defect).
            assert "STANDARDS.md" in body, body
            continue
        assert "BLIND" not in body, f"{head} is blind:\n{body}"
    assert "capacity-requests-need-proof" in r.stdout
    assert "Deployment/litellm spec.replicas" in r.stdout
    assert "login-drill" in r.stdout  # founder 2026-08-29: trace-drill removed; the login drill grades llm.<zone>/ui/


def test_an_unknown_row_is_blind_and_red():
    r = run("no-such-row-anywhere", "--no-live")
    assert r.returncode == 1
    assert "BLIND: no Kustomization named no-such-row-anywhere" in r.stdout


def test_the_standards_row_is_read_when_the_page_is_named(tmp_path):
    page = tmp_path / "STANDARDS.md"
    page.write_text(
        "| Layer | Choice | State | Evidence |\n|---|---|---|---|\n"
        "| LLM providers | LiteLLM proxy at idp platform/llm, llm.<zone> | live | measured |\n"
    )
    env = dict(os.environ, ESTATE_STANDARDS_MD=str(page))
    r = subprocess.run(
        [sys.executable, str(TOOL), "llm", "--no-live"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    body = r.stdout.split("## Standards row", 1)[1]
    assert "LLM providers" in body, body
