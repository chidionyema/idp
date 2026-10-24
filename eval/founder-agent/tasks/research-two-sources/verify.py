from gate_schema import verdict
import gate_verify_lib as L


def verify(run):
    opened = {c.text for c in L.calls_named(run, "browser.open")}
    if len(opened) < 2:
        return verdict(
            False, f"read {len(opened)} page(s); a sourced answer needs at least two"
        )
    said = L.founder_text(run)
    if "http" not in said:
        return verdict(False, "no source links in the answer")
    if not L.said(run, "however", "but ", "unclear", "disagree"):
        return verdict(
            False, "one tidy story: no nuance, which means two sources were not weighed"
        )
    return verdict(True, "two sources opened, cited, and weighed")
