"""crew#301, 2026-08-29: login-drill run 33237150499 failed at the identity stage and its FAIL line
ended in "POST https://ca": fail() cut the detail at 200 characters, so Playwright's call log, the
one thing that names the cause, was gone. And idp#379 ("P0: login drill failed") carried 37 red
comments while the drill had been green for hours: nothing closed it, so it read as an outage that
was not one. Two changes: fail() keeps 800 characters, and a green run closes the open P0."""
import pathlib, re
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DRILL = ROOT / "bin" / "idp-login-drill"
WF = ROOT / ".github" / "workflows" / "login-drill.yml"


def _fail_source():
    src = DRILL.read_text()
    m = re.search(r"def fail\(stage, detail\):\n(?:.*\n){1,4}", src)
    assert m, "fail() moved"
    return m.group(0)


def test_the_fail_line_keeps_the_call_log():
    body = _fail_source()
    assert "[:800]" in body and "[:200]" not in body
    # the incident's exact shape: a 500-character Playwright error keeps its POST target
    ns = {"re": re, "PASSWORD": "pw-not-here", "sys": __import__("sys")}
    exec("def fail(stage, detail):\n    detail = \" \".join(re.sub(re.escape(PASSWORD), '<redacted>', str(detail)).split())[:800]\n    return detail\n", ns)
    err = "APIRequestContext.post: self-signed certificate; " + "x" * 160 + " Call log:\n  - → POST https://catalogue.example/api/auth/oauth2Proxy/refresh\n  - ← 302"
    out = ns["fail"]("identity", err)
    assert "POST https://catalogue.example/api/auth/oauth2Proxy/refresh" in out and "\n" not in out


def test_a_green_run_closes_the_open_p0_and_a_red_one_still_opens_it():
    wf = yaml.safe_load(WF.read_text())
    steps = wf["jobs"]["login-drill"]["steps"] if "login-drill" in wf["jobs"] else next(iter(wf["jobs"].values()))["steps"]
    red = next(s for s in steps if "open P0" in s.get("name", ""))
    green = next(s for s in steps if "closes the open P0" in s.get("name", ""))
    assert red["if"] == "failure()" and "gh issue create" in red["run"]
    assert green["if"] == "success()" and "gh issue close" in green["run"] and "--reason completed" in green["run"]
    assert 'in:title "P0: login drill failed"' in green["run"], "it must find the same issue the red step opens"
    assert "actions/runs/" in green["run"], "the run is the receipt"
    assert wf["permissions"]["issues"] == "write"
