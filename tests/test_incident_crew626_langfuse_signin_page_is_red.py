"""crew#626: the founder was asked to log in again on Langfuse while the drill was green.

The drill user landed on /auth/sign-in (run 33254022447) and the drill graded only "no
password box". A sign-in page under /auth/ is a second login and must fail the drill.
"""

from pathlib import Path

DRILL = Path(__file__).resolve().parents[1] / "bin" / "idp-login-drill"


def test_a_langfuse_auth_page_fails_the_second_hop():
    src = DRILL.read_text()
    assert 'lf_path.startswith("/auth/")' in src
    assert "second login" in src
