"""idp#8342: a tool the estate runs must not write bytes the estate's own gate refuses.

Class FC_NON_ASCII_TOOL_OUTPUT. growmos journal wrote '### <ts> <U+00B7> <author>', and
.githooks/pre-push Layer 1c refuses non-ASCII added lines, so every journal commit from every agent
was refused. bin/growmos-pin patches the pinned source and proves the class closed by running the
tool; agent-sandbox.yml boots every sandbox agent with that proved source on PATH, and the App
token that reads the private fork never reaches the agent job.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "bin" / "growmos-pin"
DOT = "\u00b7"

# A stand-in growmos with the real journal line and a CLI that runs it.
_STORE = (
    "from datetime import datetime, timezone\n"
    "from pathlib import Path\n"
    "def journal(text, author='agent'):\n"
    "    now_iso = lambda: datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')\n"
    '    entry = f"\\n### {now_iso()} ' + DOT + ' {author}\\n\\n{text.strip()}\\n"\n'
    "    Path('.growmos').mkdir(exist_ok=True)\n"
    "    with open('.growmos/journal.md', 'a', encoding='utf-8') as f:\n"
    "        f.write(entry)\n"
)
_MAIN = (
    "import sys\n"
    "from growmos.store import journal\n"
    "if sys.argv[1] == 'journal':\n"
    "    journal(sys.argv[2])\n"
)


def _growmos(tmp: Path, store: str) -> Path:
    pkg = tmp / "gm" / "src" / "growmos"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text(_MAIN)
    (pkg / "store.py").write_text(store, encoding="utf-8")
    return tmp / "gm"


def _pin(src: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PIN), str(src)], capture_output=True, text=True, timeout=60
    )


def test_the_pin_turns_the_journal_heading_ascii_and_proves_it(tmp_path):
    src = _growmos(tmp_path, _STORE)
    r = _pin(src)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (src / "src/growmos/store.py").read_text(encoding="utf-8").isascii()


def test_a_tool_that_still_writes_non_ascii_is_refused(tmp_path):
    # The same output written another way: the patch cannot match it, the proof must still refuse.
    other = _STORE.replace(" " + DOT + " ", " {chr(0xb7)} ")
    r = _pin(_growmos(tmp_path, other))
    assert r.returncode == 1 and "FC_NON_ASCII_TOOL_OUTPUT" in r.stdout, r.stdout


def test_the_pin_itself_is_ascii():
    assert PIN.read_bytes().isascii()


def test_every_sandbox_agent_boots_with_the_proved_growmos_and_no_token():
    flow = yaml.safe_load((ROOT / ".github/workflows/agent-sandbox.yml").read_text())
    tools, agent = flow["jobs"]["tools"], flow["jobs"]["agent"]
    sha = tools["env"]["GROWMOS_SHA"]
    assert len(sha) == 40 and all(c in "0123456789abcdef" for c in sha), (
        "pin a full commit"
    )
    tools_run = "\n".join(s.get("run", "") for s in tools["steps"])
    assert "bin/growmos-pin" in tools_run and "rm -rf growmos/.git" in tools_run
    assert tools["if"] == agent["if"], (
        "the token is minted only for a run that starts an agent"
    )
    assert agent["needs"] == "tools"
    agent_text = yaml.safe_dump(agent)
    assert "SEED_GITHUB_APP" not in agent_text and "steps.app" not in agent_text
    names = [s.get("name", "") for s in agent["steps"]]
    assert names.index("Put the pinned growmos on PATH") < names.index(
        "Run the agent (its output goes to a file, never to this public log)"
    )
