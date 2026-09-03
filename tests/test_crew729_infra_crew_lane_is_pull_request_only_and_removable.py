"""crew#729 step 2: the infra crew's GitHub identity is one lane on the one estate App, and the
lane is its own kill switch.

The lane `infra-crew` in platform/github-app/lanes.json can open and update pull requests and
nothing more: no workflows, no actions write, no administration, no secrets. `bin/idp-github-app
token infra-crew` narrows the installation token to exactly that set.

The kill switch is one git change: delete the lane. `bin/idp-github-app token <lane>` reads
lanes.json before it reads the vault, and a lane the file does not hold is refused with a
plain-English line and a non-zero exit, so no token is minted and no secret is touched. This
test proves both halves without a network, a vault or a credential: it runs the script against a
copy of lanes.json with the lane removed.
"""

import json
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-github-app"
LANES = ROOT / "platform" / "github-app" / "lanes.json"
LANE = "infra-crew"

# What a pull-request-only identity may hold, and nothing else (crew#729).
ALLOWED = {
    "metadata": "read",
    "contents": "write",
    "pull_requests": "write",
    "issues": "write",
    "actions": "read",
    "checks": "read",
}
NEVER = {
    "workflows",
    "administration",
    "secrets",
    "environments",
    "organization_administration",
}


def _lanes() -> dict:
    return json.loads(LANES.read_text())


def test_the_lane_exists_and_is_pull_request_only():
    lane = _lanes().get(LANE)
    assert lane is not None, f"{LANE} is not a lane in {LANES}"
    assert lane == ALLOWED, (
        f"{LANE} must hold exactly the pull-request-only set, got {lane}"
    )
    assert not (set(lane) & NEVER)
    assert lane.get("actions") != "write" and "workflows" not in lane


def _token_with_lanes(
    lanes_file: pathlib.Path, tmp_path: pathlib.Path
) -> subprocess.CompletedProcess:
    """Run `idp-github-app token infra-crew` against a copy of the repo that holds `lanes_file`.

    The script resolves lanes.json relative to its own location, so the copy carries bin/ and
    platform/github-app/ only. Nothing else is needed: the lane check runs before the vault read.
    """
    fake = tmp_path / "idp"
    (fake / "bin").mkdir(parents=True)
    (fake / "platform" / "github-app").mkdir(parents=True)
    shutil.copy(SCRIPT, fake / "bin" / "idp-github-app")
    shutil.copy(lanes_file, fake / "platform" / "github-app" / "lanes.json")
    # No vault, no age key, no cloud: if the script gets past the lane check it must fail loudly
    # on the vault read, never mint anything. HOME is empty so no real key file is found.
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
    }
    return subprocess.run(
        ["bash", str(fake / "bin" / "idp-github-app"), "token", LANE],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_removing_the_lane_from_lanes_json_refuses_the_token_before_any_secret_is_read(
    tmp_path,
):
    lanes = _lanes()
    del lanes[LANE]
    killed = tmp_path / "lanes.json"
    killed.write_text(json.dumps(lanes, indent=2))
    r = _token_with_lanes(killed, tmp_path)
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert f"REFUSED: no lane '{LANE}'" in r.stdout, r.stdout + r.stderr
    assert "ghs_" not in r.stdout + r.stderr
    assert "BLIND" not in r.stdout, (
        "the refusal must come from the lane check, never the vault"
    )


def test_the_lane_check_runs_before_the_vault_read():
    """The kill switch is only a kill switch if no secret is read first: in the `token` branch
    the lanes.json lookup precedes the `idp-cloud secret get` line."""
    src = SCRIPT.read_text()
    token_branch = src.split("\ntoken)\n", 1)[1]
    assert token_branch.index("lanes.json") < token_branch.index("secret get")
    assert "REFUSED: no lane" in token_branch
