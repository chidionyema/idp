"""crew#631 CP9: the catalogue is the first surface after Langfuse. Each probe FAILs its broken
door: a closed door fails L2, an open door fails the NEGATIVE control, a dead host fails L1."""

import json
import pathlib

from probes import backstage as B

IDP = pathlib.Path(__file__).resolve().parents[1]
ROW = json.dumps([{"kind": "Component", "metadata": {"name": "idp"}}])


def _stub(*, with_token=(200, ROW), without=(401, '{"error":"Missing credentials"}')):
    def get(url, auth=None, timeout=0, data=None, bearer=None):
        return with_token if bearer else without

    return get


def _outcomes(rows):
    return {a["name"]: a["ok"] for a in rows}


def test_a_healthy_catalogue_passes_all_four():
    got = _outcomes(B.probe("https://c", "tok", get=_stub()))
    assert got == {
        "l1.catalogue.answers": True,
        "l2.entities.status": True,
        "l2.entities.first_row_has_kind": True,
        "l2.NEGATIVE.no_token_is_refused": True,
    }


def test_an_open_door_fails_the_negative_control_only():
    got = _outcomes(B.probe("https://c", "tok", get=_stub(without=(200, ROW))))
    assert (
        got["l2.NEGATIVE.no_token_is_refused"] is False
        and got["l2.entities.status"] is True
    )


def test_a_sign_in_page_or_empty_list_fails_l2():
    page = _outcomes(
        B.probe("https://c", "tok", get=_stub(with_token=(200, "<html>sign in</html>")))
    )
    assert page["l2.entities.first_row_has_kind"] is False
    empty = _outcomes(B.probe("https://c", "tok", get=_stub(with_token=(200, "[]"))))
    assert empty["l2.entities.first_row_has_kind"] is False


def test_a_dead_host_fails_l1():
    got = _outcomes(B.l1_liveness("https://c", get=lambda *a, **k: (0, "refused")))
    assert got["l1.catalogue.answers"] is False


def test_the_machine_door_is_minted_and_read_from_the_secret_volume():
    seed = (IDP / "bin/idp-estate-seed").read_text()
    assert "backstage-env             PROVER_TOKEN                urlsafe32" in seed
    cfg = (IDP / "backstage/app-config.container.yaml").read_text()
    assert (
        "externalAccess" in cfg and "$file: /run/secrets/backstage/PROVER_TOKEN" in cfg
    )
    assert "PROVER_TOKEN: ${" not in cfg  # never from the environment
