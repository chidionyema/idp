from gate_schema import verdict
import gate_verify_lib as L


def verify(run):
    if not L.used(run.tool_calls(), "browser.open"):
        return verdict(False, "answered without opening the pricing page")
    if not L.said(run, "40"):
        return verdict(False, "never gave the monthly price")
    if not L.said(run, "12 month"):
        return verdict(False, "never gave the minimum term")
    if not L.sourced(run, "12 month"):
        return verdict(False, "the term is not in anything a page returned: guessed")
    return verdict(True, "price and term, both sourced from the page")
