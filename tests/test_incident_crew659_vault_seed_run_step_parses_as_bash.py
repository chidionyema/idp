"""crew#659: the vault-seed seed step must parse as bash before it can mint anything.

idp#938 spliced the science block in before the hermes block's closing `fi`. Every YAML test
passed (the document was valid, the last line was still `rm -f "$ESTATE_ENV_FILE"`), and the first
dispatch died with `line 104: syntax error: unexpected end of file` (run 33293566905). A shell
step that is only ever graded as YAML is a step nobody has run. This test hands every `run:` in
the workflow to `bash -n`.
"""

from __future__ import annotations

import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "vault-seed.yml"


def _run_steps() -> list[tuple[str, str]]:
    doc = yaml.safe_load(WORKFLOW.read_text())
    out = []
    for job, spec in doc["jobs"].items():
        for i, step in enumerate(spec.get("steps", [])):
            if step.get("run"):
                out.append((f"{job}[{i}] {step.get('name', '')}", step["run"]))
    return out


def test_every_run_step_in_vault_seed_parses_as_bash():
    steps = _run_steps()
    assert steps, "no run steps found"
    for name, body in steps:
        r = subprocess.run(["bash", "-n"], input=body, capture_output=True, text=True)
        assert r.returncode == 0, f"{name}: {r.stderr.strip()}"


def test_every_entry_block_closes_before_the_next_opens():
    body = next(b for n, b in _run_steps() if "ENTRY" in b)
    depth = 0
    for ln, line in enumerate(body.splitlines(), 1):
        s = line.strip()
        if s.startswith("if "):
            if s.startswith('if [ "$ENTRY"'):
                assert depth == 0, (
                    f"line {ln}: an entry block opens inside another block"
                )
            depth += 1
        elif s == "fi":
            depth -= 1
    assert depth == 0
