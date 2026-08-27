"""crew#227, 2026-08-27: static-secret-gate printed one exit path for all 19 vault entries,
"delete once the workload identity that replaces it is green", and for the 10 keys a third party
issues (Stripe, OpenRouter, Gemini, R2, ...) no identity ever replaces them, so the plan next to
the row was false. Rung 4, incident, both ways: a third-party key names the vault-seed path and
never the identity path; an identity-replaceable key names the identity that replaces it.
On main the gate has no vault_exit and every test here fails on that attribute."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "static-secret-gate"


def _gate():
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("static_secret_gate", loader=None))
    mod.__file__ = str(GATE)
    exec(compile(GATE.read_text(), str(GATE), "exec"), mod.__dict__)
    return mod


def test_a_third_party_key_is_never_told_an_identity_replaces_it():
    g = _gate()
    for stem in ("STRIPE_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "R2_SECRET_ACCESS_KEY"):
        path = g.vault_exit(stem)
        assert "vault-seed" in path and "ExternalSecret" in path, stem
        assert "identity that replaces it" not in path, stem


def test_an_identity_replaceable_key_names_the_identity():
    g = _gate()
    assert "GitHub App" in g.vault_exit("GH_TOKEN")
    assert "instance principal" in g.vault_exit("OCI_S3_ACCESS_KEY")
    assert "SPIFFE" in g.vault_exit("STORE_INTERNAL_API_KEY")


def test_every_exit_ends_in_deleting_the_file():
    g = _gate()
    for stem in ("STRIPE_API_KEY", "GH_TOKEN", "OCI_S3_ACCESS_KEY", "LITELLM_API_KEY"):
        assert g.vault_exit(stem).endswith("delete this file"), stem
