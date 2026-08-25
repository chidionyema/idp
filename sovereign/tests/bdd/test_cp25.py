"""cp25 acceptance: Vision to repo -- a photo becomes a committed markdown file and one receipt

Owner: W4. The vision model is a true external boundary (a paid call), so
it is the one thing stubbed here, through the `vision=` seam the pipeline
exposes. The git repository, the receipt chain and the presence gate run
for real against the temporary estate.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sovereign.intake import from_phone
from sovereign.intake.presence import GhostPresence

from .conftest import REPO_ROOT, MessageSink

scenarios("features/sovereign-bus/cp25_vision_to_repo.feature")

# A PNG header is enough: the stub never decodes it, and a real model call
# never happens in a test.
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
_EXTRACTED_TEXT = "The core argument is that governance must precede autonomy."


@pytest.fixture
def software_trust(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the receipt key out of the founder's Keychain: the trust anchor
    reports the software backend, so the key is a 0600 file under the
    temporary estate."""
    from sovereign.trust import anchor

    monkeypatch.setattr(anchor, "_detect_backend", lambda: "software_key")


@pytest.fixture
def vision_stub(context: dict[str, Any]):
    """The vision seam. Records what it was asked and answers with the
    strict JSON the prompt demands."""

    def _call(model: str, messages: list[dict[str, Any]]) -> str:
        context["vision_model_used"] = model
        context["vision_messages"] = messages
        return json.dumps({
            "markdown": f"## Core arguments\n\n{_EXTRACTED_TEXT}",
            "slug": "Governance Before Autonomy",
            "tags": ["ml", "governance", "agents"],
            "title": "Governance before autonomy",
        })

    return _call


@given(parsers.parse('the founder sends a photo with caption "{caption}"'))
def _photo(caption: str, context: dict[str, Any]) -> None:
    context["caption"] = caption
    context["image"] = _PNG
    context["chat_id"] = "telegram-thread-1"


@when("hermes routes it to the vision model through LiteLLM with the strict JSON prompt")
def _route(
    context: dict[str, Any],
    scratch_repo: Path,
    receipts_path: Path,
    software_trust: None,
    vision_stub,
    messages: MessageSink,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SB_VISION_MODEL", "estate-vision-alias")
    presence = GhostPresence("converse")  # the request came from a Converse thread
    result = from_phone(
        context["image"], context["caption"], scratch_repo, context["chat_id"],
        reply=messages.send, presence=presence, vision=vision_stub,
    )
    context["result"] = result
    context["presence"] = presence
    assert context["vision_model_used"] == "estate-vision-alias"
    system = context["vision_messages"][0]
    assert system["role"] == "system" and "JSON" in system["content"]


@then("a file docs/<slug>.md is committed in the knowledge repo")
def _committed(context: dict[str, Any], scratch_repo: Path) -> None:
    result = context["result"]
    assert result.relative_path.startswith("docs/") and result.relative_path.endswith(".md")
    assert result.path.exists()
    assert _EXTRACTED_TEXT in result.path.read_text()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=scratch_repo, capture_output=True, text=True, check=True)
    assert head.stdout.strip() == result.commit
    shown = subprocess.run(
        ["git", "show", "--stat", "--format=%s", "HEAD"], cwd=scratch_repo, capture_output=True, text=True, check=True
    ).stdout
    assert result.relative_path in shown
    clean = subprocess.run(["git", "status", "--porcelain"], cwd=scratch_repo, capture_output=True, text=True, check=True)
    assert clean.stdout == "", f"working tree not clean after intake: {clean.stdout!r}"


@then("the reply in the thread is exactly one receipt line")
def _one_line(context: dict[str, Any], messages: MessageSink, receipts_path: Path) -> None:
    from sovereign.engine import receipts

    msg = messages.assert_exactly_one()
    result = context["result"]
    assert msg.channel == context["chat_id"]
    assert msg.text == result.receipt_line
    assert "\n" not in msg.text
    assert msg.text.startswith("[✓] DOC_COMMIT | file:docs/")
    assert f"hash:{result.commit[:8]}" in msg.text
    assert "tags:#ml,#governance,#agents" in msg.text
    # The line is in the signed chain, and the chain verifies.
    rows = receipts.read_all(receipts_path)
    assert [r["text"] for r in rows] == [msg.text]
    assert rows[0]["kind"] == "doc_commit" and rows[0]["commit"] == result.commit
    assert receipts.verify(receipts_path)["ok"] is True
    # R4: intake left presence where it found it and did not move it to Converse itself.
    assert result.presence_before == result.presence_after == context["presence"].current()


@then("no extracted text is echoed to the chat")
def _no_echo(context: dict[str, Any], messages: MessageSink) -> None:
    result = context["result"]
    for m in messages.sent:
        assert _EXTRACTED_TEXT not in m.text
        assert result.extraction.markdown not in m.text


@when(parsers.parse('I run "{command}"'))
def _run(command: str, context: dict[str, Any]) -> None:
    """The feature names sovereign/vision; this lane's package is
    sovereign/intake. The same grep runs over both, and over the CLI that
    registers the subcommand, so the assertion is stricter than the text."""
    argv = command.split()
    pattern = " ".join(argv[2:-1]).strip("'")
    outputs = []
    for target in (argv[-1], "sovereign/intake", "sovereign/cli.py"):
        proc = subprocess.run(
            ["grep", "-rnI", "--exclude-dir=__pycache__", pattern, target], cwd=REPO_ROOT, capture_output=True, text=True
        )
        outputs.append(proc.stdout)
    context["grep_output"] = "".join(outputs)


@then("the output is empty")
def _empty(context: dict[str, Any]) -> None:
    assert context["grep_output"] == "", context["grep_output"]


@then("the model alias comes from SB_VISION_MODEL")
def _alias_from_env(monkeypatch: pytest.MonkeyPatch, config) -> None:
    from sovereign.intake import vision

    monkeypatch.setenv("SB_VISION_MODEL", "alias-from-env")
    assert vision.vision_model() == "alias-from-env"
    monkeypatch.delenv("SB_VISION_MODEL")
    # Unset, it falls back to the config table's model.vision -- still an alias.
    assert vision.vision_model() == config.get("model.vision").value
    assert config.KEYS["intake.vision_model"].env == "SB_VISION_MODEL"
