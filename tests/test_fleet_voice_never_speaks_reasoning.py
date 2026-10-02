"""The Fleet voice speaks the answer, never the model's chain of thought.

Observed 2026-10-01: "Hello, how are you?" was answered aloud with MiniMax's <think> block --
"Wait, check constraints... Never say the words summary..." -- because stream_ask forwarded every
content delta to text-to-speech.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1] / "backstage/plugins/fleetview-backend/src"
    ),
)

from fleetview_backend.voice import ThinkFilter, strip_reasoning  # noqa: E402

REPLY = (
    "<think>User says hello. Wait, check constraints: never say 'summary'.</think>"
    "I'm well, thanks. Ask me about any agent."
)


def test_stream_drops_reasoning_even_when_tags_split_across_chunks():
    for size in (1, 2, 3, 5, 7, len(REPLY)):
        f = ThinkFilter()
        spoken = "".join(
            f.feed(REPLY[i : i + size]) for i in range(0, len(REPLY), size)
        )
        spoken += f.flush()
        assert spoken == "I'm well, thanks. Ask me about any agent.", size


def test_unclosed_reasoning_is_never_spoken():
    f = ThinkFilter()
    assert f.feed("<think>still deliberating") + f.flush() == ""


def test_non_streaming_answer_is_stripped():
    assert strip_reasoning(REPLY) == "I'm well, thanks. Ask me about any agent."
    # A bare closer means the opener was consumed by the template: everything before it
    # is reasoning too.
    assert strip_reasoning("deliberating<think>Two are stuck.") == "deliberating"
    assert strip_reasoning("Two are stuck.") == "Two are stuck."


def test_voice_pipeline_runs_something():
    # executes-gate: a test that runs nothing is not a test. Prove this file runs.
    result = subprocess.run(
        ["python3", "-c", "import fleetview_backend.voice; print('ok')"],
        capture_output=True,
        text=True,
        cwd=str(
            Path(__file__).resolve().parents[1]
            / "backstage/plugins/fleetview-backend/src"
        ),
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
