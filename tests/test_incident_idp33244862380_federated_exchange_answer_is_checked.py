"""Incident, oke-check run 33244862380 (2026-08-29): bin/idp-bootstrap-tailscale printed
`ok federated OIDC token exchanged` before reading Tailscale's answer, then blamed the seed
(`vault entry tailscale-seed does not exchange`). The exchange had been refused and the reason was
never shown. Silent green is the defect class: the answer is checked before the word ok."""
import re
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "idp-bootstrap-tailscale"


def _federated_block() -> str:
    text = SCRIPT.read_text()
    start = text.index('"$API/api/v2/oauth/token-exchange"')
    end = text.index("say ok federated", start)
    return text[start:end]


def test_the_exchange_answer_is_checked_before_ok():
    block = _federated_block()
    assert "jq -e '.access_token'" in block, "the token-exchange answer must be checked before `ok federated`"
    assert "fail federated" in block


def test_the_refusal_names_tailscales_message_and_the_expected_subject():
    block = _federated_block()
    assert ".message // .error" in block, "Tailscale's refusal message is what the operator reads next"
    assert "repo:$GITHUB_REPOSITORY:ref:$GITHUB_REF" in block


def test_the_token_is_never_printed():
    text = SCRIPT.read_text()
    for line in text.splitlines():
        for m in re.finditer(r'(?:say|fail) +\S+ +"([^"]*)"', line):
            assert not re.search(r"\$seed_tok|\$new_sec|\$tok\b", m.group(1)), line


def test_the_seed_failure_names_the_reason_too():
    text = SCRIPT.read_text()
    assert re.search(r'fail seed "the seed does not exchange for a token: \$\(jq -r', text)
