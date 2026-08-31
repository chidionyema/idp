"""crew#764 (R66): a blank photograph is never evidence.

Login-drill run 33427731536 handed the founder a 4 KB blank grey rectangle as its
photograph: the shot fired before the page painted. The camera now waits until the
page's words exist AND stop growing, and the evidence stage turns the drill red on a
page that never answers or never paints. These tests pin that shape in the drill's
source and in its workflow, so no edit can quietly bring the blank-photo class back.
Each assertion fails on the pre-change file (proved both ways on idp#1084).
"""

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DRILL = (ROOT / "bin" / "idp-login-drill").read_text()
WORKFLOW = (ROOT / ".github" / "workflows" / "login-drill.yml").read_text()


def driver() -> str:
    m = re.search(r"<<'PYDRIVER'\n(.*?)\nPYDRIVER", DRILL, re.S)
    assert m, (
        "bin/idp-login-drill no longer embeds its python driver as a PYDRIVER heredoc"
    )
    return m.group(1)


def test_every_photograph_waits_for_paint_to_settle():
    src = driver()
    body = re.search(r"def painted_words\(pg\):\n(.*?)\n\n", src, re.S)
    assert body, "the painted_words shutter condition is gone from the drill"
    assert "w == prev" in body.group(1), (
        "painted_words no longer requires two consecutive equal readings: a growing page "
        "would be photographed mid-paint, the exact defect of run 33433191136"
    )
    shot_block = src[src.index('os.environ.get("DRILL_SHOT")') :]
    first_call = min(shot_block.index("painted_words("), len(shot_block))
    first_shot = shot_block.index("page.screenshot(")
    assert first_call < first_shot, (
        "the home photograph fires before painted_words: run 33427731536 shipped a blank "
        "grey rectangle exactly this way"
    )


def test_an_unpainted_or_unloaded_page_turns_the_drill_red():
    src = driver()
    stage = re.search(r"DRILL_EVIDENCE_PATHS.*?ctx\.close\(\)", src, re.S)
    assert stage, "the evidence stage is gone from the drill"
    reds = re.findall(r'fail\("evidence",', stage.group(0))
    assert len(reds) >= 3, (
        "the evidence stage no longer fails on all three red roads (never loaded, bad "
        "status, never painted); a silent camera is the silent-green class in picture form"
    )


def test_the_workflow_carries_the_paths_in_and_the_pictures_out():
    doc = yaml.safe_load(WORKFLOW)
    inputs = doc[True]["workflow_dispatch"]["inputs"]
    assert "evidence_paths" in inputs, "the evidence_paths dispatch input is gone"
    drill_env = next(
        s for s in doc["jobs"]["login-drill"]["steps"] if s.get("id") == "drill"
    )["env"]
    assert drill_env.get("DRILL_EVIDENCE_PATHS") == "${{ inputs.evidence_paths }}", (
        "the dispatch input no longer reaches the drill as DRILL_EVIDENCE_PATHS"
    )
    assert "DRILL_SHOT_DIR" in drill_env, "the drill has nowhere to put the pictures"
    upload = next(
        s
        for s in doc["jobs"]["login-drill"]["steps"]
        if "upload-artifact" in str(s.get("uses", ""))
    )
    assert "shots" in upload["with"]["path"], (
        "the shots directory is no longer uploaded: the pictures would be taken and thrown away"
    )
