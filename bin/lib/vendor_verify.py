"""The one vendor-key probe: bin/idp-bootstrap-vendors and bin/idp-vendor-setup both grade a key with verify(). Values are substituted in-process and never reach argv or a log."""

import base64
import functools
import glob
import re
import sys
import urllib.error
import urllib.request


def say(st: str, who: str, msg: str) -> None:
    print(f"{st:<7} {who:<20} {msg}", flush=True)


@functools.lru_cache(maxsize=None)
def zone(idp: str) -> str:
    """The estate's DNS zone is written once, in clusters/<cluster>/estate-config.yaml, and every
    other platform file says ${ESTATE_ZONE} (founder 2026-08-26, crew#269: "as always
    configurable"; bin/estate-zone-gate refuses a literal anywhere under platform/)."""
    for p in sorted(glob.glob(f"{idp}/clusters/*/estate-config.yaml")):
        m = re.search(r"^\s*ESTATE_ZONE:\s*(\S+)", open(p).read(), re.M)
        if m:
            return m.group(1)
    return ""


def verify(v: dict, subs: dict, idp: str) -> str:
    """subs maps a placeholder to its value: {"key": k} for a single root, one entry per target
    FIELD for a pair. Everything is substituted in-process; no value reaches argv."""
    spec = v["verify"]

    def fill(s):
        for ph, val in subs.items():
            s = s.replace("{" + ph + "}", val)
        if "${ESTATE_ZONE}" in s:
            z = zone(idp)
            if not z:
                # BLIND, never a quiet https://api./... probe: a half-built URL would be refused by
                # the vendor and read as a bad credential, which is the wrong thing to tell anyone.
                say(
                    "BLIND",
                    "registry",
                    "no ESTATE_ZONE in clusters/*/estate-config.yaml; the probe URL cannot be built",
                )
                sys.exit(2)
            s = s.replace("${ESTATE_ZONE}", z)
        if "${" in s:
            say(
                "FAIL",
                "registry",
                f"unresolved placeholder in {spec['url']}; every substitution is named here",
            )
            sys.exit(1)
        return s

    headers = {k: fill(val) for k, val in (spec.get("headers") or {}).items()}
    # `basic: '{user}:{password}'` -- HTTP basic auth (Grafana Cloud's OTLP gateway, idp#4591),
    # encoded here so the registry never has to spell a base64 of two fields it cannot compute.
    # The encoded form joins the scrub list, so a vendor echoing the header never reaches the log.
    if spec.get("basic"):
        cred = base64.b64encode(fill(spec["basic"]).encode()).decode()
        headers["Authorization"] = "Basic " + cred
        subs = {**subs, "_basic": cred}
    data = fill(spec["body"]).encode() if spec.get("body") else None
    req = urllib.request.Request(  # noqa: S310 -- the URL is the registry's verify url, never user input
        fill(spec["url"]), data=data, method=spec["method"], headers=headers
    )
    refuse = spec.get("refuse_when")

    def head(body):
        # The first 120 characters of what the vendor said, on one line, with every substituted
        # value scrubbed. A vendor echoing a key back must never reach the log.
        text = body.decode("utf-8", "replace")
        for val in subs.values():
            if val:
                text = text.replace(val, "***")
        return " ".join(text.split())[:120]

    # Returns "" when the credential verifies, otherwise the vendor's answer: "HTTP <status> <body
    # head>" or "no answer (<error>)". Measured 2026-09-02 (runs 33681830297, 33685104831): three
    # funded vendor keys read "refused" with the status swallowed, so a dead key, an empty balance,
    # a wrong probe URL and a rate limit were one word, and the founder was told to revoke keys he
    # had made that day. The status is the evidence; it rides the FAIL line.
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 -- the URL is the registry's verify url, never user input
            body = resp.read(65536)
            if refuse:
                return (
                    ""
                    if not re.search(refuse, body.decode("utf-8", "replace"))
                    else f"HTTP {resp.status} {head(body)}"
                )
            return (
                "" if 200 <= resp.status < 300 else f"HTTP {resp.status} {head(body)}"
            )
    except urllib.error.HTTPError as e:
        # An HTTPError IS the response, and a `refuse_when` vendor answers on a 4xx on purpose: the
        # Google token endpoint will not confirm an OAuth client, it will only refuse one it does
        # not know. Reading that body is the whole check. Without refuse_when a 4xx is still a FAIL.
        body = e.read(65536)
        if refuse and not re.search(refuse, body.decode("utf-8", "replace")):
            return ""
        return f"HTTP {e.code} {head(body)}"
    except Exception as e:
        return f"no answer ({type(e).__name__})"
