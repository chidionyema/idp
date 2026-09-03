"""crew#612 CP8: dev speak never crosses the boundary into a page a person reads.

Founder, 2026-08-31: "ur jargon has filtered through the estate and no one can understand anything
any more" / "all docs, all sites jargon free" / "it needs enterprise solution" / "dev speak should
never cross boundaries".

The grader is Vale (the prose linter GitLab, Microsoft and Red Hat run on their own documentation)
with the estate's boundary in `.vale.ini` and `styles/Estate/`. Markdown surfaces are graded by
`.github/workflows/prose.yml` directly. The YAML surfaces a person reads through Backstage hold
machine fields too (keys, URLs, template expressions), so this test extracts exactly the fields a
person sees and grades those with the same configuration. The fields listed here ARE the boundary:
a new human-read field is added here or it is not graded.

Mistake class: guard-watched-one-file (the old plain-English guard graded one catalogue file while
the same jargon reached 23 buttons, 12 drill rows and every docs page).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
BUTTONS = ROOT / "backstage" / "templates" / "founder-actions"
FOUNDER_CATALOG = ROOT / "backstage" / "founder" / "catalog-info.yaml"
DRILLS = ROOT / "drills" / "catalogue.yaml"
VALE_INI = ROOT / ".vale.ini"
PROSE = ROOT / ".github" / "workflows" / "prose.yml"
GENERATOR = ROOT / "bin" / "idp-portal-buttons"


def _vale(text: str) -> list[str]:
    """Grade prose with the estate's Vale configuration; return the error-level findings."""
    if shutil.which("vale") is None:
        pytest.skip(
            "vale is not installed here; .github/workflows/prose.yml runs this test with it"
        )
    r = subprocess.run(
        ["vale", "--ext=.md", "--output=JSON", "--no-exit", "--minAlertLevel=error"],
        input=text,
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout or "{}")
    return [
        f"{a['Check']}: {a['Message']}  <- {a['Match']!r}"
        for alerts in doc.values()
        for a in alerts
    ]


def _button_fields(path: Path) -> list[str]:
    d = yaml.safe_load(path.read_text())
    out = [d["metadata"].get("title", ""), d["metadata"].get("description", "")]
    for step in d["spec"].get("parameters") or []:
        out += [step.get("title", ""), step.get("description", "")]
        for prop in (step.get("properties") or {}).values():
            out += [prop.get("title", ""), prop.get("description", "")]
    for link in (d["spec"].get("output") or {}).get("links") or []:
        out.append(link.get("title", ""))
    return [x for x in out if x]


def _catalog_fields(path: Path) -> list[str]:
    out = []
    for d in yaml.safe_load_all(path.read_text()):
        if not d:
            continue
        m = d["metadata"]
        out += [m.get("title", ""), m.get("description", "")]
        out += [link.get("title", "") for link in m.get("links") or []]
    return [x for x in out if x]


def _drill_fields(path: Path) -> list[str]:
    rows = yaml.safe_load(path.read_text())["drills"]
    return [str(r.get("proves", "")) for r in rows if r.get("proves")]


def test_the_boundary_refuses_a_ticket_code_a_layer_label_and_dev_speak() -> None:
    """Negative control: the grader is awake. A sentence with all three classes is refused."""
    findings = _vale("The prover checks crew#631 at L1 and reconciles the HelmRelease.")
    checks = {f.split(":")[0] for f in findings}
    assert {"Estate.DevSpeak", "Estate.TicketCodes", "Estate.Layers"} <= checks, (
        findings
    )


def test_the_configuration_and_the_gate_are_pinned() -> None:
    ini = VALE_INI.read_text()
    assert "StylesPath = styles" in ini
    assert re.search(r"BasedOnStyles = .*\bEstate\b", ini), (
        "the Estate boundary is not applied"
    )
    for style in ("TicketCodes", "DevSpeak", "Layers"):
        assert (ROOT / "styles" / "Estate" / f"{style}.yml").is_file(), style
    wf = yaml.safe_load(PROSE.read_text())
    steps = wf["jobs"]["plain-english"]["steps"]
    uses = [s.get("uses", "") for s in steps]
    assert any(
        u.startswith("errata-ai/vale-action@") and re.search(r"@[0-9a-f]{40}", u)
        for u in uses
    ), uses
    runs = "\n".join(s.get("run", "") for s in steps)
    assert "vale --minAlertLevel=error README.md" in runs
    assert Path(__file__).name in runs, "prose.yml does not run this test"
    assert "GITHUB_STEP_SUMMARY" in runs, (
        "the docs-tree burn-down count is not on the run summary"
    )


def test_the_button_generator_refuses_a_workflow_without_plain_english_lines() -> None:
    """The buttons are generated; the plain words are written at the source or the generator stops."""
    src = GENERATOR.read_text()
    assert "# button:" in src and "# founder:" in src
    assert "SystemExit" in src.split("def _founder_lines")[1].split("def ")[0]
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        text = wf.read_text()
        if "workflow_dispatch" not in text:
            continue
        head = text[:600]
        assert "# button:" in head and "# founder:" in head, (
            f"{wf.name} has no plain-English header"
        )
