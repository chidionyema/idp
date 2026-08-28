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
        if c == "/" and text[i:i + 2] == "//":
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
    assert set(policy) >= {"tagOwners", "acls", "ssh"}
    assert "tag:founder-mac" in policy["tagOwners"]
    assert "tag:k8s" in policy["tagOwners"]


def test_the_cluster_still_reaches_the_mac_on_ssh_and_nothing_else(policy):
    """crew#516 CP5's rule is untouched: the machine side is still exactly one port."""
    assert _dst_ports(policy, "tag:founder-mac")["tag:k8s"] == {SHORTCUT_SSH_PORT}


@pytest.mark.parametrize("port", SUNSHINE_PORTS)
def test_the_founder_reaches_sunshine_on_every_port_it_listens_on(policy, port):
    """One missing port is a stream that connects and then stalls -- worse than a clean refusal."""
    member = _dst_ports(policy, "tag:founder-mac").get(FOUNDER_SRC, set())
    assert port in member, f"Sunshine listens on {port} and no rule lets the founder's phone reach it"


def test_the_ios_shortcut_can_ssh_to_wake_the_mac(policy):
    """Action 1 of the Shortcut is `caffeinate -u -t 2` over SSH; without 22 the Mac never wakes."""
    member = _dst_ports(policy, "tag:founder-mac").get(FOUNDER_SRC, set())
    assert SHORTCUT_SSH_PORT in member


def test_tailscale_ssh_also_admits_the_founder_not_only_the_cluster(policy):
    """`tailscale up --ssh` hands port 22 to the ssh block, so an acl rule alone is not enough.

    The founder's sitting turns Tailscale SSH on for this device (the README's Phase 2 step). From
    then on Tailscale, not sshd, decides port 22, and it decides from `ssh[]`. A file that allows
    the founder in `acls` and forgets `ssh` refuses the Shortcut anyway.
    """
    srcs = {s for r in policy["ssh"] if r.get("action") in ("accept", "check") for s in r["src"]}
    assert FOUNDER_SRC in srcs
    assert "tag:k8s" in srcs, "the cluster's own SSH rule was dropped while adding the founder's"


def test_tailscale_ssh_needs_the_acls_rule_as_well(policy):
    """The `:22` in the acls dst is load-bearing, and a header cannot stop someone deleting it.

    "For a connection to be permitted, the tailnet policy file must contain rules permitting both
    network access and SSH access" (tailscale.com/kb/1193/tailscale-ssh). `--ssh` adds the second
    gate; it does not replace the first. The failure this refuses is a reader who sees the ssh rule
    naming the same connection, concludes the acls `:22` is dead weight, removes it -- and gets SSH
    refused with an ssh rule still sitting there looking correct (peer review, session 78caaa17).
    """
    member = _dst_ports(policy, "tag:founder-mac").get(FOUNDER_SRC, set())
    assert SHORTCUT_SSH_PORT in member, (
        "port 22 left the acls rule. Tailscale SSH needs BOTH an acls rule and an ssh rule; "
        "the ssh entry alone does not permit the connection (kb/1193)")


def test_the_founder_is_named_not_taken_from_whoever_is_in_the_tailnet(policy):
    """`autogroup:member` is dynamic; the founder's spec for this tag is identity, not membership.

    With `autogroup:member` the first person added to the tailnet later -- a buyer's engineer in
    diligence, a contractor, a second account -- silently gets Moonlight streaming of the founder's
    desktop and SSH as his Unix user, with nothing red and no PUT failure. Naming the login makes a
    second person a deliberate edit to this file (peer review, session 78caaa17 on idp#606).
    """
    srcs = {s for r in policy["acls"] for s in r["src"]}
    srcs |= {s for r in policy["ssh"] for s in r["src"]}
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
    assert used == {"FOUNDER_MAC_USER", "FOUNDER_TAILNET_USER"}, used
    allowed = set(re.findall(r"envsubst '([^']*)'", applier)[0].replace("$", "")
                  .replace("{", "").replace("}", "").split(","))
    assert used <= allowed, f"not substituted, would be PUT as a literal: {used - allowed}"
    for name in used:
        assert f'read_cfg {name}' in applier, f"{name} is never read from estate-config"
        assert f'{name} is empty' in applier, f"{name} has no empty-value guard; it must fail closed"
    assert "*'${'*)" in applier, "the applier no longer refuses a body with a surviving placeholder"


def test_estate_config_declares_both_founder_keys_and_neither_is_a_literal():
    """LAW 46 and LAW 21: the values are the founder's hand, empty in git until he fills them."""
    cfg = (ROOT / "clusters/oke/estate-config.yaml").read_text()
    for name in ("FOUNDER_MAC_USER", "FOUNDER_TAILNET_USER"):
        assert f'{name}: ""' in cfg, f"{name} is missing or carries a literal value in git"


def test_the_founder_is_not_given_the_whole_mac(policy):
    """"Structurally locked down by identity" is the founder's own spec; this stays a port list.

    The fix for being locked out is a named set of ports, not `*`. A wildcard would pass every
    test above and quietly undo the thing crew#516 CP5 was for.
    """
    member = _dst_ports(policy, "tag:founder-mac").get(FOUNDER_SRC, set())
    assert len(member) < 1000, "the founder's rule opened the whole device; name the ports"
    assert member <= {SHORTCUT_SSH_PORT} | set(range(47984, 48011))


def test_no_username_host_or_account_is_a_literal(policy):
    """LAW 46. The one substitution this file carries is the placeholder, not a name."""
    text = POLICY.read_text()
    assert "${FOUNDER_MAC_USER}" in text
    for rule in policy["ssh"]:
        assert rule["users"] == ["${FOUNDER_MAC_USER}"]
    assert "@" not in json.dumps(policy), "a literal login reached the policy body"
    assert policy["groups"]["group:founder"] == ["${FOUNDER_TAILNET_USER}"]


def test_the_reason_this_file_changed_is_written_in_it(policy):
    """The next reader must find the two Tailscale rules that make one rule an outage.

    Not a style check: the single-rule version looked correct to everyone who read it, including
    its author, because both rules are about what happens OUTSIDE this file.
    """
    text = POLICY.read_text()
    assert "crew#562" in text
    assert "deny-by-default" in text or "default deny" in text
    assert "removes any user-based authentication" in text
    assert "permitting both" in text, "the acls-and-ssh conjunction (kb/1193) left the header"
