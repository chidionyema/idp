"""crew#718 CP2 (founder 2026-08-30): "WHERE ARE ALL THE MONITORING TOOLS, WHY CAN I NOT USE THEM".

The login drill graded the second hop by counting password fields. SigNoz renders its sign-in
as a React form whose password input only appears after an email is typed, so the drill read
`0 password field(s)` on signoz.<zone>/login and called the hop ok while the founder was looking
at a login screen -- the silent-green class. A surface that comes to rest on a sign-in path did
not sign anybody in, whatever its DOM says.

This grades the rule itself, not the wording: the paths are evaluated against the ones the
estate actually landed on, an excuse has to carry its vendor page and its ticket, and the
founder-facing sentence on the Tools page may not promise the one login while an excuse stands.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRILL = (ROOT / "bin" / "idp-login-drill").read_text()
TOOLS = (
    ROOT
    / "backstage"
    / "packages"
    / "app"
    / "src"
    / "modules"
    / "home"
    / "toolGroups.ts"
).read_text()


def _literal(name, closer):
    """The drill is bash around a python heredoc, so the rule is read out of the source and
    evaluated here rather than matched as a string -- a reworded constant still gets graded."""
    start = DRILL.index(f"{name} = ")
    end = DRILL.index(closer, start) + len(closer)
    return ast.literal_eval(DRILL[start + len(f"{name} = ") : end])


SIGN_IN_PATHS = _literal("SIGN_IN_PATHS", ")")
EXPECTED = _literal("SECOND_LOGIN_EXPECTED", "}")


def _is_sign_in(path):
    return any(path.startswith(sp) for sp in SIGN_IN_PATHS)


def test_the_paths_the_estate_actually_landed_on_are_graded_as_sign_in_pages():
    # signoz run 33332291556, langfuse run 33254022447 and the shape every other tool serves
    for landed in (
        "/login",
        "/auth/error",
        "/auth/sign-in",
        "/signin",
        "/sign-in",
        "/signup",
    ):
        assert _is_sign_in(landed), (
            f"{landed} is a sign-in page and the drill would pass it"
        )


def test_a_surface_that_opened_is_not_called_a_sign_in_page():
    for landed in ("/", "/ui/", "/screen/", "/services", "/catalog", "/dashboard"):
        assert not _is_sign_in(landed), (
            f"{landed} opened; the drill would fail a working door"
        )


def test_an_unexcused_surface_resting_on_a_sign_in_page_fails_the_drill():
    branch = DRILL[
        DRILL.index("elif any(path.startswith(sp) for sp in SIGN_IN_PATHS):") :
    ]
    branch = branch[: branch.index("if sso_red:")]
    assert "sso_red.append(" in branch, (
        "an unnamed second login has to go red, not print"
    )
    assert "the one login is two" in branch


def test_every_excuse_names_the_vendor_page_it_was_read_from_and_the_ticket_that_closes_it():
    assert EXPECTED, "the set may be empty; a silent entry may not be"
    for name, why in EXPECTED.items():
        assert re.search(r"[a-z0-9-]+\.[a-z]{2,}/", why), (
            f"{name}: no vendor page in the reason"
        )
        assert re.search(r"read 20\d\d-\d\d-\d\d", why), (
            f"{name}: the vendor page has no read date"
        )
        assert re.search(r"crew#\d+", why), f"{name}: no ticket that closes it"


def test_the_tools_page_does_not_promise_one_login_while_a_second_credential_stands():
    sentence = TOOLS[TOOLS.index("export const toolsSentence") :]
    sentence = sentence[: sentence.index("\n};")]
    assert "estate login" in sentence
    if EXPECTED:
        assert "second credential" in sentence, (
            "%s asks the founder for a second credential; the Tools page may not tell him "
            "every door opens on the estate login (crew#718)"
            % ", ".join(sorted(EXPECTED))
        )
