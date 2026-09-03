"""crew#562: the tailnet ACL, applied as written, would have killed the founder's remote desk.

`platform/tailscale/policy.hujson` carried one rule -- `tag:k8s -> tag:founder-mac:22` -- written
for crew#516 CP5, when the only thing that needed to reach the Mac was the cluster. crew#562 then
asked for iPhone -> Mac streaming over the same tailnet, and two Tailscale rules turn that single
rule into a silent outage of it:

  1. A policy file with an `acls` section is deny-by-default. Tailscale's default "allow all" rule
     is REPLACED by whatever the file says, not extended (tailscale.com/kb/1018/acls).
  2. "Applying a tag to a device removes any user-based authentication ... A device cannot
     simultaneously use tag-based and user-based identities" (tailscale.com/kb/1068/tags). The
     founder's sitting runs `tailscale up --advertise-tags=tag:founder-mac`, so from that moment
     the Mac is not his device any more and his phone reaches it only through a named rule.

Together: Moonlight finds no route to Sunshine and the iOS Shortcut's SSH is refused, while the
ACL PUT returns 200 and every instrument stays green. His acceptance line for crew#562 is "i see
it seanlessly nno firction"; this would have been the opposite, discovered by him, after he had
already seen it work.

It has never fired only because `bin/idp-tailscale-policy apply` reads the `tailscale-operator`
OAuth client from the vault and that entry does not exist (no SEED_TAILSCALE_OAUTH_* repository
secret), so the policy has never been PUT. That is a latent trap with a fuse attached to an
unrelated fix: the day the OAuth client is created -- which is also what unblocks the blind
`tailscale/tailscale-operator-secret` row -- this file applies and the remote desk stops working.

These are the rules that file must keep.
"""

import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "platform/tailscale/policy.hujson"

# Sunshine's listening block, from its network configuration docs: TCP 47984 (HTTPS), 47989 (HTTP),
# 47990 (web UI) and 48010 (RTSP); UDP 47998/47999/48000/48002 (video, control, audio, mic) and
# 48010. The dst range below must contain every one of them.
FOUNDER_SRC = "group:founder"
SUNSHINE_PORTS = [47984, 47989, 47990, 47998, 47999, 48000, 48002, 48010]
SHORTCUT_SSH_PORT = 22
VNC_PORT = 5900  # Guacamole's egress to the Mac, platform/guacamole/mac-egress.yaml
MAC = "tag:founder-mac"  # crew#561: measured on the Mac (tailscale status --self: Tags [tag:founder-mac])
SELF = "autogroup:self"


def _hujson(text):
    """hujson is JSON with `//` comments and trailing commas; strip both, respecting strings."""
    out, i, in_str, esc = [], 0, False, False
    while i < len(text):
        c = text[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "/" and text[i : i + 2] == "//":
            i = text.find("\n", i)
            if i == -1:
                break
            continue
        out.append(c)
        i += 1
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", "".join(out)))


@pytest.fixture(scope="module")
def policy():
    return _hujson(POLICY.read_text())


def _dst_ports(policy, tag):
    """Every port the given tag is reachable on, per `src`, as {src: set(ports)}."""
    reach = {}
    for rule in policy["acls"]:
        if rule.get("action") != "accept":
            continue
        for dst in rule["dst"]:
            host, _, ports = dst.rpartition(":")
            if host != tag:
                continue
            got = set()
            for part in ports.split(","):
                if part == "*":
                    got |= set(range(1, 65536))
                elif "-" in part:
                    lo, hi = part.split("-")
                    got |= set(range(int(lo), int(hi) + 1))
                else:
                    got.add(int(part))
            for src in rule["src"]:
                reach.setdefault(src, set()).update(got)
    return reach


def test_the_hujson_still_parses_and_is_the_file_the_applier_will_put(policy):
    """If this file stops parsing, bin/idp-tailscale-policy PUTs a body Tailscale rejects."""
    assert set(policy) >= {"tagOwners", "acls"}
    assert "ssh" not in policy, (
        "crew#561: no Tailscale SSH server runs on the Mac (kb/1193); an ssh rule is a promise nothing keeps"
    )
    assert set(policy["tagOwners"]) == {
        "tag:k8s",
        "tag:founder-mac",
        "tag:k8s-operator",
    }, (
        "crew#561: the Mac is tagged (measured); a tag dropped from tagOwners is a tag the API refuses; tag:k8s-operator is the operator chart's own default device tag (idp#586)"
    )
    assert policy["tagOwners"]["tag:founder-mac"] == [], (
        "admins only may tag a device as the Mac"
    )


def test_the_cluster_still_reaches_the_mac_on_ssh_and_nothing_else(policy):
    """crew#516 CP5's rule is untouched: the machine side is still exactly one port."""
    assert _dst_ports(policy, MAC)["tag:k8s"] == {SHORTCUT_SSH_PORT, VNC_PORT}


def test_the_ios_shortcut_can_ssh_to_wake_the_mac(policy):
    """Action 1 of the Shortcut is `caffeinate -u -t 2` over SSH; without 22 the Mac never wakes."""
    member = _dst_ports(policy, MAC).get(FOUNDER_SRC, set())
    assert SHORTCUT_SSH_PORT in member


def test_the_founder_is_named_not_taken_from_whoever_is_in_the_tailnet(policy):
    """`autogroup:member` is dynamic; the founder's spec for this tag is identity, not membership.

    With `autogroup:member` the first person added to the tailnet later -- a buyer's engineer in
    diligence, a contractor, a second account -- silently gets Moonlight streaming of the founder's
    desktop and SSH as his Unix user, with nothing red and no PUT failure. Naming the login makes a
    second person a deliberate edit to this file (peer review, session 78caaa17 on idp#606).
    """
    srcs = {s for r in policy["acls"] for s in r["src"]}
    assert "autogroup:member" not in srcs, "membership is not identity; name the login"
    assert policy["groups"][FOUNDER_SRC] == ["${FOUNDER_TAILNET_USER}"]


def test_every_placeholder_the_policy_uses_is_one_the_applier_substitutes():
    """A `${...}` missing from envsubst's allow-list is PUT as a literal and matches nobody.

    `envsubst '${A},${B}'` is a single-variable allow-list: anything not in it survives verbatim,
    Tailscale accepts it as a user that does not exist, and the rule silently matches no one with
    a 200 coming back. This is the trap that made this exact change three files instead of one
    (peer review, session 78caaa17). The applier also refuses a rendered body with a surviving
    `${`, which is the runtime half of the same rule.
    """
    applier = (ROOT / "bin/idp-tailscale-policy").read_text()
    used = set(re.findall(r"\$\{([A-Z_][A-Z0-9_]*)\}", POLICY.read_text()))
    assert used == {"FOUNDER_TAILNET_USER"}, used
    allowed = set(
        re.findall(r"envsubst '([^']*)'", applier)[0]
        .replace("$", "")
        .replace("{", "")
        .replace("}", "")
        .split(",")
    )
    assert used <= allowed, (
        f"not substituted, would be PUT as a literal: {used - allowed}"
    )
    for name in used:
        assert f"read_cfg {name}" in applier, f"{name} is never read from estate-config"
        assert f"{name} is empty" in applier, (
            f"{name} has no empty-value guard; it must fail closed"
        )
    assert "*'${'*)" in applier, (
        "the applier no longer refuses a body with a surviving placeholder"
    )


def test_the_founder_reaches_only_his_own_devices_and_the_cluster_only_two_ports(
    policy,
):
    """ "Structurally locked down by identity" is the founder's own spec.

    crew#561: the founder's rule reaches the tagged Mac and his own untagged devices
    (`autogroup:self`) — never `*`, never another tag. The cluster's rule is still a port list:
    22 for mac-run, 5900 for Guacamole's VNC egress, nothing else.
    """
    for rule in policy["acls"]:
        if FOUNDER_SRC in rule["src"]:
            assert all(d.startswith((SELF + ":", MAC + ":")) for d in rule["dst"]), rule
        if "tag:k8s" in rule["src"]:
            assert all(d.startswith(MAC + ":") for d in rule["dst"]), rule
    assert _dst_ports(policy, MAC)["tag:k8s"] == {SHORTCUT_SSH_PORT, VNC_PORT}


def test_no_username_host_or_account_is_a_literal(policy):
    """LAW 46. The one substitution this file carries is the placeholder, not a name."""
    text = POLICY.read_text()
    assert "${FOUNDER_MAC_USER}" not in text, (
        "crew#561: no ssh section, so the Unix user is mac-run's business, not the policy's"
    )
    assert "@" not in json.dumps(policy), "a literal login reached the policy body"
    assert policy["groups"]["group:founder"] == ["${FOUNDER_TAILNET_USER}"]


def test_the_file_carries_exactly_one_placeholder_and_only_in_the_body():
    """Incident 2026-08-29 (oke-check run 33280019151): bin/idp-tailscale-policy greps the whole
    rendered file for `${` after envsubst, comments included; a header comment that spelled the
    placeholder shape out literally made the applier refuse its own policy, so Otto's key was
    minted but the tailnet never learned the rule. The only `${` allowed is the group:founder
    member, and it is substituted before PUT."""
    text = POLICY.read_text()
    assert text.count("${") == 1, (
        "policy.hujson must carry exactly one ${...}, the group:founder member"
    )
    body = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("//"))
    assert "${FOUNDER_TAILNET_USER}" in body
    assert "${" not in "\n".join(
        ln for ln in text.splitlines() if ln.lstrip().startswith("//")
    )
