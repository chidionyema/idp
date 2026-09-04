"""What the proving gate does, graded by doing it (decision 0020, part B).

Every test here drives `prove()` against a stand-in vendor and grades the request that
went out or the answer that came back. None of them read the source file or assert that a
line of prose is present, because a test that reads our own files back only ever proves we
wrote what we wrote.
"""

import json
import re
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "platform"))

from warden import prove as warden  # noqa: E402

SENTINEL = "sk-0123456789abcdef0123456789abcdef"


def credential_for(vendor):
    """Whatever fields this vendor's own row asks for, filled with the sentinel."""
    fields = warden.required_fields(warden.vendor_config(vendor))
    if fields == ["key"]:
        return SENTINEL
    return {name: f"{SENTINEL}-{name}" for name in fields}


class FakeResponse:
    def __init__(self, status_code=200, text="{}"):
        self.status_code = status_code
        self.text = text


class Transport:
    """Records what the module actually put on the wire."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, url, headers=None, timeout=None, json=None, data=None):
        self.calls.append(
            {"url": url, "headers": headers or {}, "json": json, "data": data}
        )
        answer = self.answers.pop(0) if self.answers else FakeResponse()
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def transport(monkeypatch):
    def install(*answers, method="get"):
        sender = Transport(*answers)
        monkeypatch.setattr(warden.requests, method, sender)
        return sender

    return install


def test_the_key_reaches_the_vendor_in_the_header_the_row_names(transport):
    sender = transport(FakeResponse(200))
    warden.prove("deepseek", SENTINEL)
    call = sender.calls[0]
    assert call["headers"]["Authorization"] == f"Bearer {SENTINEL}"
    assert SENTINEL not in call["url"]


def test_a_vendor_with_several_bases_is_still_authorised_at_each(transport):
    """A Kimi key is good; the first base simply does not answer for it."""
    sender = transport(FakeResponse(401, '{"error":"unauthorized"}'), FakeResponse(200))
    proof = warden.prove("kimi", SENTINEL)
    assert proof.status_code == 200
    assert len(sender.calls) == 2
    assert all(
        call["headers"].get("Authorization") == f"Bearer {SENTINEL}"
        for call in sender.calls
    )
    assert sender.calls[0]["url"] != sender.calls[1]["url"]


def test_a_post_body_from_the_registry_goes_out_as_an_object(transport):
    sender = transport(FakeResponse(200), method="post")
    warden.prove("exa", SENTINEL)
    sent = sender.calls[0]
    assert sent["json"] == json.loads(warden.vendor_config("exa")["verify"]["body"])
    assert sent["data"] is None


def test_a_network_failure_never_carries_the_key_out_of_the_module(transport):
    """Gemini's verify URL holds the key, so the exception text holds it too."""
    url = warden.build_request(warden.vendor_config("gemini"), SENTINEL)["url"]
    assert SENTINEL in url, (
        "this test is only meaningful while the key rides in the URL"
    )
    transport(requests.ConnectionError(f"Max retries exceeded with url: {url}"))

    with pytest.raises(warden.ProofFailed) as raised:
        warden.prove("gemini", SENTINEL)

    assert SENTINEL not in str(raised.value)
    assert SENTINEL not in raised.value.vendor_message
    assert warden.REDACTED in raised.value.vendor_message


def test_a_vendor_that_echoes_the_key_back_does_not_get_it_logged(transport):
    transport(FakeResponse(401, f'{{"error":"key {SENTINEL} is revoked"}}'))
    with pytest.raises(warden.ProofFailed) as raised:
        warden.prove("deepseek", SENTINEL)
    assert SENTINEL not in raised.value.vendor_message
    assert "revoked" in raised.value.vendor_message


def test_a_refusal_reports_the_vendors_own_status_and_words(transport):
    transport(FakeResponse(402, '{"error":"insufficient balance"}'))
    with pytest.raises(warden.ProofFailed) as raised:
        warden.prove("deepseek", SENTINEL)
    assert raised.value.status_code == 402
    assert "insufficient balance" in raised.value.vendor_message


def test_only_a_2xx_returns_a_proof(transport):
    for status in (301, 400, 401, 403, 500):
        transport(FakeResponse(status, "no"))
        with pytest.raises(warden.ProofFailed):
            warden.prove("deepseek", SENTINEL)


def test_a_body_the_row_calls_a_refusal_fails_even_on_a_200(transport):
    """Google answers 200 with an error object for a bad client secret."""
    vendors = warden.load_vendors()
    named = [
        (name, row)
        for name, row in vendors.items()
        if (row.get("verify") or {}).get("refuse_when")
    ]
    if not named:
        pytest.skip("no vendor row currently declares a refusal pattern")
    name, row = named[0]
    method = (row["verify"].get("method") or "GET").lower()
    transport(FakeResponse(200, '{"error":"invalid_client"}'), method=method)
    with pytest.raises(warden.ProofFailed):
        warden.prove(name, credential_for(name))


def test_the_summary_the_operator_reads_holds_no_key(transport):
    transport(FakeResponse(200, f'{{"echo":"{SENTINEL}"}}'))
    proof = warden.prove("deepseek", SENTINEL)
    line = warden.summary(proof)
    assert SENTINEL not in line
    assert "deepseek" in line and proof.store in line


def test_the_store_is_the_operators_choice_then_the_rows_default(transport):
    transport(FakeResponse(200), FakeResponse(200))
    assert (
        warden.prove("deepseek", SENTINEL).store
        == warden.vendor_config("deepseek")["store_default"]
    )
    assert (
        warden.prove("deepseek", SENTINEL, store="azure-key-vault").store
        == "azure-key-vault"
    )


def test_a_paired_credential_puts_both_halves_where_the_row_wants_them(transport):
    """A Telegram bot token is useless without the chat it must reach."""
    pair = {"token": SENTINEL, "chat": "-1001234567890"}
    sender = transport(FakeResponse(200))
    proof = warden.prove("apprise_telegram", pair)
    sent = sender.calls[0]["url"]
    assert SENTINEL in sent and "-1001234567890" in sent
    assert "{" not in sent
    assert SENTINEL not in warden.summary(proof)


def test_half_a_paired_credential_is_refused_before_the_vendor_is_asked(transport):
    sender = transport(FakeResponse(200))
    with pytest.raises(ValueError) as raised:
        warden.prove("apprise_telegram", {"token": SENTINEL})
    assert "chat" in str(raised.value)
    assert sender.calls == [], "a half-filled template must never reach the vendor"


def test_an_unknown_vendor_cannot_be_proved():
    with pytest.raises(ValueError):
        warden.prove("a-vendor-nobody-added", SENTINEL)


def test_every_vendor_row_can_build_a_request_for_its_own_check():
    """The registry and the builder agree, for every vendor, not just the one in hand."""
    for name, row in warden.load_vendors().items():
        if not row.get("verify"):
            continue
        base = (row.get("bases") or [None])[0]
        credential = credential_for(name)
        request = warden.build_request(row, credential, base)
        parts = [request["url"], str(request["body"] or "")] + list(
            request["headers"].values()
        )
        assert request["url"].startswith("http"), name
        assert not re.search(r"{[A-Za-z_]", " ".join(parts)), (
            f"{name} left a placeholder unfilled"
        )
        values = credential.values() if isinstance(credential, dict) else [credential]
        for value in values:
            assert any(value in part for part in parts), (
                f"{name} would ask without its credential"
            )
