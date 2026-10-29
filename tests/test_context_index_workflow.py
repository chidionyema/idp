"""The context-index workflow reads the engine's answer through its MCP envelope.

Measured 2026-10-29: every context-index run since ~00:54Z failed "the engine answered with no
working set" although the index built (93,819 nodes), because the probe and the manifest step read
`working_set` off the envelope itself. The broker unwraps it (unwrap_engine_envelope); the workflow
must too, or a good answer reads as an empty one.
"""

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/context-index.yml"


def test_every_working_set_read_unwraps_the_envelope_first():
    text = WORKFLOW.read_text()
    assert text.count('.get("working_set")') == 2
    assert text.count('isinstance(payload.get("content"), list)') == 1
    assert text.count('isinstance(context.get("content"), list)') == 1
    assert text.index('isinstance(payload.get("content"), list)') < text.index(
        'working = payload.get("working_set")'
    )
    assert text.index('isinstance(context.get("content"), list)') < text.index(
        'context.get("working_set")'
    )


def test_the_artifact_is_pushed_from_a_writable_parent():
    """flux stages its tarball beside --path; pushing /data stages in / and is refused."""
    text = WORKFLOW.read_text()
    push = text.index("| flux push artifact")  # the command, not the uses: comment
    assert text.index('sudo mv "${DATA}" "${STAGE}/data"') < push
    assert '--path="/data"' not in text


def test_the_registry_login_carries_its_credentials():
    """A bare docker/login-action fails "Username and password required" (run 40853469951), which
    skips the signature step: the index was published but never signed."""
    text = WORKFLOW.read_text()
    step = text[text.index("docker/login-action@") :]
    block = step[: step.index("- uses: imjasonh")]
    assert "registry: ghcr.io" in block
    assert "password: ${{ secrets.GITHUB_TOKEN }}" in block
