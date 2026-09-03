"""The shop's "Continue with Google" button has been missing since the move to Kubernetes, and the
registry that mints every other credential could not express the one it needed.

Measured 2026-08-31 against the live API: https://api.mumchimp.com/v1/auth/external/providers answers
200 with {"providers":[]}. Store.Api registers Google only when both halves of the client are
non-empty (Auth/AuthServiceCollectionExtensions.cs:203-211), the Kubernetes manifest never carried
them, and Store.Web's SocialSignIn returns null on an empty provider list, so the sign-in panel drew
nothing at all. Nothing was broken on the page; the credential was never carried across.

WHY THE REGISTRY COULD NOT FIX IT, WHICH IS THE PART WORTH GUARDING.

platform/vendors/consoles.yaml modelled a vendor root as ONE opaque string with ONE shape and ONE
verify call. An OAuth client is a PAIR: the id and the secret look nothing alike, so one regex
covering both refuses neither, and neither half means anything to Google alone, so neither can be
graded by itself. The registry's own footer had recorded this as an open gap since crew#579.

So `pair: true` was added, with per-target `shape` and `secret`, and `refuse_when` for a vendor that
grades a credential by refusing it rather than by answering 2xx. These tests hold that road to the
three things it has to do: write both halves or neither, refuse a pair the vendor does not know, and
keep naming the exact configuration keys the store reads.
"""

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REG = yaml.safe_load((ROOT / "platform/vendors/consoles.yaml").read_text())["vendors"]
GOOGLE = REG["google_oauth"]
ZONE = re.search(
    r"^\s*ESTATE_ZONE:\s*(\S+)",
    (ROOT / "clusters/oke/estate-config.yaml").read_text(),
    re.M,
).group(1)

# well-formed and entirely made up; the stub answers without leaving the machine
FAKE_ID = "123456789012-abcdefghijklmnop.apps.googleusercontent.com"
FAKE_SECRET = "GOCSPX-" + "F" * 28
ENV = {
    "SEED_GOOGLE_OAUTH_CLIENT_ID": FAKE_ID,
    "SEED_GOOGLE_OAUTH_CLIENT_SECRET": FAKE_SECRET,
}

# What Google answers for a pair it does not know. Measured 2026-08-31 by posting a made-up pair to
# https://oauth2.googleapis.com/token: 401, this body. A pair it DOES know never reaches this error;
# it gets as far as grading the code and answers invalid_grant.
INVALID_CLIENT = (
    '{"error":"invalid_client","error_description":"The OAuth client was not found."}'
)


def _tree(tmp_path):
    idp = tmp_path / "idp"
    (idp / "bin").mkdir(parents=True)
    (idp / "platform/vendors").mkdir(parents=True)
    (idp / "clusters/oke").mkdir(parents=True)
    shutil.copy(
        ROOT / "clusters/oke/estate-config.yaml",
        idp / "clusters/oke/estate-config.yaml",
    )
    shutil.copy(ROOT / "bin/idp-bootstrap-vendors", idp / "bin/idp-bootstrap-vendors")
    shutil.copy(
        ROOT / "platform/vendors/consoles.yaml", idp / "platform/vendors/consoles.yaml"
    )
    log = tmp_path / "calls.log"
    shims = {
        "idp-oci-whoami": "#!/bin/sh\necho estate-ci\n",
        "idp-vault-put": f"#!/bin/sh\nif [ \"$VAULT_PUT_PREFLIGHT\" = 1 ]; then echo 'vault ok'; exit 0; fi\n"
        f'v=$(cat "$ESTATE_ENV_FILE")\necho "put $1 $2 $3 ${{v#V_KEY=}}" >> {log}\n',
        "idp-cloud": "#!/bin/sh\nexit 1\n",  # every entry empty: nothing verifies from the vault
    }
    for n, body in shims.items():
        p = idp / "bin" / n
        p.write_text(body)
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
    # A stub token endpoint whose status and body the test chooses, so the refusal path is exercised
    # for real: a 4xx reaches the script as an HTTPError, which is the response it has to read.
    site = tmp_path / "site"
    site.mkdir()
    (site / "sitecustomize.py").write_text(
        "import io, os, urllib.error, urllib.request\n"
        "class _R(io.BytesIO):\n"
        "    status = 200\n"
        "    def __enter__(self): return self\n"
        "    def __exit__(self, *a): return False\n"
        "def _open(req, timeout=30):\n"
        f"    open({str(tmp_path / 'probe.log')!r}, 'a').write("
        "        req.full_url.split('?')[0] + ' ' + (req.data or b'').decode() + '\\n')\n"
        "    code = int(os.environ.get('STUB_STATUS', '200'))\n"
        "    body = os.environ.get('STUB_BODY', '{}').encode()\n"
        "    if code >= 400:\n"
        "        raise urllib.error.HTTPError(req.full_url, code, 'stub', {}, io.BytesIO(body))\n"
        "    r = _R(body); r.status = code; return r\n"
        "urllib.request.urlopen = _open\n"
    )
    return idp, log, site


def _run(idp, site, env_extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith("SEED_")}
    env.update(
        {
            "PYTHONPATH": str(site),
            "PATH": f"{Path(sys.executable).parent}:{env.get('PATH', '')}",
            **env_extra,
        }
    )
    return subprocess.run(
        [str(idp / "bin/idp-bootstrap-vendors"), "--only", "google_oauth"],
        env=env,
        capture_output=True,
        text=True,
    )


def test_both_halves_are_proved_in_one_call_and_written_together(tmp_path):
    idp, log, site = _tree(tmp_path)
    r = _run(idp, site, ENV)
    assert r.returncode == 0, r.stdout + r.stderr
    puts = log.read_text().splitlines()
    assert len(puts) == 2, puts
    assert (
        f"put --merge prospector-store-api-env Authentication__Google__ClientId=V_KEY {FAKE_ID}"
        in puts
    )
    assert (
        f"put --merge prospector-store-api-env Authentication__Google__ClientSecret=V_KEY {FAKE_SECRET}"
        in puts
    )
    # ONE probe, carrying BOTH halves. Two probes would mean each half was graded alone, which is
    # the thing Google cannot do and the reason `pair` exists.
    probes = (tmp_path / "probe.log").read_text().splitlines()
    assert len(probes) == 1, probes
    assert FAKE_ID in probes[0] and FAKE_SECRET in probes[0]
    assert "oauth2.googleapis.com/token" in probes[0]
    # and the placeholder was resolved from the estate's own config, not left in the URL: a probe
    # naming a redirect URI the store does not serve would grade a client that cannot sign anyone in
    assert f"redirect_uri=https://api.{ZONE}/signin-google" in probes[0], probes[0]
    for value in ENV.values():
        assert value not in r.stdout and value not in r.stderr, "a root reached stdout"


def test_a_pair_google_does_not_know_is_refused_and_nothing_is_written(tmp_path):
    """The defect this rule exists for: a typo, a revoked client, or another project's client. The
    old 2xx rule could not see it -- the token endpoint never answers 2xx to a probe like this, so
    every pair, good or bad, would have failed identically and told nobody which."""
    idp, log, site = _tree(tmp_path)
    r = _run(idp, site, {**ENV, "STUB_STATUS": "401", "STUB_BODY": INVALID_CLIENT})
    assert r.returncode == 1, r.stdout + r.stderr
    assert (
        "FAIL" in r.stdout
        and "refused by https://oauth2.googleapis.com/token" in r.stdout
    )
    assert not log.exists() or log.read_text() == "", log.read_text()


def test_a_pair_google_does_know_passes_though_it_answers_400(tmp_path):
    """The other side of the same rule, and the reason it is written as a refusal. A client Google
    knows gets past invalid_client and is refused for the CODE instead, with a 400. Grading that as
    a failure would be a guard refusing correct work."""
    idp, log, site = _tree(tmp_path)
    invalid_grant = '{"error":"invalid_grant","error_description":"Bad Request"}'
    r = _run(idp, site, {**ENV, "STUB_STATUS": "400", "STUB_BODY": invalid_grant})
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(log.read_text().splitlines()) == 2


def test_half_a_pair_is_blind_for_both_names_and_writes_neither(tmp_path):
    idp, log, site = _tree(tmp_path)
    r = _run(idp, site, {"SEED_GOOGLE_OAUTH_CLIENT_ID": FAKE_ID})
    assert r.returncode == 2, r.stdout + r.stderr
    assert "BLIND   google_oauth" in r.stdout
    assert "gh secret set SEED_GOOGLE_OAUTH_CLIENT_SECRET" in r.stdout
    assert not log.exists() or log.read_text() == "", "half a pair was written"


def test_a_half_that_is_the_wrong_shape_is_refused_before_anything_leaves_the_process(
    tmp_path,
):
    idp, log, site = _tree(tmp_path)
    r = _run(
        idp, site, {**ENV, "SEED_GOOGLE_OAUTH_CLIENT_SECRET": FAKE_ID}
    )  # the id in the secret's place
    assert r.returncode == 1, r.stdout + r.stderr
    assert "does not match the registry shape" in r.stdout
    assert not (tmp_path / "probe.log").exists(), (
        "a badly shaped root was sent to the vendor"
    )
    assert not log.exists() or log.read_text() == ""


def test_the_registry_still_names_the_keys_the_store_actually_reads():
    """Where this drifts silently. Kyverno secrets-not-from-env-vars refuses env-var secrets, so the
    store reads FILES through KeyPerFile, which turns a file named Authentication__Google__ClientId
    into the configuration key Authentication:Google:ClientId. That is the key
    Auth/AuthServiceCollectionExtensions.cs:203 reads before it registers the provider at all, and
    the ExternalSecret carries the whole prospector-store-api-env object across with dataFrom.extract.
    Rename a field here and the button goes quiet again with every test still green."""
    fields = {t["field"]: t for t in GOOGLE["targets"]}
    assert set(fields) == {
        "Authentication__Google__ClientId",
        "Authentication__Google__ClientSecret",
    }
    for f, t in fields.items():
        assert t["entry"] == "prospector-store-api-env"
        assert f.replace("__", ":").startswith("Authentication:Google:")
    # AddGoogle sets no CallbackPath, so ASP.NET serves the default /signin-google. A probe that
    # named a different URI would prove a client that cannot complete a sign-in.
    # ...and named as ${ESTATE_ZONE}, not spelled out: the zone is written once, in
    # clusters/<cluster>/estate-config.yaml, and bin/estate-zone-gate refuses a literal under
    # platform/ (founder 2026-08-26, crew#269: "as always configurable").
    assert (
        "redirect_uri=https://api.${ESTATE_ZONE}/signin-google"
        in GOOGLE["verify"]["body"]
    )
    assert ZONE not in GOOGLE["verify"]["body"]
    assert GOOGLE["pair"] is True
    # every half anchored on its own, and the two shapes must not be interchangeable
    id_shape, secret_shape = (t["shape"] for t in GOOGLE["targets"])
    assert re.fullmatch(id_shape, FAKE_ID) and not re.fullmatch(id_shape, FAKE_SECRET)
    assert re.fullmatch(secret_shape, FAKE_SECRET) and not re.fullmatch(
        secret_shape, FAKE_ID
    )
