"""Founder, 2026-08-29: "how do i get anything done with 6vnessages ? nost of then recurring for past
5 days cloggin up annytinng that actually needs nny attenntion".

The flux-telegram Provider posts to his PRIVATE chat (flux-telegram.channel = TELEGRAM_HOME_CHANNEL),
and the broken-workload Alert re-posts every failed reconcile of every row there, each rate-limit
window, for as long as the row is red. The 2026-08-25 ruling in estate_alert.py already said the DM
is for conversation and automated alerts go elsewhere; the cluster senders never got it.
Until the channel in that vault entry is an alerts group, the Alert stays suspended."""
import pathlib

import yaml

IDP = pathlib.Path(__file__).resolve().parents[1]


def _alerts():
    for doc in yaml.safe_load_all((IDP / "platform/alerts/alert.yaml").read_text()):
        if doc and doc.get("kind") == "Alert":
            yield doc


def test_no_telegram_alert_posts_into_the_founder_dm_unsuspended():
    telegram = [a for a in _alerts() if a["spec"]["providerRef"]["name"] == "telegram"]
    assert telegram, "the telegram Alert must still exist; it is suspended, not deleted"
    for a in telegram:
        assert a["spec"].get("suspend") is True, f"{a['metadata']['name']} posts into the founder DM"


def test_the_reds_still_have_a_reader():
    docs = list(yaml.safe_load_all((IDP / "platform/alerts-github/alert.yaml").read_text()))
    assert any(d and d.get("kind") == "Alert" and not d["spec"].get("suspend") for d in docs)


def test_catalog_render_does_not_post_the_goal_into_the_dm_by_default():
    """Founder, 2026-08-29: "disable that step"."""
    src = (IDP / "bin/catalog-render").read_text()
    assert 'os.environ.get("ESTATE_GOAL_TELEGRAM") == "1"' in src
