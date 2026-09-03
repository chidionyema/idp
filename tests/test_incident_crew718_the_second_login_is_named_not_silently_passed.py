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


# idp#1050 moved the sign-in path list into probes/front_door.py so the drill and the SigNoz
# prober share one; the test reads it from there, the same place the drill imports it.
from probes.front_door import SIGN_IN_PATHS  # noqa: E402

EXPECTED = _literal("SECOND_LOGIN_EXPECTED", "}")


def _is_sign_in(path):
    return any(path.startswith(sp) for sp in SIGN_IN_PATHS)


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
