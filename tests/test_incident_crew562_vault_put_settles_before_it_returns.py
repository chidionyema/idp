"""crew#562: `bin/idp-cloud secret put` returned while OCI was still creating the secret, so the
bootstrapper's read-back (8 s later) said NotFound: oke-check apply run 33217075374, step
bin/idp-bootstrap-sunshine, "FAIL sunshine-auth written but does not read back complete". The class:
a write that returns before the world reads it. Fixed once in idp-cloud, for every bootstrapper."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLOUD = (ROOT / "bin" / "idp-cloud").read_text()


def test_put_settles_after_both_create_and_update():
    body = CLOUD.split("put)", 1)[1]
    for verb in ("update-base64", "create-base64"):
        m = re.search(rf"oci vault secret {verb} .*\n\s+settle_secret \"\$payload\"\n", body)
        assert m, f"{verb} must be followed by settle_secret before put returns"


def test_settle_is_a_bounded_read_back_of_the_same_payload():
    assert re.search(r"settle_secret\(\) \{.*?for i in \$\(seq 1 24\).*?secret get \"\$NAME\".*?\[ \"\$got\" = \"\$want\" \].*?sleep 5.*?blind", CLOUD, re.S)
